import { useCallback, useEffect, useState } from "react";
import { api, errorMessage, formatMinutes } from "../api";
import type { Movie, RewatchPlan } from "../types";

export default function RewatchView() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [targetId, setTargetId] = useState<number | null>(null);
  const [plan, setPlan] = useState<RewatchPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listMovies()
      .then((list) => {
        setMovies(list);
        // Default to the newest movie: normally the one everyone is preparing for.
        if (list.length > 0) setTargetId(list[list.length - 1].id);
      })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  }, []);

  const loadPlan = useCallback(async (id: number) => {
    try {
      setPlan(await api.rewatchOrder(id));
      setError(null);
    } catch (e) {
      setPlan(null);
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    if (targetId !== null) void loadPlan(targetId);
  }, [targetId, loadPlan]);

  async function toggle(id: number, watched: boolean) {
    try {
      await api.updateMovie(id, { watched: !watched });
      if (targetId !== null) await loadPlan(targetId);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  const pct = plan && plan.total_count > 0 ? Math.round((plan.watched_count / plan.total_count) * 100) : 0;

  return (
    <section className="card narrow">
      <h2>Rewatch plan</h2>
      {loading && <p className="muted">Loading…</p>}
      {!loading && movies.length === 0 && (
        <p className="muted">Add some movies first on the Movies tab.</p>
      )}
      {movies.length > 0 && (
        <label className="form">
          I want to watch
          <select value={targetId ?? ""} onChange={(e) => setTargetId(Number(e.target.value))}>
            {movies.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title}
              </option>
            ))}
          </select>
        </label>
      )}
      {error && <p className="error">{error}</p>}

      {plan && (
        <>
          {plan.total_count === 0 ? (
            <p className="callout">
              Nothing to catch up on. <strong>{plan.movie_title}</strong> has no prerequisites.
            </p>
          ) : (
            <>
              <div className="progress-head">
                <strong>
                  {plan.watched_count} of {plan.total_count} watched
                </strong>
                <span className="muted">
                  {plan.remaining_runtime_minutes === 0
                    ? "All caught up!"
                    : `${formatMinutes(plan.remaining_runtime_minutes)} left to watch`}
                </span>
              </div>
              <div
                className="progress"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={plan.total_count}
                aria-valuenow={plan.watched_count}
              >
                <div className="progress-bar" style={{ width: `${pct}%` }} />
              </div>
              <ol className="steps">
                {plan.order.map((m, i) => (
                  <li key={m.id} className={m.watched ? "step done" : "step"}>
                    <span className="step-num">{i + 1}</span>
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={m.watched}
                        onChange={() => toggle(m.id, m.watched)}
                        aria-label={`Mark ${m.title} as watched`}
                      />
                    </label>
                    <span className="step-title">{m.title}</span>
                    <span className="muted small">
                      {m.release_year} · {formatMinutes(m.runtime_minutes)}
                    </span>
                  </li>
                ))}
              </ol>
              <p className="muted small">Then you're ready for {plan.movie_title}.</p>
            </>
          )}
        </>
      )}
    </section>
  );
}
