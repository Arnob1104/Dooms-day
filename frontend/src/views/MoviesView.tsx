import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, errorMessage, formatMinutes } from "../api";
import type { Movie } from "../types";

interface PickerProps {
  movies: Movie[];
  selected: number[];
  excludeId?: number;
  onChange: (ids: number[]) => void;
}

function PrerequisitePicker({ movies, selected, excludeId, onChange }: PickerProps) {
  const options = movies.filter((m) => m.id !== excludeId);
  if (options.length === 0) return <p className="muted">No other movies yet.</p>;
  const toggle = (id: number) =>
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  return (
    <div className="picker">
      {options.map((m) => (
        <label key={m.id} className="chip">
          <input type="checkbox" checked={selected.includes(m.id)} onChange={() => toggle(m.id)} />
          {m.title}
        </label>
      ))}
    </div>
  );
}

interface RowProps {
  movie: Movie;
  movies: Movie[];
  onChanged: () => Promise<void>;
}

function MovieRow({ movie, movies, onChanged }: RowProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<number[]>(movie.prerequisite_ids);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const titleOf = (id: number) => movies.find((m) => m.id === id)?.title ?? `#${id}`;

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await onChanged();
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function savePrerequisites() {
    if (await run(() => api.updateMovie(movie.id, { prerequisite_ids: draft }))) setEditing(false);
  }

  return (
    <li className={movie.watched ? "movie watched" : "movie"}>
      <div className="movie-main">
        <label className="check">
          <input
            type="checkbox"
            checked={movie.watched}
            disabled={busy}
            onChange={() => run(() => api.updateMovie(movie.id, { watched: !movie.watched }))}
            aria-label={`Mark ${movie.title} as watched`}
          />
        </label>
        <div className="movie-info">
          <strong>{movie.title}</strong>
          <span className="muted">
            {movie.release_year} · {formatMinutes(movie.runtime_minutes)}
          </span>
          <span className="muted small">
            {movie.prerequisite_ids.length === 0
              ? "No prerequisites"
              : `Watch first: ${movie.prerequisite_ids.map(titleOf).join(", ")}`}
          </span>
        </div>
        <button
          className="btn ghost"
          onClick={() => {
            setDraft(movie.prerequisite_ids);
            setError(null);
            setEditing((v) => !v);
          }}
        >
          {editing ? "Cancel" : "Edit prerequisites"}
        </button>
      </div>
      {editing && (
        <div className="editor">
          <PrerequisitePicker movies={movies} selected={draft} excludeId={movie.id} onChange={setDraft} />
          <button className="btn" disabled={busy} onClick={savePrerequisites}>
            Save prerequisites
          </button>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </li>
  );
}

export default function MoviesView() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [year, setYear] = useState("2024");
  const [runtime, setRuntime] = useState("120");
  const [prereqs, setPrereqs] = useState<number[]>([]);
  const [watched, setWatched] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setMovies(await api.listMovies());
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function addMovie(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api.createMovie({
        title: title.trim(),
        release_year: Number(year),
        runtime_minutes: Number(runtime),
        prerequisite_ids: prereqs,
        watched,
      });
      setTitle("");
      setPrereqs([]);
      setWatched(false);
      await load();
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid">
      <section className="card">
        <h2>Add a movie</h2>
        <form onSubmit={addMovie} className="form">
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} />
          </label>
          <div className="row">
            <label>
              Release year
              <input type="number" min={1888} max={2100} value={year} onChange={(e) => setYear(e.target.value)} required />
            </label>
            <label>
              Runtime (min)
              <input type="number" min={1} max={300} value={runtime} onChange={(e) => setRuntime(e.target.value)} required />
            </label>
          </div>
          <fieldset>
            <legend>Watch these first (optional)</legend>
            <PrerequisitePicker movies={movies} selected={prereqs} onChange={setPrereqs} />
          </fieldset>
          <label className="inline">
            <input type="checkbox" checked={watched} onChange={(e) => setWatched(e.target.checked)} />
            Already watched
          </label>
          {formError && <p className="error">{formError}</p>}
          <button className="btn" disabled={saving}>
            {saving ? "Adding…" : "Add movie"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>
          Movies <span className="muted">({movies.length})</span>
        </h2>
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && movies.length === 0 && (
          <p className="muted">No movies yet. Add your first one on the left.</p>
        )}
        <ul className="list">
          {movies.map((m) => (
            <MovieRow key={m.id} movie={m} movies={movies} onChanged={load} />
          ))}
        </ul>
      </section>
    </div>
  );
}
