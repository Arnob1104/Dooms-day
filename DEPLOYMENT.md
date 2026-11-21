# Deployment and Docker guide

This document explains how the project is containerised, how to run it with one command, and how to deploy it online. It is written so a reviewer can check every step.

## 1. Architecture

```
Browser
   |
   v
frontend  (nginx serving the React build)   port 3000 -> 80
   |   /api/*  is forwarded by nginx
   v
backend   (FastAPI + uvicorn)               port 8000
   |
   v
database  (Postgres: local container, or Supabase)
```

| Piece | Technology | Defined in |
|---|---|---|
| Frontend | React + TypeScript, built by Vite, served by nginx | `frontend/Dockerfile`, `frontend/nginx.conf` |
| Backend | FastAPI on Python 3.12 | `backend/Dockerfile` |
| Database | Postgres 16 container, or Supabase (Postgres) | `docker-compose.yml`, `supabase/schema.sql` |
| Orchestration | Docker Compose | `docker-compose.yml` |

## 2. What the Docker files do

**`docker-compose.yml`** starts three services with one command.

- `db`: `postgres:16-alpine` with a named volume (`pgdata`) so data survives restarts. A healthcheck (`pg_isready`) reports when it is ready.
- `backend`: built from `backend/Dockerfile`. It waits for `db` to be healthy (`depends_on: condition: service_healthy`), then creates the tables and loads the sample data. `DATABASE_URL` defaults to the local `db` container and can be overridden to point at Supabase.
- `frontend`: built from `frontend/Dockerfile`, published on port 3000.

**`backend/Dockerfile`**: Python slim image, installs `requirements.txt` first (so Docker caches that layer), copies the app, starts uvicorn on `$PORT` (default 8000).

**`frontend/Dockerfile`** is a multi-stage build. Stage 1 (Node) runs `npm ci` and `npm run build`. Stage 2 (nginx) contains only the built static files, so the final image is small and has no Node.

**`frontend/nginx.conf`** serves the React app and forwards every `/api/` request to `backend:8000`. The browser therefore talks to one address only, so no CORS setup is needed in Docker.

## 3. Run everything with one command

### Prerequisites

- Docker Desktop (Windows or Mac) or Docker Engine with the Compose plugin (Linux). Start Docker Desktop before running the command.
- Nothing else. No Python, Node or database needs to be installed.

### Steps

```bash
git clone <repository-url>
cd doomsday-ready
docker compose up --build
```

The first build takes a few minutes. When the logs show `Application startup complete`, open:

| What | URL |
|---|---|
| App | http://localhost:3000 |
| API health check | http://localhost:8000/api/health |
| Interactive API docs | http://localhost:8000/docs |

No `.env` file is needed. Without one, Compose uses the bundled Postgres and loads the sample data (8 movies, 4 cinemas).

To stop: press `Ctrl+C`. To stop and delete the containers and database data: `docker compose down -v`.

### Checklist for the reviewer

1. `http://localhost:8000/api/health` returns `{"status":"ok"}`.
2. The Movies tab lists 8 movies.
3. Rewatch Plan, choose *Avengers: Doomsday*: 7 movies appear in a valid order (Iron Man and Captain America before The Avengers, and so on), with a progress count and the remaining watch time.
4. Movies tab, edit *Iron Man* and tick *Avengers: Endgame* as its prerequisite, then save: a circular dependency error is shown and nothing changes.
5. Booking tab, choose *Dhaka Premiere* (bundles 6, 9, 20) with group size 44: 4 bundles (20 x 1, 9 x 2, 6 x 1).
6. Booking tab, choose *Odd Seats Theatre* (bundles 4, 6) with group size 7: "Not possible".
7. Optional: run the tests with `docker compose run --rm --entrypoint "" backend sh -c "pip install -q pytest httpx && pytest"`. Note that `tests/` is excluded from the image, so the simpler way is `cd backend && pip install -r requirements.txt && pytest` (45 tests).

### Using Supabase instead of the local database

1. Create a project at https://supabase.com.
2. In the dashboard, open **SQL Editor**, paste `supabase/schema.sql`, and run it (optional: the API also creates the tables on startup).
3. Open **Connect** (or Project Settings, Database) and copy the **Session pooler** connection string. Use the pooler rather than the direct host, because the direct host can be IPv6-only and fail inside Docker or on hosting platforms.
4. Create `.env` in the project root:

   ```
   DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<pooler-host>:5432/postgres
   SEED_SAMPLE_DATA=true
   ```

   URL-encode special characters in the password (for example `@` becomes `%40`).
