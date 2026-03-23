"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface Tab {
  id: string;
  label: string;
  count?: number;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

function Tabs({ tabs, activeTab, onChange, className }: TabsProps) {
  return (
    <div
      className={cn(
        "flex gap-1 rounded-[var(--radius-md)] bg-bg-nested p-1",
        className
      )}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            "relative flex items-center gap-2 rounded-[var(--radius-sm)] px-4 py-2 text-sm font-medium transition-colors",
            activeTab === tab.id
              ? "text-text-primary"
              : "text-text-muted hover:text-text-secondary"
          )}
        >
          {activeTab === tab.id && (
            <motion.div
              className="absolute inset-0 rounded-[var(--radius-sm)] bg-bg-surface shadow-sm"
              layoutId="activeTab"
              transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            />
          )}
          <span className="relative z-10">{tab.label}</span>
          {tab.count !== undefined && (
            <span
              className={cn(
                "relative z-10 rounded-full px-1.5 py-0.5 text-xs",
                activeTab === tab.id
                  ? "bg-accent-cyan/20 text-accent-cyan"
                  : "bg-bg-hover text-text-muted"
              )}
            >
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

export { Tabs };
export type { Tab };
