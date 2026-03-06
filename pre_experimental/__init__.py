from copy import deepcopy
from otree.api import *
import certifi
import json
import logging
import os
import random
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from movie_data import NUM_ROUNDS as MOVIE_NUM_ROUNDS
from polquestions_data import LIKERT6_CHOICES, POL_QUESTION_NAMES, POL_QUESTIONS, POL_QUESTIONS_BY_NAME
from survey_data import load_survey_definition
from surveyjs_page import SurveyJSPage


logger = logging.getLogger(__name__)

try:
    from user_agents import parse as parse_user_agent
except ImportError:
    parse_user_agent = None


doc = """
Pre-experimental survey and private movie ranking.
"""

PRE_COMPREHENSION_SURVEY_DEFINITION = load_survey_definition('survey_pre_comprehension.yaml')
PRE_POLITICAL_SURVEY_DEFINITION = load_survey_definition('survey_pre_political.yaml')

TREATMENT_CYCLE = [
    dict(heterogeneous='yes', political='yes', label='heterogeneous_political'),
    dict(heterogeneous='no', political='yes', label='homogeneous_political'),
    dict(heterogeneous='yes', political='no', label='heterogeneous_neutral'),
    dict(heterogeneous='no', political='no', label='homogeneous_neutral'),
]


def round_choices(num_rounds):
    options = sorted({max(1, num_rounds - 5), num_rounds, num_rounds + 5})
    return [[str(value), f'{value} rounds'] for value in options]


def set_element_choices(definition, element_name, choices):
    for page in definition.get('pages', []):
        for element in page.get('elements', []):
            if element.get('name') == element_name:
                element['choices'] = choices
                return


def required_favorites(session_config):
    try:
        value = int(session_config.get('tmdb_favorites_required', 5))
    except (TypeError, ValueError):
        value = 5
    return max(1, min(20, value))


def get_tmdb_api_key(session_config):
    env_var = session_config.get('tmdb_api_key_env_var', 'TMDB_API_KEY')
    env_key = os.environ.get(env_var)
    if env_key:
        return env_key

    fallback_key = session_config.get('tmdb_api_key', '')
    return fallback_key or ''


def tmdb_search(query, session_config):
    api_key = get_tmdb_api_key(session_config)
    if not api_key:
        raise RuntimeError('TMDb API key is not configured on the server.')

    base_url = session_config.get('tmdb_search_base_url', 'https://api.themoviedb.org/3/search/movie')
    language = session_config.get('tmdb_language', 'en-US')
    include_adult = bool(session_config.get('tmdb_include_adult', False))

    try:
        limit = int(session_config.get('tmdb_results_limit', 12))
    except (TypeError, ValueError):
        limit = 12
    limit = max(1, min(50, limit))

    params = dict(
        api_key=api_key,
        query=query,
        language=language,
        include_adult='true' if include_adult else 'false',
        page=1,
    )
    url = f"{base_url}?{urlencode(params)}"

    request = Request(url, headers={'Accept': 'application/json'})
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=10, context=ctx) as response:
        payload = json.loads(response.read().decode('utf-8'))

    enrich_results = bool(session_config.get('tmdb_enrich_results', True))
    movie_base_url = session_config.get('tmdb_movie_base_url', 'https://api.themoviedb.org/3/movie')
    try:
        cast_limit = int(session_config.get('tmdb_cast_limit', 3))
    except (TypeError, ValueError):
        cast_limit = 3
    cast_limit = max(1, min(5, cast_limit))

    def fetch_movie_credits(movie_id):
        details_params = dict(
            api_key=api_key,
            language=language,
            append_to_response='credits',
        )
        details_url = f"{movie_base_url}/{movie_id}?{urlencode(details_params)}"
        details_request = Request(details_url, headers={'Accept': 'application/json'})
        with urlopen(details_request, timeout=10, context=ctx) as details_response:
            details_payload = json.loads(details_response.read().decode('utf-8'))

        credits = details_payload.get('credits') or {}
        crew = credits.get('crew') or []
        cast = credits.get('cast') or []

        director = ''
        for person in crew:
            if not isinstance(person, dict):
                continue
            if person.get('job') == 'Director':
                director = person.get('name') or ''
                if director:
                    break

        cast_names = []
        for person in cast:
            if not isinstance(person, dict):
                continue
            name = person.get('name') or ''
            if name:
                cast_names.append(name)
            if len(cast_names) >= cast_limit:
                break

        return director, cast_names

    movies = []
    for item in payload.get('results', [])[:limit]:
        movie_id = item.get('id')
        title = item.get('title') or item.get('original_title')
        if not movie_id or not title:
            continue

        director = ''
        cast_names = []
        if enrich_results:
            try:
                director, cast_names = fetch_movie_credits(int(movie_id))
            except Exception as exc:
                logger.warning('TMDb details fetch failed for movie_id=%s: %s', movie_id, exc)

        movies.append(
            dict(
                id=int(movie_id),
                title=title,
                release_date=item.get('release_date') or '',
                poster_path=item.get('poster_path') or '',
                overview=item.get('overview') or '',
                director=director,
                cast=cast_names,
            )
        )

    return movies


