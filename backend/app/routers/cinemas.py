from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..algorithms import min_bundles
from ..database import get_db
from ..errors import AppError
from ..models import Cinema
from ..schemas import BookingOut, BundleOut, CinemaCreate, CinemaOut

router = APIRouter(prefix="/cinemas", tags=["cinemas"])


def to_out(cinema: Cinema) -> CinemaOut:
    return CinemaOut(id=cinema.id, name=cinema.name, bundle_sizes=list(cinema.bundle_sizes))


@router.post("", response_model=CinemaOut, status_code=201)
def create_cinema(payload: CinemaCreate, db: Session = Depends(get_db)) -> CinemaOut:
    taken = db.scalar(select(Cinema.id).where(func.lower(Cinema.name) == payload.name.lower()))
    if taken is not None:
        raise AppError(409, "DUPLICATE_NAME", f"A cinema named '{payload.name}' already exists")

    cinema = Cinema(name=payload.name, bundle_sizes=payload.bundle_sizes)
    db.add(cinema)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "DUPLICATE_NAME", "A cinema with that name already exists") from exc
    return to_out(cinema)


@router.get("", response_model=list[CinemaOut])
def list_cinemas(db: Session = Depends(get_db)) -> list[CinemaOut]:
    return [to_out(c) for c in db.scalars(select(Cinema).order_by(Cinema.id))]


@router.get("/{cinema_id}/booking", response_model=BookingOut)
def get_booking_quote(
    cinema_id: int,
    group_size: int = Query(alias="groupSize", ge=1, le=10_000),
    db: Session = Depends(get_db),
) -> BookingOut:
    cinema = db.get(Cinema, cinema_id)
    if cinema is None:
        raise AppError(404, "CINEMA_NOT_FOUND", f"Cinema {cinema_id} does not exist")

    result = min_bundles(list(cinema.bundle_sizes), group_size)
    if result is None:
        return BookingOut(
            cinema_id=cinema.id,
            cinema_name=cinema.name,
            group_size=group_size,
            possible=False,
            total_bundles=None,
            bundles=[],
            message=f"Not possible: no combination of bundles adds up to exactly {group_size} seats",
        )

    total = sum(b.count for b in result)
    return BookingOut(
        cinema_id=cinema.id,
        cinema_name=cinema.name,
        group_size=group_size,
        possible=True,
        total_bundles=total,
        bundles=[BundleOut(size=b.size, count=b.count) for b in result],
        message=f"{total} bundle{'s' if total != 1 else ''}: "
        + ", ".join(f"{b.size} × {b.count}" for b in result),
    )
