import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const badgeVariants = cva(
  "inline-flex items-center rounded-[var(--radius-sm)] px-2 py-0.5 text-xs font-semibold uppercase tracking-wide border",
  {
    variants: {
      variant: {
        success:
          "bg-[rgba(34,197,94,0.1)] text-[#16a34a] border-[rgba(34,197,94,0.25)]",
        warning:
          "bg-[rgba(245,158,11,0.1)] text-[#d97706] border-[rgba(245,158,11,0.25)]",
        error:
          "bg-[rgba(239,68,68,0.1)] text-[#dc2626] border-[rgba(239,68,68,0.25)]",
        info: "bg-[rgba(14,165,233,0.1)] text-[#0284c7] border-[rgba(14,165,233,0.25)]",
        neutral: "bg-bg-nested text-text-secondary border-border",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  }
);

interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
