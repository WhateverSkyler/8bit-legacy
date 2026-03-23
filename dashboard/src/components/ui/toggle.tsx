"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  label?: string;
}

function Toggle({ checked, onChange, disabled, className, label }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={cn(
        "relative inline-flex h-7 w-[52px] shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200",
        checked ? "bg-accent-cyan" : "bg-border",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      onClick={() => !disabled && onChange(!checked)}
    >
      <motion.span
        className="block h-6 w-6 rounded-full bg-white shadow-sm"
        animate={{ x: checked ? 26 : 2 }}
        transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      />
    </button>
  );
}

export { Toggle };
