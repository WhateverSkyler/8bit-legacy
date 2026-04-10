"use client";

import { cn } from "@/lib/utils";
import { useSidebar } from "@/components/providers/sidebar-provider";
import { motion } from "framer-motion";
import { usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  LayoutDashboard,
  ShoppingCart,
  Truck,
  Package,
  Search,
  Share2,
  Target,
  BarChart3,
  Settings,
  PanelLeftClose,
  PanelLeft,
  Clock,
  Sparkles,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/orders", label: "Orders", icon: ShoppingCart },
  { href: "/fulfillment", label: "Fulfillment", icon: Truck },
  { href: "/inventory", label: "Inventory", icon: Package },
  { href: "/pokemon", label: "Pokemon Import", icon: Sparkles },
  { href: "/ebay", label: "eBay Finder", icon: Search },
  { href: "/social", label: "Social Media", icon: Share2 },
  { href: "/ads", label: "Google Ads", icon: Target },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/scheduler", label: "Scheduler", icon: Clock },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const { collapsed, toggle } = useSidebar();
  const pathname = usePathname();

  return (
    <motion.aside
      className="fixed left-0 top-0 z-40 flex h-full flex-col border-r border-border bg-bg-surface"
      animate={{ width: collapsed ? 80 : 280 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Logo */}
      <div className="flex h-[var(--topbar-height)] items-center border-b border-border px-4 overflow-hidden">
        {collapsed ? (
          <Image
            src="/apple-touch-icon.png"
            alt="8-Bit Legacy"
            width={32}
            height={14}
            className="shrink-0 object-contain"
          />
        ) : (
          <Image
            src="/logo.png"
            alt="8-Bit Legacy"
            width={120}
            height={36}
            className="shrink-0 h-9 w-auto object-contain"
            priority
          />
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <ul className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    isActive
                      ? "text-accent-cyan bg-cyan-glow"
                      : "text-text-secondary hover:text-text-primary hover:bg-bg-surface"
                  )}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <motion.div
                      className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-r-full bg-accent-cyan"
                      layoutId="sidebarActive"
                      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
                    />
                  )}
                  <item.icon
                    size={20}
                    className={cn(
                      "shrink-0 transition-colors",
                      isActive
                        ? "text-accent-cyan"
                        : "text-text-muted group-hover:text-text-secondary"
                    )}
                  />
                  <motion.span
                    className="overflow-hidden whitespace-nowrap"
                    animate={{
                      opacity: collapsed ? 0 : 1,
                      width: collapsed ? 0 : "auto",
                    }}
                    transition={{ duration: 0.2 }}
                  >
                    {item.label}
                  </motion.span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-border p-3">
        <button
          onClick={toggle}
          className="flex w-full items-center justify-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-sm text-text-muted hover:text-text-primary hover:bg-bg-surface transition-colors"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeft size={20} /> : <PanelLeftClose size={20} />}
          <motion.span
            className="overflow-hidden whitespace-nowrap"
            animate={{
              opacity: collapsed ? 0 : 1,
              width: collapsed ? 0 : "auto",
            }}
            transition={{ duration: 0.2 }}
          >
            Collapse
          </motion.span>
        </button>
      </div>
    </motion.aside>
  );
}
