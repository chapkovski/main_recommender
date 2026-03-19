from os import environ
from pathlib import Path


def load_dotenv():
    dotenv_path = Path(__file__).resolve().parent / '.env'
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in environ:
            environ[key] = value


load_dotenv()

ROOMS = [
    dict(
        name='movie_recommender_room',
        display_name='Movie Recommender Room',

    ),
]

SESSION_CONFIGS = [
    dict(
        name='movie_recommender',
        app_sequence=[
            'pre_experimental', 'main', 
            'post_experimental'
            ],
        num_demo_participants=2,
    ),
    # let's add post experimental only
    # dict(
    #     name='post_exp_only',
    #      app_sequence=['post_experimental'],
    #     num_demo_participants=1
    # )
    
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc='',
    for_prolific=False,
    prolific_base_return_url='https://app.prolific.com/submissions/complete?cc=',
    prolific_return_code='CW6532UV',
    prolific_no_id_code='NO_ID',
    tmdb_api_key_env_var='TMDB_API_KEY',
    tmdb_search_base_url='https://api.themoviedb.org/3/search/movie',
    tmdb_language='en-US',
    tmdb_include_adult=False,
    tmdb_results_limit=12,
    tmdb_favorites_required=5,
    tmdb_debug_errors=False,
)

PARTICIPANT_FIELDS = [
    'treatment_heterogeneous',
    'treatment_political',
    'treatment_label',
    'pol_question_order',
    'pol_answers_json',
]
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = False

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '9892210719987'
