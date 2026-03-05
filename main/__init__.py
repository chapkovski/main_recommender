from otree.api import *
import json
import random

from movie_data import MOVIES as MOVIE_DATA, NUM_ROUNDS as MOVIE_NUM_ROUNDS
from polquestions_data import LIKERT6_LABELS, POL_QUESTIONS, POL_QUESTIONS_BY_NAME
from survey_data import load_survey_definition
from surveyjs_page import SurveyJSPage

doc = """
Main experiment: independent rating rounds.
"""

RATING_SURVEY_DEFINITION = load_survey_definition('survey_main_rating.yaml')


def treatment_alert_context(player):
    participant = player.participant
    heterogeneous = participant.vars.get(
        'treatment_heterogeneous',
        getattr(participant, 'treatment_heterogeneous', 'no'),
    )
    political = participant.vars.get(
        'treatment_political',
        getattr(participant, 'treatment_political', 'yes'),
    )

    relation = 'disagrees' if heterogeneous == 'yes' else 'agrees'
    target_treatment = 'polarizing' if political == 'yes' else 'neutral'
    topic_label = 'political' if political == 'yes' else 'non-political'

    order = participant.vars.get('pol_question_order', [])
    answers = participant.vars.get('pol_answers', {})

    statements = []
    seen = set()
    for question_name in order if isinstance(order, list) else []:
        question = POL_QUESTIONS_BY_NAME.get(question_name)
        if not question or question['treatment'] != target_treatment or question_name in seen:
            continue
        seen.add(question_name)
        response_label = LIKERT6_LABELS.get(str(answers.get(question_name, '')), '')
        statements.append(
            dict(
                text=question['text'],
                response=response_label,
            )
        )

    if not statements:
        for question in POL_QUESTIONS:
            if question['treatment'] == target_treatment:
                statements.append(dict(text=question['text'], response=''))

    return dict(
        relation=relation,
        topic_label=topic_label,
        statements=statements,
    )


class C(BaseConstants):
    NAME_IN_URL = 'main'
    PLAYERS_PER_GROUP = None
    MOVIES = MOVIE_DATA
    NUM_ROUNDS = MOVIE_NUM_ROUNDS

    ENDOWMENT = cu(2.50)
    RATING_COST = cu(0.25)
    BONUS_PER_CORRECT = cu(2)
    MAX_CORRECT = 5


def creating_session(subsession: BaseSubsession):
    if subsession.round_number != 1:
        return

    for player in subsession.get_players():
        player.participant.vars['movie_order_main'] = random.sample(C.MOVIES, C.NUM_ROUNDS)


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    decision = models.StringField(
        choices=[['skip', 'Skip (no cost)'], ['rate', 'Rate this movie (pay EUR 0.25)']],
        widget=widgets.RadioSelect,
    )
    movie_rating = models.IntegerField(
        blank=True,
        choices=[
            [1, '1 - Strongly dislike'],
            [2, '2 - Dislike'],
            [3, '3 - Neutral'],
            [4, '4 - Like'],
            [5, '5 - Strongly like'],
        ],
        widget=widgets.RadioSelect,
        label='If you choose to rate, what is your rating?',
    )

    movie_title = models.StringField(blank=True)
    round_cost = models.CurrencyField(initial=cu(0))
    treatment_heterogeneous = models.StringField(blank=True)
    treatment_political = models.StringField(blank=True)

    def current_movie(self):
        movie_order = self.participant.vars['movie_order_main']
        return movie_order[self.round_number - 1]


class RatingDecision(SurveyJSPage):
    form_model = 'player'
    form_fields = ['decision', 'movie_rating']

    @staticmethod
    def vars_for_template(player: Player):
        movie = player.current_movie()
        spent_so_far = sum((round_player.round_cost for round_player in player.in_previous_rounds()), cu(0))
        remaining_budget = C.ENDOWMENT - spent_so_far
        treatment_alert = treatment_alert_context(player)
        return dict(
            movie=movie,
            movie_number=player.round_number,
            total_movies=C.NUM_ROUNDS,
            movie_image_url=f"/static/{movie['image']}",
            survey_json=json.dumps(RATING_SURVEY_DEFINITION),
            num_rounds=C.NUM_ROUNDS,
            spent_so_far=spent_so_far,
            remaining_budget=remaining_budget,
            peer_relation=treatment_alert['relation'],
            peer_topic_label=treatment_alert['topic_label'],
            peer_statements=treatment_alert['statements'],
        )

    def process_survey_data(self, data):
        return dict(
            decision=data.get('decision'),
            movie_rating=data.get('movie_rating'),
        )

    @staticmethod
    def error_message(player: Player, values):
        if values.get('decision') == 'rate' and not values.get('movie_rating'):
            return 'Please provide a rating if you choose "Rate this movie".'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.treatment_heterogeneous = player.participant.vars.get('treatment_heterogeneous', 'no')
        player.treatment_political = player.participant.vars.get('treatment_political', 'yes')
        player.movie_title = player.current_movie()['title']
        if player.decision == 'rate':
            player.round_cost = C.RATING_COST
        else:
            player.round_cost = cu(0)
            player.movie_rating = None

        if player.round_number == C.NUM_ROUNDS:
            all_rounds = player.in_all_rounds()
            num_ratings = sum(1 for round_player in all_rounds if round_player.decision == 'rate')
            player.participant.vars['num_ratings_main'] = num_ratings


class MainResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        all_rounds = player.in_all_rounds()
        num_ratings = sum(1 for round_player in all_rounds if round_player.decision == 'rate')
        total_cost = C.RATING_COST * num_ratings
        remaining_endowment = C.ENDOWMENT - total_cost
        return dict(
            total_rounds=C.NUM_ROUNDS,
            num_ratings=num_ratings,
            total_cost=total_cost,
            remaining_endowment=remaining_endowment,
            endowment=C.ENDOWMENT,
        )


page_sequence = [RatingDecision, MainResults]
