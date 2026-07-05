# StudyMate

Upload your course material (PDF), study it with AI-generated summaries,
key concepts and flashcards, then test yourself with a quiz that grades
itself — explains your mistakes, tracks streaks/achievements, and shows
your progress over time in a light- or dark-mode dashboard.

- **Backend:** Flask + SQLite (or Postgres) + pdfplumber + Google Gemini API
- **Frontend:** React (Vite) + Tailwind + Recharts + react-hot-toast + canvas-confetti

## How it works

1. **Add your material** — upload a PDF or Word (.docx), paste in text
   directly, give it a web page URL, a YouTube video link, or an audio
   file. Text is extracted (or transcribed) and stored the same way
   regardless of source.
2. **Study** — a reading view with a timer, plus AI-generated **Summary**,
   **Key Concepts**, and **Flashcards** tabs (cached after first generation).
3. **Take a quiz** — choose a difficulty and Gemini generates fresh questions
   from your document:
   - **Easy** — MCQ only. Choose 60 questions @ 1 mark or 30 @ 2 marks
     (60 marks total either way — enforced server-side, never exceeded).
     Straightforward, directly from the text.
   - **Hard** — mix of MCQ + theory. MCQs look simple but contain a subtle
     trap (FALSE/EXCEPT phrasing, near-identical distractors, commonly
     confused concepts). Theory questions test explanation in your own words.
   - **Difficult** — mix of MCQ + theory, the hardest tier: precise
     wordplay, applying concepts to specific situations, and multi-step
     reasoning. Every scenario stays grounded in the material itself —
     no invented fictional settings.
4. **Get graded** — MCQs are auto-graded instantly. Theory answers are graded
   by Gemini against marking points, with feedback on what was missed.
5. **Report card popup** — immediately after submitting, a modal shows your
   score, grade, correct/incorrect breakdown, time spent, confetti for 80%+,
   and options to review, retake, or download results.
6. **Explain my mistakes** — on the results page, get a plain-language
   explanation of why each wrong/partial answer was marked that way and what
   to revise.
7. **Track progress** — quiz history, score-over-time charts, study streaks,
   and achievements (First Quiz, Centurion, Perfect Score, 7-Day Streak).
8. **Profile** — view account info, stats, achievements, change password, or
   reset a forgotten one via email link.
9. **Light/dark theme** — toggle in the header, persisted across sessions.

## Routes

- `/` — public marketing landing page (how it works, difficulty tiers,
  features) with Log in / Sign up in the nav. No auth required.
- `/login`, `/signup`, `/forgot-password`, `/reset-password` — auth pages.
  Sign up includes a Student/Teacher role toggle.
- `/dashboard` — role-aware: students see the usual upload/quiz/progress
  dashboard; teachers see the Teacher Dashboard (create assignments, view
  join codes, see student results) instead. Same URL for both, the
  frontend checks `profile.role` and renders accordingly.
- `/join` — student-facing: redeem a teacher's join code to get the quiz.
- Everything else (`/profile`, `/history`, `/documents/:id/*`,
  `/quiz/:quizId`, `/results/:attemptId`) requires a logged-in session and
  lives behind `PrivateRoute`.

## Polish

A handful of small additions that don't change functionality but close
gaps that make an app feel unfinished:

- **Favicon** (`frontend/public/favicon.svg`) - a simple geometric mark
  in the app's accent color, replacing the default Vite icon.
- **Per-route page titles** - `usePageTitle()` hook
  (`frontend/src/hooks/usePageTitle.js`) sets `document.title` per page
  (e.g. "Dashboard — StudyMate"), restoring the previous title on
  unmount so navigation never leaves a stale tab title behind.
- **First-paint loading screen** - a small pulsing mark shown via plain
  CSS in `index.html` between the blank page and React mounting, removed
  by `main.jsx` once the app takes over. Same trick as the dark-mode
  anti-flash script: pure HTML/CSS, no dependency on JS having loaded yet.
