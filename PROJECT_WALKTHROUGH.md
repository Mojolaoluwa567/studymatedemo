# StudyMate — Full Project Walkthrough

This document explains every part of the project: what each file does, how
the pieces connect, and how data flows through the system from signup to
quiz results. Read it top to bottom once and you'll understand the whole
codebase well enough to explain or extend it yourself.

---

## 1. The big picture

StudyMate is a **client-server web app**:

- The **frontend** (`frontend/`) is a React app. It runs in the user's
  browser. It has no database access and no secrets — it only knows how to
  display things and make HTTP requests.
- The **backend** (`backend/`) is a Flask (Python) app. It owns the
  database, handles authentication, talks to the Gemini AI API, and exposes
  a REST API (a set of URLs that return JSON).

They are two **completely separate programs** that talk to each other over
HTTP. In development they run on different ports:
- Backend: `http://localhost:5000`
- Frontend: `http://localhost:5173`

The frontend is configured (via `frontend/.env` → `VITE_API_URL`) to know
where the backend lives. Every button click that needs data calls a function
in `frontend/src/api.js`, which sends a `fetch()` request to that URL.

---

## 2. Backend — file by file

### `backend/app.py` — the main application

This is the entry point. It does four things:

1. **Configuration** — reads settings from environment variables (loaded
   from `.env` via `load_dotenv()`):
   - `SECRET_KEY` / `JWT_SECRET_KEY` — used to cryptographically sign
     session tokens, so they can't be forged.
   - `DATABASE_URL` — defaults to a local SQLite file `app.db`.
   - `FRONTEND_ORIGIN` — tells Flask-CORS which frontend URL is allowed to
     call this API (browsers block cross-origin requests unless the server
     explicitly allows them).

2. **Extension setup** — initializes:
   - `db` (SQLAlchemy) — the database connection/ORM.
   - `bcrypt` — for hashing passwords (never store plain passwords).
   - `jwt` — for issuing and verifying login tokens.
   - `CORS` — cross-origin permission.

3. **Routes** — every `@app.route(...)` function is one API endpoint. Each
   one: reads the request (`request.get_json()` or `request.files`),
   does something (query/update the database, call helper modules), and
   returns `jsonify(...)`.

4. **Startup** — `db.create_all()` creates the SQLite tables if they don't
   exist yet, and `app.run()` starts the dev server.

#### Endpoints, grouped by purpose:

**Auth**
- `POST /signup` — takes `{username, password}`, hashes the password with
  bcrypt, stores a new `User` row.
- `POST /login` — checks the username/password, and if correct, returns a
  JWT access token (a signed string that proves "this is user #N").
- `GET /profile` — example of a protected route; requires a valid token.

**Documents**
- `POST /documents` — accepts a PDF file upload (`multipart/form-data`),
  extracts its text via `pdf_utils.py`, and saves a `Document` row.
- `GET /documents` — lists the logged-in user's documents.
- `GET /documents/<id>` — returns one document including its full text
  (used by the Study page to display the reading material).

**Study sessions**
- `POST /study-sessions` — logs `{document_id, duration_seconds}` every time
  the user finishes a study timer session. These accumulate over time.

**Quizzes**
- `GET /quizzes/config` — returns the difficulty/marking configuration
  (question counts, marks, time limits) so the frontend can display options
  without hardcoding them.
- `POST /quizzes` — the core AI step. Given `{document_id, difficulty,
  easy_mode}`, it calls `quiz_generator.generate_quiz_questions(...)`, which
  asks Gemini to write quiz questions from the document's text. The
  generated questions are saved as `Quiz` + `Question` rows, and returned
  to the frontend **without** the correct answers.
- `GET /quizzes/<id>` — re-fetches a quiz's questions (also without answers)
  — used if the Quiz page needs to reload.

**Attempts (taking + grading a quiz)**
- `POST /attempts` — called when the user starts a quiz. Creates an
  `Attempt` row, snapshots the user's total study time for this document so
  far (`study_time_seconds`), and returns the time limit.
- `POST /attempts/<id>/submit` — the grading step. For each question:
  - **MCQ**: `grading.grade_mcq()` does a simple string comparison against
    the stored correct answer — instant, no AI needed.
  - **Theory**: all theory answers are sent together to
    `grading.grade_theory_batch()`, which asks Gemini to score each one
    against the stored marking points and give feedback.
  Scores are summed into `Attempt.total_score` / `percentage`, and a full
  per-question breakdown is returned to the frontend for the Results page.
- `GET /attempts` — list of all past attempts (for history).

**Performance**
- `GET /documents/<id>/performance` — aggregates all attempts for one
  document into a list (used to draw the score-over-time chart) plus the
  total study time logged.

---

### `backend/extensions.py`

