"use client";

import { useSidebar } from "@/components/providers/sidebar-provider";
import { motion } from "framer-motion";
import { Bell, Search } from "lucide-react";

export function Topbar() {
  const { collapsed } = useSidebar();

  return (
    <motion.header
      className="fixed top-0 right-0 z-30 flex h-[var(--topbar-height)] items-center justify-between border-b border-border bg-bg-surface px-6"
      animate={{ left: collapsed ? 80 : 280 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Search */}
      <div className="relative w-full max-w-md">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
        />
        <input
          type="text"
          placeholder="Search products, orders, analytics..."
          className="h-9 w-full rounded-[var(--radius-pill)] border border-border bg-bg-nested pl-9 pr-4 text-sm text-text-primary placeholder:text-text-muted transition-colors focus:border-accent-cyan focus:outline-none"
        />
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <button
          className="relative flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] text-text-muted hover:bg-bg-nested hover:text-text-primary transition-colors"
          aria-label="Notifications"
        >
          <Bell size={18} />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-accent-red" />
        </button>

        {/* User avatar */}
        <div className="ml-2 flex h-9 w-9 items-center justify-center rounded-full bg-[#ff9526] text-xs font-bold text-white">
          8B
        </div>
      </div>
    </motion.header>
  );
}