- **"What's next" section on the landing page** - the genuinely
  not-yet-built ideas (AI tutor, voiceover/video lessons, deeper
  retrieval/RAG) are shown with a clear "Coming soon" badge rather than
  either hidden entirely or implied to already work. The WAEC/JAMB idea
  is deliberately NOT listed here - it still needs its own conversation
  about legitimate content sourcing before it's something to publicly
  commit to, even as a roadmap item.

## Admin dashboard

A privilege layer separate from `role` (student/teacher) - `User.is_admin`
is its own boolean, not a 3rd role value, since an admin account is still
also a student or teacher underneath (the regular Dashboard routing via
`DashboardRouter` is completely untouched by this).

**There's no signup flow for admin access - it's not self-service.** To
make an account an admin, set the flag directly in the database, one
time:

```bash
cd backend
python3 -c "
from app import app, db
from models import User
with app.app_context():
    user = User.query.filter_by(username='YOUR_USERNAME').first()
    user.is_admin = True
    db.session.commit()
    print(f'{user.username} is now an admin')
"
```

Once flagged, an "Admin" link appears in that account's sidebar
automatically (checked via `profile.is_admin` in `Layout.jsx`).

**What it shows** (`admin.py` - kept as its own module since the
aggregation logic is substantial enough to clutter `app.py`):
- **Overview** - total users (split by role), documents, quizzes,
  attempts, new/active users in the last 7 days, platform-wide average
  score.
- **Users** - every user with per-user document/attempt counts, searchable
  by username or email, with a drill-down into one user's full document
  list and recent attempt history.
