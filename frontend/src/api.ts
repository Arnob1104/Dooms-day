import type { BookingQuote, Cinema, Movie, NewMovie, RewatchPlan } from "./types";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Cannot reach the server. Is the API running?", 0, "NETWORK");
  }
  if (!res.ok) {
    let code = "ERROR";
    let message = `Request failed (${res.status})`;
    try {
      const body = (await res.json()) as { error?: string; message?: string };
      code = body.error ?? code;
      message = body.message ?? message;
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(message, res.status, code);
  }
  return (await res.json()) as T;
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError && e.code === "CIRCULAR_DEPENDENCY") {
    return "Circular dependency: a movie can't require itself, directly or through other movies.";
  }
  return e instanceof Error ? e.message : "Something went wrong";
}

export const api = {
  listMovies: () => request<Movie[]>("/movies"),
  createMovie: (body: NewMovie) =>
    request<Movie>("/movies", { method: "POST", body: JSON.stringify(body) }),
  updateMovie: (id: number, body: Partial<Pick<Movie, "watched" | "prerequisite_ids">>) =>
    request<Movie>(`/movies/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  rewatchOrder: (id: number) => request<RewatchPlan>(`/movies/${id}/rewatch-order`),
  listCinemas: () => request<Cinema[]>("/cinemas"),
  createCinema: (body: { name: string; bundle_sizes: number[] }) =>
    request<Cinema>("/cinemas", { method: "POST", body: JSON.stringify(body) }),
  bookingQuote: (cinemaId: number, groupSize: number) =>
    request<BookingQuote>(`/cinemas/${cinemaId}/booking?groupSize=${groupSize}`),
};

export function formatMinutes(total: number): string {
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h === 0) return `${m}m`;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}