5. Run `docker compose up --build` again. The local `db` container still starts but is not used.

## 4. Deploy online (free tier)

Setup: **Supabase** (database), **Render** (backend, uses the existing Dockerfile), **Vercel** (frontend).

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Doomsday Ready full-stack app"
git branch -M main
git remote add origin https://github.com/<username>/doomsday-ready.git
git push -u origin main
```

Create the empty repository on GitHub first. `.env` is git-ignored, so secrets are not uploaded. Confirm no `.env` file appears in the repository.

### Step 2: Database on Supabase

Follow "Using Supabase" above (steps 1 to 4) and keep the Session pooler connection string.

### Step 3: Backend on Render

1. On https://render.com choose **New, Web Service**, and connect the GitHub repository.
2. Settings:
   - **Root Directory:** `backend`
   - **Runtime / Language:** `Docker` (Render uses `backend/Dockerfile`)
   - **Instance type:** Free
3. Environment variables:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | the Session pooler string from Step 2 |
   | `SEED_SAMPLE_DATA` | `true` (loads sample data once, only if the tables are empty) |
   | `CORS_ORIGINS` | your Vercel URL, added in Step 5 |

4. Deploy. Then open `https://<service>.onrender.com/api/health`. It should return `{"status":"ok"}`.

The free plan sleeps after inactivity, so the first request can take about a minute.

### Step 4: Frontend on Vercel

1. On https://vercel.com choose **Add New, Project**, and import the repository.
2. Settings:
   - **Root Directory:** `frontend`
   - **Framework preset:** Vite (build command `npm run build`, output directory `dist`)
3. Environment variable:

   | Name | Value |
   |---|---|
   | `VITE_API_URL` | `https://<service>.onrender.com/api` |

   This is read at build time, so after changing it you must redeploy. It is needed because a static host has no nginx proxy to forward `/api`.
4. Deploy and note the URL, for example `https://doomsday-ready.vercel.app`.

### Step 5: Allow the frontend to call the backend (CORS)

In Render, set `CORS_ORIGINS` to the exact Vercel URL with no trailing slash:

```
CORS_ORIGINS=https://doomsday-ready.vercel.app
```

Save. Render redeploys automatically.

### Step 6: Verify the live site

Repeat the reviewer checklist from section 3 on the Vercel URL, then add the live links to the top of `README.md`:

```
Live app: https://doomsday-ready.vercel.app
Live API docs: https://<service>.onrender.com/docs
```

## 5. Environment variables

| Variable | Used by | Meaning | Default |
|---|---|---|---|
| `DATABASE_URL` | backend | Postgres connection string (Supabase or other). `postgres://` and `postgresql://` both work | local SQLite file (outside Docker), local Postgres container (Compose) |
| `SEED_SAMPLE_DATA` | backend | Load the sample movies and cinemas if the tables are empty | `false` (`true` in Compose) |
| `CORS_ORIGINS` | backend | Comma-separated list of browser origins allowed to call the API | `http://localhost:5173,http://localhost:3000` |
| `PORT` | backend | Port to listen on (set by hosts like Render) | `8000` |
| `VITE_API_URL` | frontend (build time) | API base URL when frontend and API are on different domains | `/api` |

## 6. Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop is not running. Start it and retry |
| Port 3000 or 8000 already in use | Stop the other program, or change the left-hand port in `docker-compose.yml` (for example `"3001:80"`) |
| Backend cannot reach Supabase | Use the Session pooler string, check the password, URL-encode special characters |
| Page shows "Cannot reach the server" | On Vercel: `VITE_API_URL` is missing or wrong, or Render is still waking up. In Docker: backend failed to start, check `docker compose logs backend` |
| Browser console shows a CORS error | `CORS_ORIGINS` does not exactly match the Vercel URL |
| Sample data did not appear | `SEED_SAMPLE_DATA` is not `true`, or the tables already contain movies. To start fresh locally: `docker compose down -v` then `docker compose up --build` |
| Stale old data or schema in Docker | `docker compose down -v` removes the database volume |
