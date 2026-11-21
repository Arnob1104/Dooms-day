-- Doomsday Ready: database schema for Supabase (Postgres).
--
-- Run this in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- It is optional: the API also creates these tables on startup if they are missing.
-- It is safe to run more than once.

create table if not exists public.movies (
    id               integer generated always as identity primary key,
    title            varchar(200) not null,
    release_year     integer      not null,
    runtime_minutes  integer      not null,
    watched          boolean      not null default false,
    constraint ck_movie_runtime check (runtime_minutes between 1 and 300)
);

-- Titles are unique, ignoring upper/lower case.
create unique index if not exists uq_movies_title_lower on public.movies (lower(title));

-- Self-referencing many-to-many: movie_id requires prerequisite_id to be watched first.
create table if not exists public.movie_prerequisites (
    movie_id         integer not null references public.movies (id) on delete cascade,
    prerequisite_id  integer not null references public.movies (id) on delete cascade,
    primary key (movie_id, prerequisite_id),
    constraint ck_no_self_prerequisite check (movie_id <> prerequisite_id)
);

create index if not exists ix_movie_prerequisites_prerequisite
    on public.movie_prerequisites (prerequisite_id);

create table if not exists public.cinemas (
    id            integer generated always as identity primary key,
    name          varchar(200) not null,
    -- Seat bundles sold for opening night, e.g. {2,5}. 1-10 sizes, 1-500 seats each.
    bundle_sizes  integer[]    not null,
    constraint ck_cinema_bundle_count check (cardinality(bundle_sizes) between 1 and 10)
);

create unique index if not exists uq_cinemas_name_lower on public.cinemas (lower(name));

-- Lock the tables away from Supabase's auto-generated public REST API (anon key).
-- The FastAPI backend connects directly as the database owner, which bypasses RLS,
-- so with RLS on and no policies nobody else can read or write this data.
alter table public.movies              enable row level security;
alter table public.movie_prerequisites enable row level security;
alter table public.cinemas             enable row level security;
