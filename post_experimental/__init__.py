from otree.api import *


doc = """
Post-experimental questionnaire and payment summary.
"""


class C(BaseConstants):
    NAME_IN_URL = 'post_experimental'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    ENDOWMENT = cu(2.50)
    RATING_COST = cu(0.25)
    BONUS_PER_CORRECT = cu(2)


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    clarity_instructions = models.IntegerField(
        choices=[1, 2, 3, 4, 5, 6, 7],
        widget=widgets.RadioSelect,
        label='How clear were the instructions? (1 = very unclear, 7 = very clear)',
    )
    system_understanding = models.IntegerField(
        choices=[1, 2, 3, 4, 5, 6, 7],
        widget=widgets.RadioSelect,
        label='How well do you think you understood how the recommendation system learns? (1 = not at all, 7 = very well)',
    )
    decision_difficulty = models.IntegerField(
        choices=[1, 2, 3, 4, 5, 6, 7],
        widget=widgets.RadioSelect,
        label='How difficult were your rating/skip decisions? (1 = very easy, 7 = very difficult)',
    )
    strategy_text = models.LongStringField(
        blank=True,
        label='Briefly describe your strategy (optional).',
    )
    comments = models.LongStringField(
        blank=True,
        label='Any additional comments? (optional)',
    )


class PostQuestionnaire(Page):
    form_model = 'player'
    form_fields = ['clarity_instructions', 'system_understanding', 'decision_difficulty', 'strategy_text', 'comments']


class FinalPaymentInfo(Page):
    @staticmethod
    def vars_for_template(player: Player):
        num_ratings = int(player.participant.vars.get('num_ratings_main', 0))
        total_cost = C.RATING_COST * num_ratings
        remaining_endowment = C.ENDOWMENT - total_cost

        true_ranking = player.participant.vars.get('true_movie_ranking', [])
        return dict(
            num_ratings=num_ratings,
            total_cost=total_cost,
            remaining_endowment=remaining_endowment,
            endowment=C.ENDOWMENT,
            bonus_per_correct=C.BONUS_PER_CORRECT,
            true_ranking=true_ranking,
        )


page_sequence = [PostQuestionnaire, FinalPaymentInfo]
