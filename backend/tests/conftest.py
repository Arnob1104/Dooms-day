import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def client():
    """API client backed by a fresh in-memory SQLite database per test."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # No `with` block on purpose: skips the startup hook that touches the real database.
    yield TestClient(app)
    app.dependency_overrides.clear()


# Sample data from the brief: title -> (runtime, [prerequisite titles])
SAMPLE = {
    "Iron Man": (126, []),
    "Captain America: The First Avenger": (124, []),
    "The Avengers": (143, ["Iron Man", "Captain America: The First Avenger"]),
    "Captain America: Civil War": (147, ["The Avengers"]),
    "Thor: Ragnarok": (130, []),
    "Avengers: Infinity War": (149, ["Captain America: Civil War", "Thor: Ragnarok"]),
    "Avengers: Endgame": (181, ["Avengers: Infinity War"]),
    "Avengers: Doomsday": (150, ["Avengers: Endgame"]),
}


@pytest.fixture()
def sample_movies(client) -> dict[str, int]:
    """Create the brief's example movies through the API; returns title -> id."""
    ids: dict[str, int] = {}
    for title, (runtime, prereqs) in SAMPLE.items():
        res = client.post(
            "/api/movies",
            json={
                "title": title,
                "release_year": 2010,
                "runtime_minutes": runtime,
                "prerequisite_ids": [ids[p] for p in prereqs],
            },
        )
        assert res.status_code == 201, res.text
        ids[title] = res.json()["id"]
    return ids