def tmdb_debug_errors_enabled(session_config):
    return bool(session_config.get('tmdb_debug_errors', False))


def tmdb_error_message(session_config, exc):
    generic = 'TMDb search is currently unavailable. Please try again.'
    if not tmdb_debug_errors_enabled(session_config):
        return generic

    if isinstance(exc, HTTPError):
        detail = f'HTTP {exc.code} {exc.reason}'
    elif isinstance(exc, URLError):
        detail = f'URL error: {exc.reason}'
    elif isinstance(exc, TimeoutError):
        detail = 'Request timed out.'
    elif isinstance(exc, RuntimeError):
        detail = str(exc)
    elif isinstance(exc, ValueError):
        detail = str(exc)
    else:
        detail = f'{exc.__class__.__name__}: {exc}'

    return f'{generic} (debug: {detail})'


def treatment_for_index(index):
    return TREATMENT_CYCLE[(index - 1) % len(TREATMENT_CYCLE)]


def ensure_pol_question_order(participant):
    order = participant.vars.get('pol_question_order')
    if isinstance(order, list) and sorted(order) == sorted(POL_QUESTION_NAMES):
        return order

    order = POL_QUESTION_NAMES.copy()
    random.shuffle(order)
    participant.vars['pol_question_order'] = order
    participant.pol_question_order = json.dumps(order)
    return order


def build_pol_survey_definition(order):
    pages = [
        dict(
            name='intro_page',
            elements=[
                dict(
                    type='html',
                    name='intro_text',
                    html="Now we will ask you to state whether you agree or disagree with specific statements. Click 'Next' to proceed.",
                )
            ],
        )
    ]

    for question_name in order:
        question = POL_QUESTIONS_BY_NAME.get(question_name)
        if not question:
            continue

        pages.append(
            dict(
                name=f"page_{question['name']}",
                elements=[
                    dict(
                        type='radiogroup',
                        name=question['name'],
                        title=question['text'],
                        isRequired=True,
                        colCount=6,
                        choices=LIKERT6_CHOICES,
                    )
                ],
            )
        )

    return dict(
        showQuestionNumbers='off',
        showProgressBar='top',
        progressBarType='pages',
        pages=pages,
    )


def sync_player_treatment_fields(player):
    player.treatment_heterogeneous = player.participant.vars.get('treatment_heterogeneous', 'no')
    player.treatment_political = player.participant.vars.get('treatment_political', 'yes')


