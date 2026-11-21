"""Sample data from the brief (not an official watch guide).

Run manually:   python -m app.seed
Or automatically on startup when SEED_SAMPLE_DATA=true and the tables are empty.
"""

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from .database import SessionLocal, engine
from .models import Base, Cinema, Movie, movie_prerequisites

# (title, year, runtime, [prerequisite titles])
# Avengers: Doomsday's runtime is a placeholder - it is not released yet.
MOVIES: list[tuple[str, int, int, list[str]]] = [
    ("Iron Man", 2008, 126, []),
    ("Captain America: The First Avenger", 2011, 124, []),
    ("The Avengers", 2012, 143, ["Iron Man", "Captain America: The First Avenger"]),
    ("Captain America: Civil War", 2016, 147, ["The Avengers"]),
    ("Thor: Ragnarok", 2017, 130, []),
    ("Avengers: Infinity War", 2018, 149, ["Captain America: Civil War", "Thor: Ragnarok"]),
    ("Avengers: Endgame", 2019, 181, ["Avengers: Infinity War"]),
    ("Avengers: Doomsday", 2026, 150, ["Avengers: Endgame"]),
]

# Bundle sets chosen to match the booking examples in the brief.
CINEMAS: list[tuple[str, list[int]]] = [
    ("Star Cineplex", [2, 5]),
    ("Grand Mall IMAX", [1, 3, 4]),
    ("Dhaka Premiere", [6, 9, 20]),
    ("Odd Seats Theatre", [4, 6]),
]


def seed(db: Session) -> bool:
    """Insert sample data if there are no movies yet. Returns True if it seeded."""
    if db.scalar(select(func.count()).select_from(Movie)):
        return False

    ids: dict[str, int] = {}
    for title, year, runtime, _ in MOVIES:
        movie = Movie(title=title, release_year=year, runtime_minutes=runtime, watched=False)
        db.add(movie)
        db.flush()
        ids[title] = movie.id

    edges = [
        {"movie_id": ids[title], "prerequisite_id": ids[pre]}
        for title, _, _, prereqs in MOVIES
        for pre in prereqs
    ]
    db.execute(insert(movie_prerequisites), edges)

    if not db.scalar(select(func.count()).select_from(Cinema)):
        for name, sizes in CINEMAS:
            db.add(Cinema(name=name, bundle_sizes=sizes))

    db.commit()
    return True


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        print("Seeded sample data." if seed(session) else "Movies already exist; nothing to do.")