- **Content** - every document platform-wide with its owner, searchable
  by title, with a moderation delete that works on ANY user's document
  (not just the admin's own) - same cascade behavior as a user deleting
  their own document.
- **Usage** - an *estimated* AI-call count broken down by type (quiz
  generations, theory grading batches, summaries, key concepts,
  flashcards, explanations), plus average score by difficulty and a
  14-day attempt-volume trend.

**Important honesty note on the usage numbers**: every figure here is
**derived from existing rows** (a Quiz row implies one generation call, a
cached `Document.summary` implies one call, etc.) - there's no dedicated
metering table counting actual Gemini API requests. This was a deliberate
choice to avoid threading a new write-path through every AI call just for
analytics; it's a good proxy for relative usage and trends, but should
never be read as an exact count against Gemini's real quota. The frontend
usage tab states this explicitly, not just this README.

## Navigation

`Layout.jsx` is the single chrome component every authenticated page
renders inside - a persistent left sidebar on desktop (`md:` and up),
collapsing to a hamburger-triggered slide-in drawer on mobile. Built
last, after every other authenticated route existed, so the nav list
reflects the real final set rather than guessing ahead: Dashboard
(role-aware - routes to the student or teacher view via
`DashboardRouter`), Join a quiz and History (hidden for teachers, who
don't take quizzes themselves), and Profile - plus theme toggle and log
out pinned to the bottom of the sidebar/drawer.

The active route is highlighted (`useLocation()` + a prefix match, so
e.g. `/documents/3/study` still highlights nothing extra, only exact nav
targets light up). The mobile drawer closes automatically on navigation.

This was a frontend-only change, contained entirely to `Layout.jsx` -
every authenticated page already rendered inside `<Layout>` without
assuming anything about its internal structure (confirmed by grep before
making the change), so no other component needed touching.

## Lecturer-style quizzes

A 4th quiz mode, separate from the Easy/Hard/Difficult ladder: a student
picks their course material as usual, plus a second document - a sample
of a specific lecturer's past questions (uploaded the same way as any
other document; PDF, Word, pasted text, etc. all work). The generated
quiz is about the course material, but written to match the *phrasing
and structure* of the past-questions sample - "get used to how this
lecturer writes exams," not a difficulty tier.

Design decisions worth knowing:

- **No persistent "lecturer profile" concept (yet).** A student picks a
  style document fresh each time from their existing uploads - there's no
  named, reusable profile that aggregates multiple past papers for one
  lecturer. This was a deliberate scope cut for the testing stage: it
  keeps the feature to one new endpoint and zero schema changes. If it
  proves useful, turning "pick a document each time" into a named,
  multi-document profile is an additive upgrade later, not a rebuild.
- **The style document is never quizzed on.** The prompt
  (`_build_lecturer_style_prompt()` in `quiz_generator.py`) is explicit
  that the past-questions sample is a style reference only - facts,
  topics, and answers must come from the content document. The grounding
  check (see below) is run **only against the content document's text**,
  never the style document's - checking against the style text would be
  meaningless, since a well-written question is expected to share almost
  no keyword overlap with someone else's old exam paper.
- **No schema changes.** `Quiz.difficulty` was already a plain string
  column - `"lecturer_style"` is just a new value, not a new column.
- New endpoint: `POST /quizzes/lecturer-style` with
  `{content_document_id, style_document_id}` - both must belong to the
  requesting user and must be different documents. Reuses every existing
  downstream piece (attempts, grading, achievements, history, the
  card-based quiz UI) without any changes to those.

**A cross-phase bug this surfaced and fixed:** the Phase H difficulty
recommendation engine assumed every quiz's difficulty was one of
`easy`/`hard`/`difficult` and would crash (`ValueError`) if a student's 3
most recent attempts on a document were all `lecturer_style` quizzes,
since that value isn't on the step-up/step-down ladder.
`_recommend_difficulty()` now explicitly returns `None` for that case
instead - a good example of why each new mode needs a regression pass
against every *prior* feature, not just its own tests.

## Quiz-taking UI

Questions are presented one at a time as a card, not as a long
scrollable page - `currentIndex` state in `Quiz.jsx` tracks which
question is showing. A row of numbered progress dots above the card
shows answered (filled) vs unanswered (outlined) questions at a glance,
and is clickable - students can jump to any question directly, not just
step through linearly, and can freely go back and change a previous
answer before submitting.

"Submit now" is always available, not just on the last question -
useful if a student wants to submit early rather than being forced to
click through to the end. Manual submission with unanswered questions
remaining shows a confirmation ("You have N unanswered questions. Submit
anyway?"); the automatic submit that fires when the timer hits zero
skips that confirmation, since there's nothing to confirm at that point.

This was a frontend-only change - all existing answer state, timer
logic, and the `POST /attempts/:id/submit` payload shape are unchanged,
so no backend modifications were needed.

## Grounding check (closed-book enforcement)

The landing page claims every question comes from the uploaded material,
not general knowledge. Until this was added, that claim rested entirely
on prompt instructions ("only use this text") - true in practice almost
all the time, but not actually *enforced*, just requested.

`_filter_grounded()` in `quiz_generator.py` adds a real (if intentionally
simple) enforcement step, run on every generated question before
`_normalize_questions()`:

1. Extract the meaningful keywords (lowercased, stopwords removed) from
   the question text and its correct answer (for MCQ, the text of the
   correct option - not just its letter).
2. Check what fraction of those keywords actually appear in the source
   document text.
3. Drop any question where less than 30% of its keywords are grounded in
   the source. `total_marks`/`num_questions` are then recalculated from
   whatever survives - same "never trust the raw count, recalculate from
   what's left" pattern as the Easy mark-cap fix.

This is a **heuristic, not semantic verification** - deliberately chosen
over a second AI call per question to keep it free and instant, given the
shared Gemini quota is already being protected with rate limits
elsewhere. It reliably catches a model inventing an unrelated fact (wrong
subject matter entirely), but it will NOT catch a subtly wrong claim
phrased entirely using words that genuinely do appear in the source text.
A stronger, AI-call-based verification pass (or full RAG - chunking +
embedding + retrieval, which would also fix long-document coverage since
documents are currently truncated to ~18k characters before generation)
is a deliberate future upgrade, not implemented here.

## Difficulty recommendations

After enough attempts on a document, Quiz Setup can suggest stepping up
or down a tier - this is a *suggestion*, never automatic: the student
still picks, the recommendation just pre-selects a default and can be
dismissed.

The signal (`_recommend_difficulty()` in `app.py`) is deliberately
conservative:
- Needs the student's **3 most recent attempts on that document** to all
  be at the **same difficulty** as their last attempt - so switching
  tiers, or having too little history, simply produces no suggestion
  rather than a noisy one.
- Step up if those 3 attempts averaged ≥80%; step down if they averaged
  ≤45%. Anything in between is left alone.
- No suggestion is possible beyond Easy (nothing lower) or Difficult
  (nothing higher).

This reads entirely from existing `Attempt`/`Quiz` data - no new tables.

## Teacher & student roles

Every account is either a `student` or a `teacher` (chosen at signup, no
separate registration flow). Both roles use the same `User` table, the
same login, and the same JWT auth - only what they can *do* differs:

- **Teachers** can turn one of their own uploaded documents into an
  **assignment**: a quiz with a short 6-character join code
  (`POST /assignments`). They can list their assignments and see every
  student's submitted score (`GET /assignments`,
  `GET /assignments/:id/results`). Teacher-only routes reject students
  with a 403, enforced by a `_require_role("teacher")` decorator in
  `app.py`.
- **Students** redeem a join code (`POST /assignments/join`) to get the
  quiz and attempt it exactly like a personal quiz - no comment box or
  messaging is part of this (explicitly out of scope for now).
- Architecturally, a `Quiz` was already independently `user_id`-owned
  from `Attempt` (the quiz creator and the attempt taker are different
  fields) - so a teacher-created quiz attempted by a different student
  fit the existing schema with only two new `Quiz` columns
  (`is_assignment`, `join_code`) plus the new routes and permission
  checks above. No structural rework was needed.

## YouTube and audio ingestion

Two more ways to get content in, alongside PDF/Word/text/web page from
earlier:

- **YouTube** (`POST /documents/from-youtube`) tries the video's captions
  first via `youtube-transcript-api` - fast, free, no audio processing,
  and works for the large majority of videos (auto-generated captions are
  on by default for most uploads). If a video genuinely has no captions,
  it falls back to downloading just the audio track with `yt-dlp` and
  transcribing it via Gemini (which accepts audio directly as input - no
  separate speech-to-text library needed). The fallback is meaningfully
  slower, so it's rate-limited tighter (10/hour vs 20/hour for plain URLs)
  and the frontend shows a "this can take a minute" message when it kicks in.
- **Audio file upload** (`POST /documents/from-audio`) sends the file
  straight to Gemini for transcription. Supports mp3, wav, m4a, ogg, webm,
  flac, aac, capped at 25MB.
- Both extractors live in `content_ingestion.py` alongside every other
  source type, and both take the actual Gemini call
  (`transcribe_audio()` in `quiz_generator.py`) as an injected function
  parameter rather than importing the Gemini SDK directly - keeps
  `content_ingestion.py` independently testable with plain mocks, same
  as the rest of this module.
- Once extracted, a YouTube- or audio-sourced document is just a
  `Document` row like any other - it flows through quiz generation, study
  aids, and everything else identically to a PDF.

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Add your Gemini API key to .env - it's free, no credit card needed:
# https://aistudio.google.com/app/apikey

python app.py                   # runs on http://localhost:5000
```

**System dependency:** `ffmpeg` must be installed separately (not a pip
package) for the YouTube audio-transcription fallback to work when a video
has no captions. The captions path and every other ingestion type work
fine without it.
- Mac: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: download from ffmpeg.org and add it to PATH

If `ffmpeg` isn't installed, everything still works except that one
fallback case - it'll return a clear error instead of crashing.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env            # set VITE_API_URL to your backend URL
npm run dev                      # runs on http://localhost:5173
npm run build                    # production build -> dist/
```

## API Endpoints

| Method | Endpoint                          | Auth | Description |
|--------|-----------------------------------|------|-------------|
| POST   | /signup                            | No   | Create account `{username, email, password, role?}` (`role`: "student" or "teacher", default "student") |
| POST   | /login                             | No   | Returns JWT |
| GET    | /profile                           | Yes  | Username, email, role, member since |
| POST   | /profile/change-password           | Yes  | `{current_password, new_password}` |
| GET    | /profile/stats                     | Yes  | Quizzes, documents, avg score, streak, questions answered |
| GET    | /achievements                      | Yes  | All achievements with unlocked status |
| POST   | /forgot-password                   | No   | `{email}` - sends/returns reset link |
| POST   | /reset-password                    | No   | `{token, new_password}` |
| POST   | /documents                         | Yes  | Upload a PDF or Word .docx (multipart, field `file`, optional `title`) |
| POST   | /documents/from-text               | Yes  | Create a document from pasted text `{title?, text}` |
| POST   | /documents/from-url                | Yes  | Create a document by fetching a web page `{title?, url}` |
| POST   | /documents/from-youtube            | Yes  | Create a document from a YouTube video `{title?, url}` - captions first, audio transcription fallback |
| POST   | /documents/from-audio              | Yes  | Create a document by transcribing an uploaded audio file (multipart, field `file`) |
| GET    | /documents                         | Yes  | List your documents |
| GET    | /documents/:id                     | Yes  | Document + full extracted text |
| DELETE | /documents/:id                     | Yes  | Delete a document (cascades quizzes/attempts/study sessions) |
| GET    | /documents/:id/summary             | Yes  | AI summary (cached) |
| GET    | /documents/:id/key-concepts        | Yes  | AI key concepts (cached) |
| GET    | /documents/:id/flashcards          | Yes  | AI flashcards (cached) |
| POST   | /study-sessions                    | Yes  | Log study time `{document_id, duration_seconds}` |
| GET    | /quizzes/config                    | No   | Difficulty options/marking schemes |
| POST   | /quizzes                           | Yes  | Generate a personal quiz `{document_id, difficulty, easy_mode?}` |
| POST   | /quizzes/lecturer-style            | Yes  | Generate a quiz from one document, styled after a second past-questions document `{content_document_id, style_document_id}` |
| GET    | /quizzes/:id                       | Yes  | Quiz questions (no answers) - owner or, if it's an assignment, any student |
| POST   | /assignments                       | Teacher | Generate + publish an assignment quiz with a join code `{document_id, difficulty, easy_mode?, title?}` |
| GET    | /assignments                       | Teacher | List this teacher's assignments with submission counts |
| GET    | /assignments/:id/results            | Teacher | Every student's submitted attempt on one assignment |
| POST   | /assignments/join                  | Yes  | Redeem a join code `{join_code}` - returns the quiz to attempt |
| POST   | /attempts                          | Yes  | Start an attempt `{quiz_id}` (works for personal or assignment quizzes) |
| POST   | /attempts/:id/submit               | Yes  | Submit answers, get graded results + new achievements |
| GET    | /attempts/:id                      | Yes  | Full breakdown for a past attempt (review) |
| POST   | /attempts/:id/explain               | Yes  | Generate/cache "explain my mistakes" |
| GET    | /attempts                          | Yes  | Your attempt history |
| GET    | /documents/:id/performance         | Yes  | Score trend + study time for a document |
| GET    | /admin/overview                    | Admin | Platform-wide stat summary |
| GET    | /admin/users                       | Admin | All users + activity counts `?search=` |
| GET    | /admin/users/:id                   | Admin | One user's full document/attempt history |
| GET    | /admin/content                     | Admin | All documents platform-wide + owner `?search=` |
| DELETE | /admin/content/:id                 | Admin | Delete any user's document (moderation) |
| GET    | /admin/usage                       | Admin | Estimated AI-call breakdown + score analytics |
| GET    | /documents/:id/recommended-difficulty | Yes | Suggests stepping up/down a tier based on recent same-difficulty performance on this document, or `null` if no clear signal |

## Hosting (free options)

**Backend (Render):**
1. Push this repo to GitHub.
2. On render.com, create a new Web Service from the repo, root directory `backend`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app` (add `gunicorn` to requirements.txt for production)
5. Add environment variables: `SECRET_KEY`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`,
   and `FRONTEND_ORIGIN` (set this once you know your frontend's deployed URL).
6. Note: Render's free tier has an ephemeral filesystem, so the SQLite DB
   resets on every redeploy/restart - fine for a portfolio demo, not for
   real users.

**Frontend (Vercel or Netlify):**
1. Import the repo, set root directory to `frontend`.
2. Build command: `npm run build`, output directory: `dist`.
3. Add environment variable `VITE_API_URL` = your Render backend URL
   (e.g. `https://studymate-backend.onrender.com`).
4. Once deployed, copy the frontend URL back into the backend's
   `FRONTEND_ORIGIN` env var on Render and redeploy the backend.

## Notes on deployment

- **Use Postgres in production**, not SQLite — set `DATABASE_URL` to a managed
  Postgres connection string (Render Postgres, Supabase, Neon, or Railway's
  own Postgres add-on all have free tiers). This is the single most
  important change before sharing the app with real testers: SQLite on most
  hosts lives on an ephemeral filesystem and gets wiped on every redeploy,
  silently deleting every user's account and history. Postgres survives
  redeploys. The code needs zero changes either way — SQLAlchemy handles
  both, and `postgres://` URLs (the scheme some hosts hand out) are
  automatically normalized to `postgresql://` on startup.
- **Rate limiting** is in place on AI-calling endpoints (`/quizzes`,
  `/attempts/:id/explain`, the study-aid endpoints, `/forgot-password`) to
  protect the shared Gemini free-tier quota from being exhausted by one
  user or a runaway frontend loop.
- **JWT access tokens expire after 24 hours** (refresh tokens after 30 days)
  so a leaked token doesn't work indefinitely.
- **Documents can be deleted** (`DELETE /documents/:id`) — this cascades to
  remove every quiz, question, attempt, answer, and study session tied to
  that document, so there's no orphaned data left behind.
- SQLite is fine for a demo, but most free hosts have ephemeral filesystems —
  data resets on redeploy. That's expected for a portfolio demo. See
  `SCALABILITY.md` for further scaling notes toward ~1,000 users.
- Requires `GEMINI_API_KEY` set in the backend `.env` (free, no credit card -
  https://aistudio.google.com/app/apikey). Without it, quiz generation,
  grading, and AI study aids return a clear error; everything else (auth,
  upload, study timer, history, profile) works fine.
- Optional `SMTP_*` env vars enable real password-reset emails; without them,
  `/forgot-password` returns the reset link directly in the response (dev mode).
- Set `FRONTEND_ORIGIN` on the backend to your deployed frontend's URL (CORS),
  and use strong random values for `SECRET_KEY` / `JWT_SECRET_KEY`.
- Scanned/image-only PDFs aren't supported — text must be extractable.
  Legacy `.doc` (not `.docx`) Word files aren't supported either — only the
  modern XML-based `.docx` format. Web page ingestion works on static
  articles/docs pages but not on JavaScript-rendered single-page apps,
  since there's no headless browser involved.
- YouTube videos with region/age restrictions or that require sign-in may
  fail to download audio even when no captions exist - this surfaces as a
  clear error, not a crash. Audio files are capped at 25MB; very long
  recordings (multi-hour lectures) may need to be split first.
- **No schema change in this update** — `Document.source_type` already
  accepted any string and gained `"youtube"` / `"audio"` as valid values;
  `source_url` (already existed for the `url` type) is reused for YouTube
  links too. Existing `app.db` files don't need to be deleted for this
  particular update.
- **Schema changed** in this update (new `User.email`, `User.role`,
  `User.is_admin`, `Document.summary` / `key_concepts` / `flashcards` /
  `source_type` / `source_url`, `Quiz.is_assignment` / `join_code` /
  `title`, `Answer.explanation`, `Achievement` table). Delete any existing
  `backend/app.db` before running so it's recreated with the new schema —
  or, in production, use Flask-Migrate to apply schema changes without
  losing data (see `SCALABILITY.md`). After recreating the database,
  follow the admin dashboard section above to flag your own account as
  admin again - that flag does not survive a database reset.
# studymatedemo
