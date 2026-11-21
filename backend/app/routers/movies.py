from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..algorithms import CycleError, creates_cycle, rewatch_order
from ..database import get_db
from ..errors import AppError
from ..models import Movie, movie_prerequisites
from ..schemas import MovieCreate, MovieOut, MovieUpdate, RewatchItem, RewatchOut

router = APIRouter(prefix="/movies", tags=["movies"])

def circular_error(message: str) -> AppError:
    return AppError(409, "CIRCULAR_DEPENDENCY", message)


# ------------------------------------------------------------------ helpers
def load_graph(db: Session) -> dict[int, list[int]]:
    """movie id -> list of its prerequisite ids (whole graph, one query)."""
    graph: dict[int, list[int]] = {}
    rows = db.execute(
        select(movie_prerequisites.c.movie_id, movie_prerequisites.c.prerequisite_id).order_by(
            movie_prerequisites.c.movie_id, movie_prerequisites.c.prerequisite_id
        )
    )
    for movie_id, prerequisite_id in rows:
        graph.setdefault(movie_id, []).append(prerequisite_id)
    return graph


def get_movie_or_404(db: Session, movie_id: int) -> Movie:
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise AppError(404, "MOVIE_NOT_FOUND", f"Movie {movie_id} does not exist")
    return movie


def ensure_prerequisites_exist(db: Session, ids: list[int]) -> None:
    if not ids:
        return
    found = set(db.scalars(select(Movie.id).where(Movie.id.in_(ids))))
    missing = sorted(set(ids) - found)
    if missing:
        raise AppError(422, "UNKNOWN_PREREQUISITE", f"Unknown prerequisite movie id(s): {missing}")


def ensure_title_free(db: Session, title: str, exclude_id: int | None = None) -> None:
    query = select(Movie.id).where(func.lower(Movie.title) == title.lower())
    if exclude_id is not None:
        query = query.where(Movie.id != exclude_id)
    if db.scalar(query) is not None:
        raise AppError(409, "DUPLICATE_TITLE", f"A movie titled '{title}' already exists")


def replace_prerequisites(db: Session, movie_id: int, ids: list[int]) -> None:
    db.execute(delete(movie_prerequisites).where(movie_prerequisites.c.movie_id == movie_id))
    if ids:
        db.execute(
            insert(movie_prerequisites),
            [{"movie_id": movie_id, "prerequisite_id": pid} for pid in ids],
        )


def to_out(movie: Movie, prerequisite_ids: list[int]) -> MovieOut:
    return MovieOut(
        id=movie.id,
        title=movie.title,
        release_year=movie.release_year,
        runtime_minutes=movie.runtime_minutes,
        watched=movie.watched,
        prerequisite_ids=sorted(prerequisite_ids),
    )


def commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:  # lost a race on the unique title index
        db.rollback()
        raise AppError(409, "DUPLICATE_TITLE", "A movie with that title already exists") from exc


# ---------------------------------------------------------------- endpoints
@router.post("", response_model=MovieOut, status_code=201)
def create_movie(payload: MovieCreate, db: Session = Depends(get_db)) -> MovieOut:
    ensure_title_free(db, payload.title)
    ensure_prerequisites_exist(db, payload.prerequisite_ids)

    # A brand-new movie has no id yet, so nothing can depend on it and it cannot
    # be part of a cycle: no cycle check is needed on create.
    movie = Movie(
        title=payload.title,
        release_year=payload.release_year,
        runtime_minutes=payload.runtime_minutes,
        watched=payload.watched,
    )
    db.add(movie)
    db.flush()
    replace_prerequisites(db, movie.id, payload.prerequisite_ids)
    commit_or_conflict(db)
    return to_out(movie, payload.prerequisite_ids)


@router.get("", response_model=list[MovieOut])
def list_movies(db: Session = Depends(get_db)) -> list[MovieOut]:
    graph = load_graph(db)
    movies = db.scalars(select(Movie).order_by(Movie.id))
    return [to_out(m, graph.get(m.id, [])) for m in movies]


@router.patch("/{movie_id}", response_model=MovieOut)
def update_movie(movie_id: int, payload: MovieUpdate, db: Session = Depends(get_db)) -> MovieOut:
    movie = get_movie_or_404(db, movie_id)
    changes = payload.model_dump(exclude_unset=True)

    if "title" in changes:
        ensure_title_free(db, changes["title"], exclude_id=movie_id)

    graph = load_graph(db)
    if "prerequisite_ids" in changes:
        new_ids = changes["prerequisite_ids"]
        ensure_prerequisites_exist(db, new_ids)
        if creates_cycle(movie_id, new_ids, graph):
            raise circular_error(
                f"Movie {movie_id} cannot depend on itself, directly or through other movies"
            )
        replace_prerequisites(db, movie_id, new_ids)
        graph[movie_id] = list(new_ids)

    for field in ("title", "release_year", "runtime_minutes", "watched"):
        if field in changes:
            setattr(movie, field, changes[field])

    commit_or_conflict(db)
    return to_out(movie, graph.get(movie_id, []))


@router.get("/{movie_id}/rewatch-order", response_model=RewatchOut)
def get_rewatch_order(movie_id: int, db: Session = Depends(get_db)) -> RewatchOut:
    target = get_movie_or_404(db, movie_id)
    try:
        ordered_ids = rewatch_order(movie_id, load_graph(db))
    except CycleError as exc:  # unreachable unless the data was edited behind our back
        raise circular_error(str(exc)) from exc

    by_id = (
        {m.id: m for m in db.scalars(select(Movie).where(Movie.id.in_(ordered_ids)))}
        if ordered_ids
        else {}
    )
    items = [
        RewatchItem(
            id=by_id[i].id,
            title=by_id[i].title,
            release_year=by_id[i].release_year,
            runtime_minutes=by_id[i].runtime_minutes,
            watched=by_id[i].watched,
        )
        for i in ordered_ids
    ]
    return RewatchOut(
        movie_id=target.id,
        movie_title=target.title,
        order=items,
        total_count=len(items),
        watched_count=sum(1 for i in items if i.watched),
        remaining_runtime_minutes=sum(i.runtime_minutes for i in items if not i.watched),
    )
