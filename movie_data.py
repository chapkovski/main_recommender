from pathlib import Path

import yaml


MOVIES_PATH = Path(__file__).resolve().parent / "data" / "movies.yaml"


def load_movies():
    with MOVIES_PATH.open("r", encoding="utf-8") as f:
        movies = yaml.safe_load(f) or []

    if not isinstance(movies, list):
        raise ValueError("data/movies.yaml must contain a list of movie objects.")

    required_keys = {"title", "category", "synopsis", "image"}
    for idx, movie in enumerate(movies, start=1):
        if not isinstance(movie, dict):
            raise ValueError(f"Movie #{idx} is not a mapping.")
        missing_keys = required_keys - set(movie.keys())
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise ValueError(f"Movie #{idx} is missing keys: {missing}")

    return movies


MOVIES = load_movies()
MOVIE_IDS = list(range(1, len(MOVIES) + 1))
NUM_ROUNDS = len(MOVIES)
