# Movie Recommender Experiment (oTree)

Current app status (code in this repository) is:

- One session config: `movie_recommender`
- App sequence: `pre_experimental -> main -> post_experimental`
- Currency: `EUR`
- Main task rounds: `len(data/movies.yaml)` (currently 10 movies)

## End-to-end Flow

### 1) `pre_experimental` (1 round)

Current page sequence:

1. `Consent`
2. `InstructionsIntro`
3. `ComprehensionCheck`
4. `PolPage`
5. `MovieRanking`

Notes:

- `PoliticalSurvey` exists in code but is currently not in `page_sequence`.
- `MovieRanking` uses server-side TMDb search via `live_method`.
- Participants must rank exactly `tmdb_favorites_required` movies (default: `5`).

### 2) `main` (N rounds, N = number of movies)

Current page sequence:

1. `RatingDecision` (repeats each round)
2. `MainResults` (final round only)

Notes:

- Each round shows one movie from a participant-specific randomized order.
- Participants choose `skip` (no cost) or `rate` (cost `EUR 0.25`).
- Endowment is `EUR 2.50`.

### 3) `post_experimental` (1 round)

Current page sequence:

1. `PostQuestionnaire`
2. `FinalPaymentInfo`
3. `FinalForProlific` (displayed only when `for_prolific=True`)

Notes:

- `FinalForProlific` redirects to Prolific with configured completion code.

## Treatment Logic

Treatment is assigned in `pre_experimental.creating_session()` in a deterministic 4-cell cycle by `id_in_subsession`:

1. `heterogeneous_political`
2. `homogeneous_political`
3. `heterogeneous_neutral`
4. `homogeneous_neutral`

Stored fields:

- Participant-level: `treatment_heterogeneous`, `treatment_political`, `treatment_label` (`PARTICIPANT_FIELDS`)
- Player-level snapshots are also stored in both `pre_experimental.Player` and `main.Player`:
  - `treatment_heterogeneous`
  - `treatment_political`

Political/neutral statements are loaded from `data/polquestions.csv` (`name,text,treatment`, where treatment is `polarizing` or `neutral`).

## Data and Survey Definitions

- Movies: `data/movies.yaml` (required keys per movie: `title`, `category`, `synopsis`, `image`)
- SurveyJS YAML files loaded server-side through `survey_data.py`:
  - `data/survey_pre_comprehension.yaml`
  - `data/survey_pre_political.yaml`
  - `data/survey_main_rating.yaml`
  - `data/survey_post_questionnaire.yaml`
- `data/survey_pre_ranking.yaml` exists but is not currently used in page logic.

Shared SurveyJS runtime:

- `_static/global/surveyjs_runtime.js`
- `surveyjs_page.py` maps submitted `surveyResults` JSON into oTree form fields.

## Configuration (`settings.py`)

Default session options include:

- TMDb:
  - `tmdb_api_key_env_var='TMDB_API_KEY'`
  - `tmdb_search_base_url='https://api.themoviedb.org/3/search/movie'`
  - `tmdb_language='en-US'`
  - `tmdb_include_adult=False`
  - `tmdb_results_limit=12`
  - `tmdb_favorites_required=5`
  - `tmdb_debug_errors=False`
- Prolific:
  - `for_prolific=False`
  - `prolific_base_return_url='https://app.prolific.com/submissions/complete?cc='`
  - `prolific_return_code='CW6532UV'`
  - `prolific_no_id_code='NO_ID'`

## Local Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set environment variables (recommended):

```bash
TMDB_API_KEY="your_tmdb_api_key"
OTREE_ADMIN_PASSWORD="your_admin_password"
```

3. Start oTree:

```bash
otree devserver
```

4. Open the URL printed in the terminal.
