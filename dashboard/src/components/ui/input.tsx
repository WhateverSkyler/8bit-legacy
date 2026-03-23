import { cn } from "@/lib/utils";
import { forwardRef } from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => (
    <div className="w-full">
      <input
        ref={ref}
        className={cn(
          "h-10 w-full rounded-[var(--radius-md)] border bg-bg-nested px-3 text-sm text-text-primary placeholder:text-text-muted transition-all duration-200",
          "focus:outline-none focus:border-accent-cyan focus:shadow-[inset_0_0_0_2px_rgba(14,165,233,0.15)]",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          error ? "border-accent-red" : "border-border",
          className
        )}
        {...props}
      />
      {error && (
        <p className="mt-1 text-xs text-accent-red">{error}</p>
      )}
    </div>
  )
);
Input.displayName = "Input";

export { Input };
