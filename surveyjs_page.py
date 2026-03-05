import json
import logging

from otree.api import Page
from starlette.datastructures import FormData


logger = logging.getLogger(__name__)


class SurveyJSPage(Page):
    survey_results_field = 'surveyResults'

    def process_survey_data(self, data):
        raise NotImplementedError

    @staticmethod
    def _serialize_value(value):
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        if value is None:
            return ''
        return str(value)

    def post(self):
        if not self.participant.is_browser_bot:
            try:
                raw = self._form_data.get(self.survey_results_field)
                if not raw:
                    raise ValueError('Missing surveyResults payload')

                survey_results = json.loads(raw)
                mapped_values = self.process_survey_data(survey_results) or {}

                # Keep a multidict-like wrapper (with getlist) for WTForms/oTree.
                existing_items = list(self._form_data.multi_items())
                filtered_items = [
                    (key, value)
                    for key, value in existing_items
                    if key not in mapped_values
                ]
                mapped_items = [
                    (field_name, self._serialize_value(value))
                    for field_name, value in mapped_values.items()
                ]
                self._form_data = FormData(filtered_items + mapped_items)
            except json.JSONDecodeError as exc:
                logger.error('Invalid SurveyJS JSON on %s: %s', self.__class__.__name__, exc)
                raise
            except Exception as exc:
                logger.error('Survey processing failed on %s: %s', self.__class__.__name__, exc)
                raise

        return super().post()
