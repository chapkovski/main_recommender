from copy import deepcopy
from otree.api import *
import json

from movie_data import NUM_ROUNDS as MOVIE_NUM_ROUNDS
from survey_data import load_survey_definition
from surveyjs_page import SurveyJSPage


doc = """
Pre-experimental survey and private movie ranking.
"""

PRE_COMPREHENSION_SURVEY_DEFINITION = load_survey_definition('survey_pre_comprehension.yaml')
PRE_POLITICAL_SURVEY_DEFINITION = load_survey_definition('survey_pre_political.yaml')
PRE_RANKING_SURVEY_DEFINITION = load_survey_definition('survey_pre_ranking.yaml')


def round_choices(num_rounds):
    options = sorted({max(1, num_rounds - 5), num_rounds, num_rounds + 5})
    return [[str(value), f'{value} rounds'] for value in options]


def set_element_choices(definition, element_name, choices):
    for page in definition.get('pages', []):
        for element in page.get('elements', []):
            if element.get('name') == element_name:
                element['choices'] = choices
                return


class C(BaseConstants):
    NAME_IN_URL = 'pre_experimental'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    MAIN_NUM_ROUNDS = MOVIE_NUM_ROUNDS
    MOVIES_FOR_RANKING = [
        'Civil War',
        'Oppenheimer',
        'Killers of the Flower Moon',
        'The Zone of Interest',
        '20 Days in Mariupol',
    ]


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
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
    ranking_json = models.LongStringField(blank=True)


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
                return 'One or more answers are incorrect. Please review the instructions and try again.'


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


class MovieRanking(SurveyJSPage):
    form_model = 'player'
    form_fields = ['ranking_json']

    @staticmethod
    def vars_for_template(player: Player):
        survey_definition = deepcopy(PRE_RANKING_SURVEY_DEFINITION)
        set_element_choices(survey_definition, 'ranking_json', C.MOVIES_FOR_RANKING)
        return dict(
            num_rounds=C.MAIN_NUM_ROUNDS,
            ranking_movies=C.MOVIES_FOR_RANKING,
            survey_json=json.dumps(survey_definition),
        )

    def process_survey_data(self, data):
        return dict(ranking_json=data.get('ranking_json', []))

    @staticmethod
    def error_message(player: Player, values):
        raw_ranking = values.get('ranking_json') or ''
        try:
            ranking = json.loads(raw_ranking)
        except json.JSONDecodeError:
            return 'Please rank all 5 movies before continuing.'

        if not isinstance(ranking, list):
            return 'Please rank all 5 movies before continuing.'

        expected = C.MOVIES_FOR_RANKING
        if len(ranking) != len(expected):
            return 'Please rank all 5 movies before continuing.'

        if sorted(ranking) != sorted(expected):
            return 'The ranking list is invalid. Please reorder again.'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.participant.vars['true_movie_ranking'] = json.loads(player.ranking_json)


page_sequence = [InstructionsIntro, ComprehensionCheck, PoliticalSurvey, MovieRanking]