Tiny file — just creates the `db`, `bcrypt`, `jwt` objects *without*
attaching them to the app yet. This avoids a "circular import" problem:
`models.py` needs `db`, and `app.py` needs both `models` and `db`. By
defining `db` in its own file, both can import it safely.

---

### `backend/models.py` — the database schema

Each class is a **table**. SQLAlchemy turns these Python classes into SQL
tables automatically. The relationships (`db.relationship(...)`) let you
write `user.documents` or `quiz.questions` and get the related rows without
writing SQL joins yourself.

```
User
 ├── Document (one user, many documents)
 │     ├── StudySession (timer logs)
 │     └── Quiz
 │           └── Question (the generated questions)
 └── Attempt (one per quiz-taking session)
       └── Answer (one per question, per attempt)
```

Key fields to know:
- `Question.correct_answer` — for MCQ, this is the letter ("A"/"B"/etc).
  For theory questions, it's actually the **model answer / marking points**
  text used later for grading — same field, different meaning depending on
  `Question.type`.
- `Attempt.study_time_seconds` — a *snapshot* taken at attempt-start time of
  how much total study time existed for that document. This is what lets
  the Performance page correlate "score vs. how much you'd studied so far."

---

### `backend/pdf_utils.py`

Uses the `pdfplumber` library to open an uploaded PDF and pull out the text
from every page, joining it into one big string. `MAX_CHARS` (18,000)
truncates the text before sending it to Gemini — large PDFs would otherwise
exceed the AI's context limits. The full text is still stored in the
database for the Study page.

---

### `backend/quiz_generator.py` — the AI prompt engineering

This is the most "AI" part of the project. Walk through it like this:

1. `get_quiz_plan(difficulty, easy_mode)` — pure Python, no AI. Returns a
   dict describing *how many* questions of each type, how many marks each
   is worth, and the time limit. This is where the "60Q@1mark vs
   30Q@2marks" easy-mode choice and the hard/difficult compositions
   (14 MCQ + 6 theory, etc.) are defined as constants
   (`EASY_MODES`, `HARD_CONFIG`, `DIFFICULT_CONFIG`).

2. `_build_prompt(document_text, plan)` — builds the actual text prompt sent
   to Gemini. It has three different "style" instructions (easy/hard/
   difficult) describing the *tone* of questions to write (straightforward
   vs. trap-laden vs. Nigerian-exam-style word problems), followed by a
   strict JSON schema description telling Gemini exactly what fields each
   question object must have.

3. `get_client()` — creates the Gemini API client **lazily** (only when
   actually needed), using `GEMINI_API_KEY` from `.env`. This is why the
   backend can still start and serve signup/login even if no AI key is
   configured yet — the key is only required at the moment you generate a
   quiz.

4. `generate_quiz_questions(...)` — sends the prompt to
   `client.models.generate_content(...)` with
   `response_mime_type: "application/json"` (this tells Gemini to *only*
   output valid JSON, no extra commentary), then parses that JSON into a
   Python list of question dicts.

---

### `backend/grading.py`

- `grade_mcq(question, user_answer)` — pure string comparison, no AI.
- `grade_theory_batch(theory_items)` — builds one prompt containing *all*
  theory questions + the student's answers + the marking points, and asks
  Gemini to return a JSON array of `{score, feedback}` — one per question.
  Batching them into a single call (instead of one call per question) saves
  API requests, which matters on a free tier with daily request limits.

---

## 3. Frontend — file by file

### `frontend/src/main.jsx` & `App.jsx`

`main.jsx` is the actual entry point — it mounts the `<App />` component
into the page's `<div id="root">`. `App.jsx` defines all the **routes**
(URL paths → which page component to show) using `react-router-dom`.
Routes inside `<Route element={<PrivateRoute />}>` require login —
`PrivateRoute` checks for a token in `localStorage` and redirects to `/` if
missing.

### `frontend/src/api.js` — the bridge to the backend

Every network call goes through this file. `api.post()`, `api.get()`, and
`api.upload()`:
- prepend `API_URL` (from `VITE_API_URL`) to the path,
- automatically attach `Authorization: Bearer <token>` from `localStorage`,
- parse the JSON response,
- throw a JS `Error` if the response wasn't OK (so pages can `catch` it and
  show an error message).

This means individual page components never write raw `fetch()` calls or
deal with tokens — they just call `api.get('/documents')` etc.

### Pages (`frontend/src/pages/`)

- **`Login.jsx` / `SignUp.jsx`** — forms that call `/login` or `/signup`,
  store the returned JWT in `localStorage`, then navigate to `/dashboard`.

- **`Dashboard.jsx`** — on load, calls `GET /documents` to list uploaded
  PDFs. The upload form sends a `FormData` (file + optional title) to
  `POST /documents` via `api.upload()`. Each document card links to Study,
  Quiz setup, and Progress pages.

