"use client";

import { useSidebar } from "@/components/providers/sidebar-provider";
import { motion } from "framer-motion";

export function MainContent({ children }: { children: React.ReactNode }) {
  const { collapsed } = useSidebar();

  return (
    <motion.main
      className="min-h-screen pt-[var(--topbar-height)]"
      animate={{ paddingLeft: collapsed ? 80 : 280 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
    >
      <div className="mx-auto max-w-[1440px] p-6">{children}</div>
    </motion.main>
  );
}
