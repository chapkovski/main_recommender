from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import yaml


SURVEY_DATA_DIR = Path(__file__).resolve().parent / 'data'


@lru_cache(maxsize=None)
def _read_survey_yaml(filename):
    path = SURVEY_DATA_DIR / filename
    with path.open('r', encoding='utf-8') as f:
        definition = yaml.safe_load(f) or {}

    if not isinstance(definition, dict):
        raise ValueError(f'{path} must contain a mapping at root.')

    return definition


def load_survey_definition(filename):
    return deepcopy(_read_survey_yaml(filename))
