import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ThemeToggle from "../components/ThemeToggle";

const TYPED_QUESTION = "Which of these is FALSE about threads?";
const TYPED_OPTIONS = [
  { key: "A", text: "Threads share memory with other threads in the process" },
  { key: "B", text: "Threads are heavier than processes" },
  { key: "C", text: "Threads are units of execution" },
];

function useTypewriter(text, speed = 28, startDelay = 300) {
  const [shown, setShown] = useState("");
  useEffect(() => {
    let i = 0;
    let interval;
    const startTimer = setTimeout(() => {
      interval = setInterval(() => {
        i += 1;
        setShown(text.slice(0, i));
        if (i >= text.length) clearInterval(interval);
      }, speed);
    }, startDelay);
    return () => {
      clearTimeout(startTimer);
      clearInterval(interval);
    };
  }, [text, speed, startDelay]);
  return shown;
}

const HeroPreviewCard = () => {
  const typed = useTypewriter(TYPED_QUESTION);
  const [revealOptions, setRevealOptions] = useState(false);
  const [picked, setPicked] = useState(null);

  useEffect(() => {
    if (typed.length === TYPED_QUESTION.length) {
      const t = setTimeout(() => setRevealOptions(true), 200);
      return () => clearTimeout(t);
    }
  }, [typed]);

  useEffect(() => {
    if (revealOptions) {
      const t = setTimeout(() => setPicked("B"), 1400);
      return () => clearTimeout(t);
    }
  }, [revealOptions]);

  return (
    <div className="bg-surface border border-border rounded-2xl p-5 shadow-xl shadow-black/5 w-full max-w-sm">
      <div className="flex items-center justify-between mb-4">
        <span className="font-mono text-xs text-accent uppercase tracking-wider">
          Hard · OS Notes.pdf
        </span>
        <span className="font-mono text-xs text-muted">2 marks</span>
      </div>
      <p className="text-sm font-medium leading-relaxed min-h-[2.5rem]">
        {typed}
        {typed.length < TYPED_QUESTION.length && (
          <span className="inline-block w-[2px] h-4 bg-accent ml-0.5 animate-pulse" />
        )}
      </p>
      <div
        className={`space-y-2 mt-3 transition-opacity duration-300 ${
          revealOptions ? "opacity-100" : "opacity-0"
        }`}
      >
        {TYPED_OPTIONS.map((opt) => {
          const isPicked = picked === opt.key;
          const isCorrect = opt.key === "B";
          let style = "border-border";
          if (picked && isCorrect) style = "border-correct bg-correct/10";
          else if (isPicked) style = "border-incorrect bg-incorrect/10";
          return (
            <div
              key={opt.key}
              className={`text-xs rounded-lg border px-3 py-2 transition-colors duration-300 ${style}`}
            >
              <span className="font-mono text-muted mr-1.5">{opt.key}.</span>
              {opt.text}
            </div>
          );
        })}
      </div>
      {picked && (
        <p className="text-xs text-correct mt-3 font-medium">
          ✓ Graded instantly — threads are lighter than processes, not heavier.
        </p>
      )}
    </div>
  );
};

const StepCard = ({ index, title, description }) => (
  <div className="bg-surface border border-border rounded-xl p-6">
    <span className="font-mono text-xs text-accent">{`0${index}`}</span>
    <h3 className="font-semibold text-lg mt-2 mb-1.5">{title}</h3>
    <p className="text-sm text-muted leading-relaxed">{description}</p>
  </div>
);

const DifficultyCard = ({ name, color, description, detail }) => (
  <div className="bg-surface border border-border rounded-xl p-6">
    <span
      className={`font-mono text-xs uppercase tracking-wider px-2 py-0.5 rounded border ${color}`}
    >
      {name}
    </span>
    <p className="text-sm mt-3 leading-relaxed">{description}</p>
    <p className="text-xs text-muted mt-2 font-mono">{detail}</p>
  </div>
);

const FeatureItem = ({ title, description }) => (
  <div>
    <h3 className="font-semibold mb-1.5">{title}</h3>
    <p className="text-sm text-muted leading-relaxed">{description}</p>
  </div>
);

