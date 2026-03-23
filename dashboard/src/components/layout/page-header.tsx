"use client";

import { motion } from "framer-motion";
import { slideInLeft } from "@/lib/motion";

interface PageHeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <motion.div
      className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between"
      variants={slideInLeft}
      initial="hidden"
      animate="visible"
    >
      <div>
        <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
        {description && (
          <p className="mt-0.5 text-sm text-text-secondary">{description}</p>
        )}
      </div>
      {children && <div className="flex items-center gap-2 mt-3 sm:mt-0">{children}</div>}
    </motion.div>
  );
}
