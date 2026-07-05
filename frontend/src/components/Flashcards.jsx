import React, { useState } from "react";

const Flashcards = ({ cards }) => {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  if (!cards || cards.length === 0) {
    return <p className="text-muted text-sm">No flashcards yet.</p>;
  }

  const card = cards[index];

  const go = (delta) => {
    setFlipped(false);
    setIndex((prev) => (prev + delta + cards.length) % cards.length);
  };

  return (
    <div className="flex flex-col items-center">
      <p className="text-xs text-muted font-mono mb-3">
        {index + 1} / {cards.length}
      </p>

      <button
        onClick={() => setFlipped((f) => !f)}
        className="w-full max-w-md aspect-[3/2] bg-surface border border-border rounded-2xl p-6 flex items-center justify-center text-center cursor-pointer hover:border-accent transition-colors"
      >
        <div>
          <p className="text-xs text-muted uppercase tracking-wide mb-2">
            {flipped ? "Answer" : "Question"}
          </p>
          <p className="text-lg leading-relaxed">
            {flipped ? card.back : card.front}
          </p>
        </div>
      </button>

      <p className="text-xs text-muted mt-2">Tap card to flip</p>

      <div className="flex gap-3 mt-4">
        <button
          onClick={() => go(-1)}
          className="border border-border rounded-lg px-4 py-1.5 text-sm hover:border-accent transition-colors"
        >
          ← Prev
        </button>
        <button
          onClick={() => go(1)}
          className="border border-border rounded-lg px-4 py-1.5 text-sm hover:border-accent transition-colors"
        >
          Next →
        </button>
      </div>
    </div>
  );
};

export default Flashcards;