const Landing = () => {
  return (
    <div className="min-h-screen bg-bg text-ink">
      {/* Nav */}
      <header className="border-b border-border sticky top-0 bg-bg/95 backdrop-blur z-20">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono text-accent text-xs tracking-[0.3em] uppercase">
              StudyMate
            </span>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              to="/login"
              className="text-sm text-muted hover:text-ink transition-colors"
            >
              Log in
            </Link>
            <Link
              to="/signup"
              className="text-sm bg-accent text-bg font-semibold rounded-lg px-4 py-2 hover:opacity-90 transition-opacity"
            >
              Sign up free
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-4 pt-16 pb-20 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <p className="font-mono text-xs text-accent uppercase tracking-wider mb-4">
            Upload notes → get quizzed → track what you know
          </p>
          <h1 className="text-4xl sm:text-5xl font-semibold leading-[1.1] mb-5">
            Reading your notes again won't tell you what you don't know.
          </h1>
          <p className="text-muted text-lg leading-relaxed mb-4 max-w-md">
            Upload your course material. StudyMate turns it into a real exam
            experience — graded instantly, with per-topic mastery tracking so
            you always know exactly what to focus on next.
          </p>
          <p className="inline-flex items-center gap-1.5 text-xs font-mono text-correct border border-correct/30 bg-correct/10 rounded-full px-3 py-1.5 mb-8">
            <span>●</span> Closed-book by design — every question comes from
            your material, nothing else
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/signup"
              className="bg-accent text-bg font-semibold rounded-lg px-6 py-3 hover:opacity-90 transition-opacity"
            >
              I'm a student →
            </Link>
            <Link
              to="/signup?role=teacher"
              className="border border-border rounded-lg px-6 py-3 hover:border-accent transition-colors"
            >
              I'm a teacher →
            </Link>
          </div>
        </div>
        <div className="flex justify-center lg:justify-end">
          <HeroPreviewCard />
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="max-w-5xl mx-auto px-4 py-16 border-t border-border">
        <h2 className="text-2xl font-semibold mb-2">How it works</h2>
        <p className="text-muted mb-8">
          Four steps — your first quiz is ready in under a minute.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StepCard
            index={1}
            title="Upload your material"
            description="Drop in a PDF, Word doc, paste notes, or link a YouTube lecture. Up to 20 files at once for teachers."
          />
          <StepCard
            index={2}
            title="Pick a stage"
            description="Easy for quick recall, Hard for objective mastery, Difficult for final-exam simulation with theory included."
          />
          <StepCard
            index={3}
            title="Get graded instantly"
            description="Multiple choice grades itself. Theory answers get AI feedback on exactly what you missed."
          />
          <StepCard
            index={4}
            title="Track what you know"
            description="See mastery per topic across all your attempts. Weak spots? One click generates a focused review quiz."
          />
        </div>
      </section>

      {/* Difficulty tiers */}
      <section className="max-w-5xl mx-auto px-4 py-16 border-t border-border">
        <h2 className="text-2xl font-semibold mb-2">Three stages, one system</h2>
        <p className="text-muted mb-8">
          Each stage has a genuinely different structure — not just harder
          wording. All questions are generated strictly from your uploaded
          material, never from general knowledge.
        </p>
        <div className="grid sm:grid-cols-3 gap-4">
          <DifficultyCard
            name="Stage 1 — Easy"
            color="border-correct text-correct"
            description="MCQ only. Direct recall, definitions, and simple concept checks. Tests whether you know the material at all."
            detail="40 × 1 mark or 20 × 2 marks — 40 marks total"
          />
          <DifficultyCard
            name="Stage 2 — Hard"
            color="border-accent text-accent"
            description="MCQ only, but genuinely twisted. NOT/EXCEPT phrasing, near-identical options, application questions. Tests whether you truly understand — not just remember."
            detail="60 × 1 mark or 30 × 2 marks — 60 marks total"
          />
          <DifficultyCard
            name="Stage 3 — Difficult"
            color="border-incorrect text-incorrect"
            description="MCQ + theory combined. Objective side = 60%, theory side = 40%. Feels like a real final exam, not random AI practice."
            detail="60 MCQ + 10 theory = 100 marks, or 30 MCQ + 5 theory = 100 marks"
          />
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-4 py-16 border-t border-border">
        <h2 className="text-2xl font-semibold mb-8">Everything you need to actually retain it</h2>
        <div className="grid sm:grid-cols-2 gap-8">
          <FeatureItem
            title="Closed-book, on purpose"
            description="No general knowledge, no outside sources. Every question is generated strictly from the material you uploaded — so practicing with StudyMate means practicing on exactly what you'll be examined on."
          />
          <FeatureItem
            title="Read the real document"
            description="PDFs render exactly as uploaded in the Study tab — not a stripped-down text dump. Scroll, zoom, and read it like you would any PDF viewer."
          />
          <FeatureItem
            title="Per-topic mastery tracking"
            description="Every question is tagged to a concept. After each quiz, your mastery per topic updates automatically — so you always know whether it's Deadlocks or CPU Scheduling that needs more work."
          />
          <FeatureItem
            title="Weak spots review mode"
            description="One click generates a short, focused quiz targeting only the topics you're struggling on. Not a random retake — a targeted one."
          />
          <FeatureItem
            title="Explain my mistakes"
            description="Every wrong answer comes with a plain-language breakdown of why the correct answer is right and what to revise."
          />
          <FeatureItem
            title="Interactive explainer"
            description="AI generates a self-contained interactive webpage from your document — collapsible sections, glossary, quick review questions. Study without re-reading."
          />
          <FeatureItem
            title="Progress you can see"
            description="Score trends over time, study time logged per document, and a full history of every attempt. Download your results or study guide as a real PDF, ready to print."
          />
          <FeatureItem
            title="Sign in your way"
            description="Email and password, or one-click Google sign-in. Your choice, same account either way."
          />
        </div>
      </section>

      {/* For teachers */}
      <section className="max-w-5xl mx-auto px-4 py-16 border-t border-border">
        <h2 className="text-2xl font-semibold mb-2">Built for teachers too</h2>
        <p className="text-muted mb-8">
          Sign up as a teacher for a completely different experience — manage assignments, classes, and track how every student is doing.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <FeatureItem title="Draft, review, then publish" description="Generate questions, review and edit each one individually, then publish when you're happy. Students can't see it until you do." />
          <FeatureItem title="Classes & cohorts" description="Create a class, share one code, and all your assignments are automatically visible to every student who joins." />
          <FeatureItem title="Bulk upload" description="Upload up to 20 lecture PDFs at once. Each becomes a document you can turn into an assignment." />
        </div>
      </section>

      {/* What's next */}
      <section className="max-w-5xl mx-auto px-4 py-16 border-t border-border">
        <h2 className="text-2xl font-semibold mb-2">What's next</h2>
        <p className="text-muted mb-8">
          In active development - not available yet, but on the roadmap.
        </p>
        <div className="grid sm:grid-cols-3 gap-4">
          <div className="bg-surface border border-border rounded-xl p-5 relative">
            <span className="absolute top-4 right-4 text-[10px] font-mono uppercase tracking-wider text-muted border border-border rounded-full px-2 py-0.5">
              Coming soon
            </span>
            <h3 className="font-semibold mb-1.5 pr-20">AI one-on-one tutor</h3>
            <p className="text-sm text-muted leading-relaxed">
              A chat-based tutor that walks through a concept with you,
              answering follow-up questions in context of your material.
            </p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-5 relative">
            <span className="absolute top-4 right-4 text-[10px] font-mono uppercase tracking-wider text-muted border border-border rounded-full px-2 py-0.5">
              Coming soon
            </span>
            <h3 className="font-semibold mb-1.5 pr-20">Voiceover & video lessons</h3>
            <p className="text-sm text-muted leading-relaxed">
              Turn a document into a narrated audio walkthrough or a short
              video lesson on a specific topic.
            </p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-5 relative">
            <span className="absolute top-4 right-4 text-[10px] font-mono uppercase tracking-wider text-muted border border-border rounded-full px-2 py-0.5">
              Coming soon
            </span>
            <h3 className="font-semibold mb-1.5 pr-20">Deeper retrieval</h3>
            <p className="text-sm text-muted leading-relaxed">
              Full-document retrieval for longer course material, so
              quizzes can draw from an entire textbook, not just the first
              portion of it.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-5xl mx-auto px-4 py-20 border-t border-border text-center">
        <h2 className="text-3xl font-semibold mb-3">Stop re-reading. Start testing yourself.</h2>
        <p className="text-muted mb-8 max-w-md mx-auto">
          Free to use. No credit card. Your first quiz is one upload away.
        </p>
        <Link
          to="/signup"
          className="bg-accent text-bg font-semibold rounded-lg px-8 py-3 hover:opacity-90 transition-opacity inline-block"
        >
          Create your free account
        </Link>
      </section>

      <footer className="border-t border-border">
        <div className="max-w-5xl mx-auto px-4 py-12">
          <div className="grid sm:grid-cols-3 gap-8 mb-10">
            <div>
              <span className="font-mono text-xs text-accent tracking-[0.2em] uppercase block mb-3">
                StudyMate
              </span>
              <p className="text-sm text-muted leading-relaxed">
                Built for active recall, not passive re-reading. Upload your
                course material — we'll turn it into a real exam experience.
              </p>
            </div>
            <div>
              <p className="text-xs font-mono text-muted uppercase tracking-wider mb-3">For students</p>
              <ul className="space-y-2">
                <li><a href="/signup" className="text-sm text-muted hover:text-ink transition-colors">Create free account</a></li>
                <li><a href="/login" className="text-sm text-muted hover:text-ink transition-colors">Log in</a></li>
                <li><a href="/join" className="text-sm text-muted hover:text-ink transition-colors">Join an assignment</a></li>
              </ul>
            </div>
            <div>
              <p className="text-xs font-mono text-muted uppercase tracking-wider mb-3">For teachers</p>
              <ul className="space-y-2">
                <li>
                  <a href="/signup" className="text-sm text-muted hover:text-ink transition-colors">
                    Sign up as a teacher
                  </a>
                </li>
                <li>
                  <span className="text-sm text-muted">
                    Create assignments with shareable join codes
                  </span>
                </li>
                <li>
                  <span className="text-sm text-muted">
                    Track every student's progress in one place
                  </span>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border pt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-xs text-muted">
              © {new Date().getFullYear()} StudyMate. Free to use, built for students.
            </p>
            <div className="flex gap-4">
              <a href="/signup" className="text-xs text-accent hover:underline">
                Get started →
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
