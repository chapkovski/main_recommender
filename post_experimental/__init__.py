from os import environ

from otree.api import *
import json

from starlette.responses import RedirectResponse

from survey_data import load_survey_definition
from surveyjs_page import SurveyJSPage


doc = """
Post-experimental questionnaire and payment summary.
"""

POST_QUESTIONNAIRE_SURVEY_DEFINITION = load_survey_definition('survey_post_questionnaire.yaml')
POST_DEMOGRAPHICS_SURVEY_DEFINITION = load_survey_definition('survey_post_demographics.yaml')


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
    age = models.IntegerField(
        min=18,
        max=100,
        label='What is your age?',
    )
    gender = models.StringField(
        label='What is your gender?',
    )
    education = models.StringField(
        label='What is the highest level of education you have completed?',
    )
    income = models.StringField(
        label='What is your annual personal income?',
    )
    marital_status = models.StringField(
        label='What is your current marital status?',
    )
    employment_status = models.StringField(
        label='What is your current employment status?',
    )


class PostQuestionnaire(SurveyJSPage):
    form_model = 'player'
    form_fields = ['clarity_instructions', 'system_understanding', 'decision_difficulty', 'strategy_text', 'comments']

    @staticmethod
    def vars_for_template(player: Player):
        return dict(survey_json=json.dumps(POST_QUESTIONNAIRE_SURVEY_DEFINITION))

    def process_survey_data(self, data):
        return dict(
            clarity_instructions=data.get('clarity_instructions'),
            system_understanding=data.get('system_understanding'),
            decision_difficulty=data.get('decision_difficulty'),
            strategy_text=data.get('strategy_text'),
            comments=data.get('comments'),
        )


class Demographics(SurveyJSPage):
    form_model = 'player'
    form_fields = ['age', 'gender', 'education', 'income', 'marital_status', 'employment_status']

    @staticmethod
    def vars_for_template(player: Player):
        return dict(survey_json=json.dumps(POST_DEMOGRAPHICS_SURVEY_DEFINITION))

    def process_survey_data(self, data):
        return dict(
            age=data.get('age'),
            gender=data.get('gender'),
            education=data.get('education'),
            income=data.get('income'),
            marital_status=data.get('marital_status'),
            employment_status=data.get('employment_status'),
        )


class FinalPaymentInfo(Page):
    @staticmethod
    def vars_for_template(player: Player):
        num_ratings = int(player.participant.vars.get('num_ratings_main', 0))
        total_cost = C.RATING_COST * num_ratings
        remaining_endowment = C.ENDOWMENT - total_cost

        true_ranking_raw = player.participant.vars.get('true_movie_ranking', [])
        if true_ranking_raw and isinstance(true_ranking_raw[0], dict):
            true_ranking = [item.get('title', '') for item in true_ranking_raw if item.get('title')]
        else:
            true_ranking = true_ranking_raw
        return dict(
            num_ratings=num_ratings,
            total_cost=total_cost,
            remaining_endowment=remaining_endowment,
            endowment=C.ENDOWMENT,
            bonus_per_correct=C.BONUS_PER_CORRECT,
            true_ranking=true_ranking,
        )


class FinalForProlific(Page):
    @staticmethod
    def is_displayed(player: Player):
        return (
            player.round_number == C.NUM_ROUNDS
            and player.session.config.get('for_prolific', False)
            and player.session.config['app_sequence'][-1] == C.NAME_IN_URL
        )

    def get(self):
        base_return_url = self.session.config.get(
            'prolific_base_return_url',
            'https://app.prolific.com/submissions/complete?cc=',
        )
        if not self.participant.label:
            ending = self.session.config.get('prolific_no_id_code', 'NO_ID')
        else:
            ending = self.session.config.get(
                'prolific_return_code',
                environ.get('DEFAULT_PROLIFIC_CODE', 'CW6532UV'),
            )
        return RedirectResponse(f'{base_return_url}{ending}')


page_sequence = [
    PostQuestionnaire,
    Demographics,
    FinalPaymentInfo, FinalForProlific]
