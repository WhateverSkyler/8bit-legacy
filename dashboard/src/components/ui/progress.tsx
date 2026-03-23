"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface ProgressProps {
  value: number;
  max?: number;
  className?: string;
  showLabel?: boolean;
}

function Progress({ value, max = 100, className, showLabel }: ProgressProps) {
  const percent = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div className={cn("w-full", className)}>
      <div className="h-2 w-full overflow-hidden rounded-full bg-bg-nested">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-accent-cyan to-accent-cyan-deep"
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
        />
      </div>
      {showLabel && (
        <p className="mt-1 text-xs text-text-secondary tabular-nums">
          {Math.round(percent)}%
        </p>
      )}
    </div>
  );
}

export { Progress };
