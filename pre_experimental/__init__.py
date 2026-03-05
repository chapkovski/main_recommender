from otree.api import *
import json


doc = """
Pre-experimental survey and private movie ranking.
"""


class C(BaseConstants):
    NAME_IN_URL = 'pre_experimental'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
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
        choices=[
            ['5', '5 rounds'],
            ['10', '10 rounds'],
            ['20', '20 rounds'],
        ],
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
    pass


class ComprehensionCheck(Page):
    form_model = 'player'
    form_fields = ['cq_endowment', 'cq_rating_cost', 'cq_rounds', 'cq_max_bonus']

    @staticmethod
    def error_message(player: Player, values):
        correct_answers = {
            'cq_endowment': '2.50',
            'cq_rating_cost': '0.25',
            'cq_rounds': '10',
            'cq_max_bonus': '10',
        }

        errors = {}
        for field_name, expected in correct_answers.items():
            if values[field_name] != expected:
                errors[field_name] = 'Please check the instructions and select the correct answer.'

        if errors:
            return errors


class PoliticalSurvey(Page):
    form_model = 'player'
    form_fields = ['politics_ideology', 'politics_interest', 'migration_policy', 'climate_priority']


class MovieRanking(Page):
    form_model = 'player'
    form_fields = ['ranking_json']

    @staticmethod
    def vars_for_template(player: Player):
        return dict(ranking_movies=C.MOVIES_FOR_RANKING)

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
