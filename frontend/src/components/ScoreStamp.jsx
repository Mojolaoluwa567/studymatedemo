import React from "react";

/**
 * A rotated, hand-graded-looking score stamp - the visual signature of the
 * results page. Color shifts from incorrect -> accent -> correct based on
 * percentage.
 */
const ScoreStamp = ({ score, maxScore, percentage }) => {
  let color = "text-incorrect border-incorrect";
  if (percentage >= 75) color = "text-correct border-correct";
  else if (percentage >= 45) color = "text-accent border-accent";

  return (
    <div
      className={`inline-flex flex-col items-center justify-center border-4 rounded-full w-32 h-32 -rotate-6 font-mono ${color}`}
      style={{ borderStyle: "double" }}
    >
      <span className="text-3xl font-bold leading-none">{percentage}%</span>
      <span className="text-xs mt-1">
        {score}/{maxScore}
      </span>
    </div>
  );
};

export default ScoreStamp;