class C(BaseConstants):
    NAME_IN_URL = 'pre_experimental'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    MAIN_NUM_ROUNDS = MOVIE_NUM_ROUNDS


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    consent_given = models.BooleanField(
        initial=False,
        label='Yes, I have read the participant information and I consent to participate.',
    )

    comprehension_failed_attempts = models.IntegerField(initial=0)

    user_agent_browser = models.StringField(blank=True)
    user_agent_browser_version = models.StringField(blank=True)
    user_agent_os = models.StringField(blank=True)
    user_agent_os_version = models.StringField(blank=True)
    user_agent_device = models.StringField(blank=True)
    user_agent_is_bot = models.BooleanField(initial=False)
    user_agent_is_mobile = models.BooleanField(initial=False)
    user_agent_is_tablet = models.BooleanField(initial=False)
    user_agent_is_pc = models.BooleanField(initial=False)

    cq_endowment = models.StringField(
        choices=[
            ['1.00', 'EUR 1.00'],
            ['2.50', 'EUR 2.50'],
            ['5.00', 'EUR 5.00'],
        ],
        widget=widgets.RadioSelect,
        label='What is your starting endowment for Part 2?',
    )
    cq_rating_cost = models.StringField(
        choices=[
            ['0.10', 'EUR 0.10'],
            ['0.25', 'EUR 0.25'],
            ['0.50', 'EUR 0.50'],
        ],
        widget=widgets.RadioSelect,
        label='How much does each rating cost?',
    )
    cq_rounds = models.StringField(
        choices=round_choices(C.MAIN_NUM_ROUNDS),
        widget=widgets.RadioSelect,
        label='How many interaction rounds are there?',
    )
    cq_max_bonus = models.StringField(
        choices=[
            ['5', 'Up to EUR 5'],
            ['10', 'Up to EUR 10'],
            ['15', 'Up to EUR 15'],
        ],
        widget=widgets.RadioSelect,
        label='What is the maximum performance bonus?',
    )

    politics_ideology = models.IntegerField(
        min=0,
        max=10,
        label='In politics, where do you place yourself? (0 = Left, 10 = Right)',
    )
    politics_interest = models.IntegerField(
        choices=[1, 2, 3, 4, 5],
        widget=widgets.RadioSelect,
        label='How interested are you in politics? (1 = Not at all, 5 = Very interested)',
    )
    migration_policy = models.IntegerField(
        choices=[1, 2, 3, 4, 5],
        widget=widgets.RadioSelect,
        label='Migration policy should be... (1 = much more open, 5 = much stricter)',
    )
    climate_priority = models.IntegerField(
        choices=[1, 2, 3, 4, 5],
        widget=widgets.RadioSelect,
        label='Climate protection should have priority even if costly (1 = strongly disagree, 5 = strongly agree)',
    )

    treatment_heterogeneous = models.StringField(blank=True)
    treatment_political = models.StringField(blank=True)

    pol_question_order_json = models.LongStringField(blank=True)
    pol_answers_json = models.LongStringField(blank=True)
    ranking_json = models.LongStringField(blank=True)


def creating_session(subsession: BaseSubsession):
    if subsession.round_number != 1:
        return

    players = sorted(subsession.get_players(), key=lambda p: p.id_in_subsession)
    for player in players:
        treatment = treatment_for_index(player.id_in_subsession)

        participant = player.participant
        participant.treatment_heterogeneous = treatment['heterogeneous']
        participant.treatment_political = treatment['political']
        participant.treatment_label = treatment['label']

        participant.vars['treatment_heterogeneous'] = treatment['heterogeneous']
        participant.vars['treatment_political'] = treatment['political']
        participant.vars['treatment_label'] = treatment['label']

        order = POL_QUESTION_NAMES.copy()
        random.shuffle(order)
        participant.vars['pol_question_order'] = order
        participant.vars['pol_answers'] = {}

        participant.pol_question_order = json.dumps(order)
        participant.pol_answers_json = '{}'

        player.pol_question_order_json = json.dumps(order)
        player.pol_answers_json = '{}'
        player.comprehension_failed_attempts = 0
        participant.vars['comprehension_failed_attempts'] = 0
        sync_player_treatment_fields(player)


