import React from "react";

const Skeleton = ({ className = "" }) => (
  <div
    className={`animate-pulse bg-surface-light rounded ${className}`}
  />
);

export const SkeletonLines = ({ lines = 4 }) => (
  <div className="space-y-3">
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        className={`h-4 ${i % 3 === 2 ? "w-2/3" : "w-full"}`}
      />
    ))}
  </div>
);

export const SkeletonCards = ({ count = 4 }) => (
  <div className="grid sm:grid-cols-2 gap-3">
    {Array.from({ length: count }).map((_, i) => (
      <Skeleton key={i} className="h-24" />
    ))}
  </div>
);

export default Skeleton;
