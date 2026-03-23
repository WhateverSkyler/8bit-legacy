"use client";

import { cn } from "@/lib/utils";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle, AlertTriangle, XCircle, Info, X } from "lucide-react";
import { createContext, useCallback, useContext, useState } from "react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastContextType {
  toast: (type: ToastType, title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType>({
  toast: () => {},
});

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle size={20} className="text-status-success" />,
  error: <XCircle size={20} className="text-status-error" />,
  warning: <AlertTriangle size={20} className="text-status-warning" />,
  info: <Info size={20} className="text-status-info" />,
};

const BORDER_COLORS: Record<ToastType, string> = {
  success: "border-l-status-success",
  error: "border-l-status-error",
  warning: "border-l-status-warning",
  info: "border-l-status-info",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback(
    (type: ToastType, title: string, message?: string) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, type, title, message }]);
      const duration = type === "error" || type === "warning" ? 6000 : 4000;
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    },
    []
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-[360px]">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 40 }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
              className={cn(
                "flex items-start gap-3 rounded-[var(--radius-card)] border border-border border-l-4 bg-bg-surface p-4 shadow-[var(--shadow-dropdown)]",
                BORDER_COLORS[t.type]
              )}
              role="status"
              aria-live="polite"
            >
              <span className="mt-0.5 shrink-0">{ICONS[t.type]}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text-primary">
                  {t.title}
                </p>
                {t.message && (
                  <p className="mt-0.5 text-xs text-text-secondary">
                    {t.message}
                  </p>
                )}
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="shrink-0 text-text-muted hover:text-text-primary transition-colors"
              >
                <X size={16} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
