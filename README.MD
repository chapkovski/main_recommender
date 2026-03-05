# Movie Recommender Experiment (oTree)

This repository contains an oTree experiment with three apps:

- `pre_experimental`: instructions, comprehension check, short survey, and private ranking task.
- `main`: repeated rate/skip movie decisions.
- `post_experimental`: debrief questionnaire and payment summary.

## Movie Data Source

Movie stimuli are defined in [`data/movies.yaml`](data/movies.yaml).

They are loaded by [`movie_data.py`](movie_data.py), which exposes:

- `MOVIES`
- `MOVIE_IDS`
- `NUM_ROUNDS`

`main` uses this data directly, and the number of rounds is computed as `len(MOVIES)`.

## Survey Definitions

SurveyJS definitions are stored in `data/*.yaml` and loaded server-side before rendering:

- `data/survey_main_rating.yaml`
- `data/survey_pre_comprehension.yaml`
- `data/survey_pre_political.yaml`
- `data/survey_pre_ranking.yaml`
- `data/survey_post_questionnaire.yaml`

Shared SurveyJS rendering assets:

- Runtime module: `_static/global/surveyjs_runtime.js`
- Reusable template includes: `main/includes/surveyjs_css.html`, `main/includes/surveyjs_js.html`, `main/includes/surveyjs_init.html`

## Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start oTree:

```bash
otree devserver
```

3. Open the local URL shown in the terminal.
