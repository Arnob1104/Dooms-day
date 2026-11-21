from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MIN_YEAR, MAX_YEAR = 1888, 2100  # first film ever made .. far enough in the future


def _dedupe(ids: list[int]) -> list[int]:
    return list(dict.fromkeys(ids))


# ---------------------------------------------------------------- movies
class MovieCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    release_year: int = Field(ge=MIN_YEAR, le=MAX_YEAR)
    runtime_minutes: int = Field(ge=1, le=300)
    prerequisite_ids: list[int] = Field(default_factory=list)
    watched: bool = False

    @field_validator("prerequisite_ids")
    @classmethod
    def _unique_prereqs(cls, v: list[int]) -> list[int]:
        return _dedupe(v)


class MovieUpdate(BaseModel):
    """PATCH body: only the fields that are sent are changed."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    release_year: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR)
    runtime_minutes: int | None = Field(default=None, ge=1, le=300)
    prerequisite_ids: list[int] | None = None
    watched: bool | None = None

    @field_validator("prerequisite_ids")
    @classmethod
    def _unique_prereqs(cls, v: list[int] | None) -> list[int] | None:
        return None if v is None else _dedupe(v)

    @model_validator(mode="after")
    def _no_explicit_nulls(self) -> "MovieUpdate":
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class MovieOut(BaseModel):
    id: int
    title: str
    release_year: int
    runtime_minutes: int
    watched: bool
    prerequisite_ids: list[int]


class RewatchItem(BaseModel):
    id: int
    title: str
    release_year: int
    runtime_minutes: int
    watched: bool


class RewatchOut(BaseModel):
    movie_id: int
    movie_title: str
    order: list[RewatchItem]
    total_count: int
    watched_count: int
    remaining_runtime_minutes: int


# --------------------------------------------------------------- cinemas
BundleSize = Annotated[int, Field(ge=1, le=500)]


class CinemaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    bundle_sizes: list[BundleSize] = Field(min_length=1, max_length=10)

    @field_validator("bundle_sizes")
    @classmethod
    def _distinct_sizes(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("bundle sizes must all be different")
        return sorted(v)


class CinemaOut(BaseModel):
    id: int
    name: str
    bundle_sizes: list[int]


class BundleOut(BaseModel):
    size: int
    count: int


class BookingOut(BaseModel):
    cinema_id: int
    cinema_name: str
    group_size: int
    possible: bool
    total_bundles: int | None
    bundles: list[BundleOut]
    message: str
