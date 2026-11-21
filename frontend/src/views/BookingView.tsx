import { FormEvent, useEffect, useState } from "react";
import { api, errorMessage } from "../api";
import type { BookingQuote, Cinema } from "../types";

function parseSizes(text: string): number[] | string {
  const parts = text.split(/[\s,]+/).filter(Boolean);
  if (parts.length === 0) return "Enter at least one bundle size.";
  const nums = parts.map(Number);
  if (nums.some((n) => !Number.isInteger(n))) return "Bundle sizes must be whole numbers, like 2, 5.";
  return nums;
}

export default function BookingView() {
  const [cinemas, setCinemas] = useState<Cinema[]>([]);
  const [cinemaId, setCinemaId] = useState<number | null>(null);
  const [groupText, setGroupText] = useState("11");
  const [quote, setQuote] = useState<BookingQuote | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [sizesText, setSizesText] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function loadCinemas(selectId?: number) {
    try {
      const list = await api.listCinemas();
      setCinemas(list);
      if (selectId !== undefined) setCinemaId(selectId);
      else setCinemaId((cur) => cur ?? list[0]?.id ?? null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  useEffect(() => {
    void loadCinemas();
  }, []);

  const groupSize = Number(groupText);
  const groupValid = Number.isInteger(groupSize) && groupSize >= 1 && groupSize <= 10_000;

  // Re-quote whenever the cinema or group size changes (ignore stale responses).
  useEffect(() => {
    if (cinemaId === null || !groupValid) {
      setQuote(null);
      return;
    }
    let stale = false;
    api
      .bookingQuote(cinemaId, groupSize)
      .then((q) => {
        if (!stale) {
          setQuote(q);
          setError(null);
        }
      })
      .catch((e) => {
        if (!stale) {
          setQuote(null);
          setError(errorMessage(e));
        }
      });
    return () => {
      stale = true;
    };
  }, [cinemaId, groupSize, groupValid]);

  async function addCinema(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const sizes = parseSizes(sizesText);
    if (typeof sizes === "string") return setFormError(sizes);
    try {
      const created = await api.createCinema({ name: name.trim(), bundle_sizes: sizes });
      setName("");
      setSizesText("");
      await loadCinemas(created.id);
    } catch (err) {
      setFormError(errorMessage(err));
    }
  }

  const selected = cinemas.find((c) => c.id === cinemaId);

  return (
    <div className="grid">
      <section className="card">
        <h2>Book opening night</h2>
        {cinemas.length === 0 ? (
          <p className="muted">No cinemas yet. Add one on the right.</p>
        ) : (
          <div className="form">
            <label>
              Cinema
              <select value={cinemaId ?? ""} onChange={(e) => setCinemaId(Number(e.target.value))}>
                {cinemas.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            {selected && (
              <p className="muted small">
                Sells bundles of: {selected.bundle_sizes.join(", ")} seats
              </p>
            )}
            <label>
              Group size (1–10,000)
              <input
                type="number"
                min={1}
                max={10000}
                value={groupText}
                onChange={(e) => setGroupText(e.target.value)}
              />
            </label>
            {!groupValid && <p className="error">Enter a whole number between 1 and 10,000.</p>}
          </div>
        )}
        {error && <p className="error">{error}</p>}

        {quote &&
          (quote.possible ? (
            <div className="quote ok">
              <strong>
                {quote.total_bundles} bundle{quote.total_bundles === 1 ? "" : "s"} for {quote.group_size} seats
              </strong>
              <ul>
                {quote.bundles.map((b) => (
                  <li key={b.size}>
                    {b.size} seats × {b.count}
                  </li>
                ))}
              </ul>
              <p className="muted small">Exact fit: nobody pays for an empty seat.</p>
            </div>
          ) : (
            <div className="quote bad">
              <strong>Not possible</strong>
              <p>
                {quote.cinema_name} can't sell exactly {quote.group_size} seats with its bundle sizes. Try
                a different group size or cinema.
              </p>
            </div>
          ))}
      </section>

      <section className="card">
        <h2>Add a cinema</h2>
        <form onSubmit={addCinema} className="form">
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} />
          </label>
          <label>
            Bundle sizes (comma separated, 1–10 sizes, 1–500 seats each)
            <input
              value={sizesText}
              onChange={(e) => setSizesText(e.target.value)}
              placeholder="e.g. 2, 5"
              required
            />
          </label>
          {formError && <p className="error">{formError}</p>}
          <button className="btn">Add cinema</button>
        </form>
      </section>
    </div>
  );
}
