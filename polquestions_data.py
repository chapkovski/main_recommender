import csv
from pathlib import Path


POLQUESTIONS_PATH = Path(__file__).resolve().parent / 'data' / 'polquestions.csv'


def load_polquestions():
    with POLQUESTIONS_PATH.open('r', encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))

    questions = []
    for idx, row in enumerate(rows, start=1):
        name = (row.get('name') or '').strip()
        text = (row.get('text') or '').strip()
        treatment = (row.get('treatment') or '').strip().lower()

        if not name or not text or treatment not in {'polarizing', 'neutral'}:
            raise ValueError(f'Invalid row #{idx} in data/polquestions.csv')

        questions.append(
            dict(
                name=name,
                text=text,
                treatment=treatment,
            )
        )

    if not questions:
        raise ValueError('data/polquestions.csv is empty')

    return questions


LIKERT6_CHOICES = [
    dict(value='1', text='Strongly Disagree'),
    dict(value='2', text='Moderately Disagree'),
    dict(value='3', text='Slightly Disagree'),
    dict(value='4', text='Slightly Agree'),
    dict(value='5', text='Moderately Agree'),
    dict(value='6', text='Strongly Agree'),
]

LIKERT6_LABELS = {choice['value']: choice['text'] for choice in LIKERT6_CHOICES}

POL_QUESTIONS = load_polquestions()
POL_QUESTION_NAMES = [q['name'] for q in POL_QUESTIONS]
POL_QUESTIONS_BY_NAME = {q['name']: q for q in POL_QUESTIONS}
