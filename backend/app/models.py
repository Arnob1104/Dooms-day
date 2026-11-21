from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Self-referencing many-to-many: (movie_id) needs (prerequisite_id) watched first.
movie_prerequisites = Table(
    "movie_prerequisites",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "prerequisite_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    CheckConstraint("movie_id <> prerequisite_id", name="ck_no_self_prerequisite"),
)


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    release_year: Mapped[int] = mapped_column(Integer)
    runtime_minutes: Mapped[int] = mapped_column(Integer)
    watched: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    __table_args__ = (
        CheckConstraint("runtime_minutes BETWEEN 1 AND 300", name="ck_movie_runtime"),
        # Case-insensitive uniqueness of titles.
        Index("uq_movies_title_lower", func.lower(title), unique=True),
    )


class Cinema(Base):
    __tablename__ = "cinemas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # integer[] on Postgres/Supabase, JSON on SQLite (used for tests / zero-setup dev).
    bundle_sizes: Mapped[list[int]] = mapped_column(
        ARRAY(Integer).with_variant(JSON(), "sqlite")
    )

    __table_args__ = (Index("uq_cinemas_name_lower", func.lower(name), unique=True),)
