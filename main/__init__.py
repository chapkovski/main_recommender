from otree.api import *
import random


doc = """
Main experiment: 10 independent rating rounds.
"""


class C(BaseConstants):
    NAME_IN_URL = 'main'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 10

    ENDOWMENT = cu(2.50)
    RATING_COST = cu(0.25)
    BONUS_PER_CORRECT = cu(2)
    MAX_CORRECT = 5

    MOVIE_POOL = [
        'Civil War',
        'The Apprentice',
        'Oppenheimer',
        'Killers of the Flower Moon',
        'The Zone of Interest',
        '12.12: The Day',
        'Io Capitano',
        'Green Border',
        'Golda',
        'Rustin',
        'Napoleon',
        'The Old Oak',
        '20 Days in Mariupol',
        'Origin',
        'Article 370',
        "Bobi Wine: The People's President",
        'Seven Winters in Tehran',
        'Occupied City',
        'Cairo Conspiracy (Boy from Heaven)',
        "The Teachers' Lounge",
        'Main Atal Hoon',
        'The Kerala Story',
        'The Eternal Memory',
        'Four Daughters',
        'Argentina, 1985',
    ]


def creating_session(subsession: BaseSubsession):
    if subsession.round_number != 1:
        return

    for player in subsession.get_players():
        player.participant.vars['movie_order_main'] = random.sample(C.MOVIE_POOL, C.NUM_ROUNDS)


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

    def current_movie(self):
        movie_order = self.participant.vars['movie_order_main']
        return movie_order[self.round_number - 1]


class RatingDecision(Page):
    form_model = 'player'
    form_fields = ['decision', 'movie_rating']

    @staticmethod
    def vars_for_template(player: Player):
        movie = player.current_movie()
        spent_so_far = sum((round_player.round_cost for round_player in player.in_previous_rounds()), cu(0))
        remaining_budget = C.ENDOWMENT - spent_so_far
        return dict(
            movie_title=movie,
            round_number=player.round_number,
            total_rounds=C.NUM_ROUNDS,
            spent_so_far=spent_so_far,
            remaining_budget=remaining_budget,
        )

    @staticmethod
    def error_message(player: Player, values):
        if values.get('decision') == 'rate' and not values.get('movie_rating'):
            return 'Please provide a rating if you choose "Rate this movie".'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.movie_title = player.current_movie()
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
            num_ratings=num_ratings,
            total_cost=total_cost,
            remaining_endowment=remaining_endowment,
            endowment=C.ENDOWMENT,
        )


page_sequence = [RatingDecision, MainResults]
