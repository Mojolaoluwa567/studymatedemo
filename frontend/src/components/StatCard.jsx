import React from "react";

const StatCard = ({ label, value, icon }) => (
  <div className="card bg-surface border border-border rounded-xl p-4 text-center hover:-translate-y-0.5">
    {icon && (
      <div className="flex justify-center text-accent mb-1.5">{icon}</div>
    )}
    <p className="font-mono text-2xl text-accent">{value}</p>
    <p className="text-xs text-muted mt-1">{label}</p>
  </div>
);

export default StatCard;