class Consent(Page):
    form_model = 'player'
    form_fields = ['consent_given']

    def get(self, *args, **kwargs):
        user_agent_string = self.request.headers.get('User-Agent', '')
        if parse_user_agent:
            user_agent = parse_user_agent(user_agent_string)
            self.player.user_agent_browser = user_agent.browser.family or ''
            self.player.user_agent_browser_version = user_agent.browser.version_string or ''
            self.player.user_agent_os = user_agent.os.family or ''
            self.player.user_agent_os_version = user_agent.os.version_string or ''
            self.player.user_agent_device = user_agent.device.family or ''
            self.player.user_agent_is_mobile = bool(user_agent.is_mobile)
            self.player.user_agent_is_tablet = bool(user_agent.is_tablet)
            self.player.user_agent_is_pc = bool(user_agent.is_pc)
            self.player.user_agent_is_bot = bool(user_agent.is_bot)
        else:
            logger.warning('user-agents package not installed; User-Agent details were not parsed.')
            self.player.user_agent_device = user_agent_string[:255]
        
        return super().get(*args, **kwargs)


class InstructionsIntro(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(num_rounds=C.MAIN_NUM_ROUNDS)


class ComprehensionCheck(SurveyJSPage):
    form_model = 'player'
    form_fields = ['cq_endowment', 'cq_rating_cost', 'cq_rounds', 'cq_max_bonus']

    @staticmethod
    def vars_for_template(player: Player):
        survey_definition = deepcopy(PRE_COMPREHENSION_SURVEY_DEFINITION)
        set_element_choices(
            survey_definition,
            'cq_rounds',
            [
                dict(value=str(value), text=f'{value} rounds')
                for value in sorted({max(1, C.MAIN_NUM_ROUNDS - 5), C.MAIN_NUM_ROUNDS, C.MAIN_NUM_ROUNDS + 5})
            ],
        )
        return dict(
            num_rounds=C.MAIN_NUM_ROUNDS,
            survey_json=json.dumps(survey_definition),
        )

    def process_survey_data(self, data):
        return dict(
            cq_endowment=data.get('cq_endowment'),
            cq_rating_cost=data.get('cq_rating_cost'),
            cq_rounds=data.get('cq_rounds'),
            cq_max_bonus=data.get('cq_max_bonus'),
        )

    @staticmethod
    def error_message(player: Player, values):
        correct_answers = {
            'cq_endowment': '2.50',
            'cq_rating_cost': '0.25',
            'cq_rounds': str(C.MAIN_NUM_ROUNDS),
            'cq_max_bonus': '10',
        }

        for field_name, expected in correct_answers.items():
            if values[field_name] != expected:
                attempts = int(player.participant.vars.get('comprehension_failed_attempts', 0)) + 1
                player.participant.vars['comprehension_failed_attempts'] = attempts
                player.comprehension_failed_attempts = attempts
                return 'One or more answers are incorrect. Please review the instructions and try again.'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.comprehension_failed_attempts = int(player.participant.vars.get('comprehension_failed_attempts', 0))


class PolPage(SurveyJSPage):
    form_model = 'player'
    form_fields = ['pol_answers_json']

    @staticmethod
    def vars_for_template(player: Player):
        order = ensure_pol_question_order(player.participant)
        player.pol_question_order_json = json.dumps(order)
        survey_definition = build_pol_survey_definition(order)
        return dict(
            num_rounds=C.MAIN_NUM_ROUNDS,
            pol_question_count=len(order),
            survey_json=json.dumps(survey_definition),
        )

    def process_survey_data(self, data):
        answers = {name: str(data.get(name, '')) for name in POL_QUESTION_NAMES if name in data}
        return dict(pol_answers_json=answers)

    @staticmethod
    def error_message(player: Player, values):
        raw = values.get('pol_answers_json') or ''
        try:
            answers = json.loads(raw)
        except json.JSONDecodeError:
            return 'Please answer all statements before continuing.'

        if not isinstance(answers, dict):
            return 'Please answer all statements before continuing.'

        missing = [name for name in POL_QUESTION_NAMES if not answers.get(name)]
        if missing:
            return 'Please answer all statements before continuing.'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        sync_player_treatment_fields(player)

        participant = player.participant
        pol_answers_json = player.field_maybe_none('pol_answers_json') or '{}'
        participant.vars['pol_answers'] = json.loads(pol_answers_json)
        participant.pol_answers_json = pol_answers_json

        order = ensure_pol_question_order(participant)
        player.pol_question_order_json = json.dumps(order)


class PoliticalSurvey(SurveyJSPage):
    form_model = 'player'
    form_fields = ['politics_ideology', 'politics_interest', 'migration_policy', 'climate_priority']

    @staticmethod
    def vars_for_template(player: Player):
        return dict(survey_json=json.dumps(PRE_POLITICAL_SURVEY_DEFINITION))

    def process_survey_data(self, data):
        return dict(
            politics_ideology=data.get('politics_ideology'),
            politics_interest=data.get('politics_interest'),
            migration_policy=data.get('migration_policy'),
            climate_priority=data.get('climate_priority'),
        )


class MovieRanking(Page):
    form_model = 'player'
    form_fields = ['ranking_json']

    @staticmethod
    def vars_for_template(player: Player):
        ranking_json = player.field_maybe_none('ranking_json') or '[]'
        return dict(
            num_rounds=C.MAIN_NUM_ROUNDS,
            favorites_required=required_favorites(player.session.config),
            ranking_json_value=ranking_json,
        )

    @staticmethod
    def live_method(player: Player, data):
        if not isinstance(data, dict):
            return {player.id_in_group: dict(type='search_error', message='Invalid request payload.')}

        if data.get('type') != 'tmdb_search':
            return {player.id_in_group: dict(type='search_error', message='Unsupported live request type.')}

        query = (data.get('q') or '').strip()
        request_id = data.get('request_id')
        if len(query) < 2:
            return {
                player.id_in_group: dict(
                    type='search_error',
                    request_id=request_id,
                    message='Type at least 2 characters to search.',
                )
            }

        query = query[:120]

        try:
            movies = tmdb_search(query, player.session.config)
            return {
                player.id_in_group: dict(
                    type='search_results',
                    request_id=request_id,
                    results=movies,
                )
            }
        except RuntimeError as exc:
            logger.warning('TMDb configuration issue: %s', exc)
            message = tmdb_error_message(player.session.config, exc)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            logger.warning('TMDb search failed for query %r: %s', query, exc)
            message = tmdb_error_message(player.session.config, exc)
        except Exception as exc:
            logger.exception('Unexpected TMDb search error for query %r: %s', query, exc)
            message = tmdb_error_message(player.session.config, exc)

        return {
            player.id_in_group: dict(
                type='search_error',
                request_id=request_id,
                message=message,
            )
        }

    @staticmethod
    def error_message(player: Player, values):
        raw_ranking = values.get('ranking_json') or ''
        try:
            ranking = json.loads(raw_ranking)
        except json.JSONDecodeError:
            return 'Please select and rank your movies before continuing.'

        if not isinstance(ranking, list):
            return 'Please select and rank your movies before continuing.'

        required = required_favorites(player.session.config)
        if len(ranking) != required:
            return f'Please rank exactly {required} movies before continuing.'

        seen_ids = set()
        for movie in ranking:
            if not isinstance(movie, dict):
                return 'The ranking format is invalid. Please try again.'
            movie_id = movie.get('id')
            title = movie.get('title')
            if movie_id is None or not title:
                return 'The ranking format is invalid. Please try again.'
            if movie_id in seen_ids:
                return 'Duplicate movies detected. Please reorder and submit again.'
            seen_ids.add(movie_id)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        sync_player_treatment_fields(player)

        ranking = json.loads(player.field_maybe_none('ranking_json') or '[]')
        player.participant.vars['true_movie_ranking_tmdb'] = ranking
        player.participant.vars['true_movie_ranking'] = [
            item.get('title', '') for item in ranking if isinstance(item, dict) and item.get('title')
        ]


page_sequence = [
    # Consent, InstructionsIntro, ComprehensionCheck, PolPage,
    # PoliticalSurvey,
    # MovieRanking
    ]