- **`StudySession.jsx`** — fetches `GET /documents/:id` for the full text,
  displays it in a scrollable reading pane, and runs a `setInterval`-based
  stopwatch. "Log session" sends the elapsed seconds to
  `POST /study-sessions`.

- **`QuizSetup.jsx`** — fetches `GET /quizzes/config` to display the
  difficulty options and marking schemes, then `POST /quizzes` to generate
  one, then navigates to `/quiz/:quizId`.

- **`Quiz.jsx`** — on load: fetches the quiz questions (`GET /quizzes/:id`)
  and starts an attempt (`POST /attempts`, which returns the time limit).
  Renders MCQ radio buttons or theory textareas. A `setInterval` countdown
  auto-submits when time runs out (uses refs — `answersRef`,
  `submittedRef` — to avoid "stale closure" bugs where the timer's callback
  would otherwise see an outdated copy of the answers). Submitting calls
  `POST /attempts/:id/submit` and navigates to `/results/:attemptId` passing
  the result via React Router's navigation `state`.

- **`Results.jsx`** — reads the result from navigation `state` (not
  re-fetched from the server — if you refresh this page, the detailed
  breakdown is lost, only the summary remains in `/attempts` history).
  Shows the `ScoreStamp` and a per-question breakdown: for MCQ, highlights
  the correct option and the user's (wrong) choice in different colors; for
  theory, shows the user's answer, Gemini's feedback, and a collapsible
  model answer.

- **`Performance.jsx`** — fetches `GET /documents/:id/performance` and draws
  a Recharts `LineChart` of percentage-over-time, plus a list of past
  attempts with study time at the time of each attempt.

### Components (`frontend/src/components/`)

- **`Layout.jsx`** — shared header (logo + logout button) wrapping every
  authenticated page.
- **`ScoreStamp.jsx`** — the circular "graded by hand" badge on the Results
  page; color changes based on percentage (red/amber/green).

### Styling

- **`tailwind.config.js`** — defines the custom color palette (`bg`,
  `surface`, `accent`, `correct`, `incorrect`, etc.) and fonts (`Poppins`
  for UI text, `Space Mono` for scores/timers/marks — giving a
  "exam paper" feel).
- **`index.css`** — imports the Google Fonts, sets the dark background, and
  pulls in Tailwind's base/components/utilities layers.

---

## 4. Following one request end-to-end

To really cement this, trace what happens when a user takes a quiz:

1. **Dashboard** → click "Take quiz" → navigates to `/documents/3/quiz-setup`.
2. **QuizSetup** loads, calls `GET /quizzes/config` → Flask returns the
   marking schemes (no DB/AI involved, just constants).
3. User picks "Hard" → clicks "Generate quiz" → `POST /quizzes
   {document_id: 3, difficulty: "hard"}`.
4. Flask: looks up `Document` #3 (checks it belongs to this user via the JWT
   identity), truncates its text, calls `quiz_generator.generate_quiz_questions`
   → Gemini returns 20 questions as JSON → Flask saves a `Quiz` row + 20
   `Question` rows → returns the quiz (without `correct_answer`) to the
   frontend.
5. Frontend navigates to `/quiz/12` (the new quiz's id).
6. **Quiz.jsx** loads: `GET /quizzes/12` (questions) +
   `POST /attempts {quiz_id: 12}` (starts the attempt, snapshots study time,
   returns the 60-minute time limit). Countdown starts.
7. User answers questions, clicks Submit (or timer hits 0) →
   `POST /attempts/45/submit {answers: [...]}`.
8. Flask: for each MCQ, compares the answer letter; batches all theory
   answers into one Gemini call for grading; sums scores; saves the
   `Attempt` + `Answer` rows; returns the full breakdown.
9. Frontend navigates to `/results/45` with that breakdown in React Router
   state → **Results.jsx** renders the `ScoreStamp` and per-question detail.
10. Later, **Performance.jsx** calls `GET /documents/3/performance`, which
    re-reads all `Attempt` rows for document 3 from the database (this is
    why history persists even though the Results page detail doesn't).

---

## 5. Hosting checklist (recap)

1. Push the project to a GitHub repo (root contains `backend/` and
   `frontend/` folders).
2. **Backend → Render**: new Web Service, root dir `backend`, build
   `pip install -r requirements.txt`, start `gunicorn app:app`. Set env vars
   `SECRET_KEY`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `FRONTEND_ORIGIN`.
3. **Frontend → Vercel**: new project, root dir `frontend`, build
   `npm run build`, output `dist`. Set env var `VITE_API_URL` to your Render
   URL.
4. Go back to Render and update `FRONTEND_ORIGIN` to your Vercel URL, then
   redeploy the backend so CORS allows it.
5. Remember: Render's free tier filesystem is ephemeral — the SQLite DB
   resets on redeploy/restart. Fine for a portfolio demo.
