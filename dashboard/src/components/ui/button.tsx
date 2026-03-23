"use client";

import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef } from "react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 font-semibold text-sm transition-all duration-200 ease-out cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-cyan active:scale-[0.97]",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-br from-accent-cyan to-accent-cyan-deep text-white hover:brightness-110 hover:shadow-[0_4px_12px_rgba(14,165,233,0.35)] active:brightness-95",
        secondary:
          "bg-bg-nested border border-border text-text-primary hover:border-accent-cyan hover:text-accent-cyan hover:bg-bg-hover active:bg-bg-nested",
        ghost:
          "bg-transparent text-text-secondary hover:bg-bg-surface hover:text-text-primary active:bg-bg-nested",
        destructive:
          "bg-accent-red text-white hover:bg-accent-red-deep hover:shadow-[0_4px_12px_rgba(239,68,68,0.35)] active:brightness-90",
        outline:
          "bg-transparent border border-border text-text-primary hover:border-accent-cyan hover:text-accent-cyan",
      },
      size: {
        sm: "h-8 px-3 text-xs rounded-[var(--radius-pill)]",
        md: "h-10 px-5 text-sm rounded-[var(--radius-pill)]",
        lg: "h-11 px-6 text-sm rounded-[var(--radius-pill)]",
        icon: "h-9 w-9 rounded-[var(--radius-md)]",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        ) : null}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
