"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatRelativeTime } from "@/lib/utils";
import {
  Clock,
  Play,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Calendar,
  Zap,
} from "lucide-react";
import { useSchedulerStatus, useRunJob } from "@/hooks/use-scheduler";
import type { SchedulerJob } from "@/hooks/use-scheduler";

const JOB_ICONS: Record<string, typeof Clock> = {
  "shopify-product-sync": RefreshCw,
  "google-ads-sync": Zap,
  "fulfillment-check": CheckCircle2,
  "price-sync": RefreshCw,
  "pokemon-price-sync": RefreshCw,
};

function JobCard({ job }: { job: SchedulerJob }) {
  const runJob = useRunJob();
  const Icon = JOB_ICONS[job.name] || Clock;

  const statusBadge = () => {
    if (job.running) {
      return (
        <Badge variant="info">
          <Loader2 size={12} className="mr-1 animate-spin" />
          Running
        </Badge>
      );
    }
    if (!job.enabled) {
      return <Badge variant="neutral">Disabled</Badge>;
    }
    if (job.lastRun?.status === "success") {
      return <Badge variant="success">Healthy</Badge>;
    }
    if (job.lastRun?.status === "failed") {
      return <Badge variant="error">Failed</Badge>;
    }
    return <Badge variant="neutral">Never Run</Badge>;
  };

  return (
    <Card>
      <CardContent>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-cyan-glow">
              <Icon size={20} className="text-accent-cyan" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">{job.name}</h3>
              <p className="text-xs text-text-secondary">{job.description}</p>
            </div>
          </div>
          {statusBadge()}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-xs">
          <div>
            <p className="font-semibold uppercase tracking-wide text-text-muted">Schedule</p>
            <p className="mt-0.5 font-mono text-text-secondary">{job.cron}</p>
          </div>
          <div>
            <p className="font-semibold uppercase tracking-wide text-text-muted">Last Run</p>
            <p className="mt-0.5 text-text-secondary">
              {job.lastRun?.finishedAt
                ? formatRelativeTime(job.lastRun.finishedAt)
                : "Never"}
            </p>
          </div>
          {job.lastRun && (
            <>
              <div>
                <p className="font-semibold uppercase tracking-wide text-text-muted">Processed</p>
                <p className="mt-0.5 text-text-secondary">
                  {job.lastRun.itemsProcessed?.toLocaleString() ?? "—"}
                </p>
              </div>
              <div>
                <p className="font-semibold uppercase tracking-wide text-text-muted">Changed</p>
                <p className="mt-0.5 text-text-secondary">
                  {job.lastRun.itemsChanged?.toLocaleString() ?? "—"}
                </p>
              </div>
            </>
          )}
        </div>

        <div className="mt-4">
          <Button
            variant="secondary"
            size="sm"
            className="w-full"
            disabled={job.running || runJob.isPending}
            onClick={() => runJob.mutate(job.name)}
          >
            {runJob.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Play size={14} />
            )}
            {job.running ? "Running..." : "Run Now"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SchedulerPage() {
  const { data, isLoading, refetch } = useSchedulerStatus();

  const jobs = data?.jobs ?? [];
  const circuitBreakers = data?.circuitBreakers ?? [];
  const activeJobs = jobs.filter((j) => j.enabled).length;
  const healthyJobs = jobs.filter((j) => j.lastRun?.status === "success").length;
  const failedJobs = jobs.filter((j) => j.lastRun?.status === "failed").length;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Scheduler"
        description="Automated job status and controls. All jobs run on America/New_York timezone."
      >
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          <RefreshCw size={14} />
          Refresh
        </Button>
      </PageHeader>

      {/* Overview KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-cyan-glow p-2">
                <Calendar size={20} className="text-accent-cyan" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Active Jobs</p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">{activeJobs}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-green-100 p-2">
                <CheckCircle2 size={20} className="text-green-600" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Healthy</p>
                <p className="text-2xl font-bold tabular-nums text-green-600">{healthyJobs}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-red-100 p-2">
                <XCircle size={20} className="text-red-500" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Failed</p>
                <p className="text-2xl font-bold tabular-nums text-red-500">{failedJobs}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-orange-100 p-2">
                <Clock size={20} className="text-orange-500" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Last Update</p>
                <p className="text-sm font-medium text-text-secondary">
                  {data?.timestamp ? formatRelativeTime(data.timestamp) : "—"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Job Cards */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={32} className="animate-spin text-accent-cyan" />
        </div>
      ) : (
        <motion.div
          className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {jobs.map((job) => (
            <motion.div key={job.name} variants={staggerItem}>
              <JobCard job={job} />
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Circuit Breakers */}
      {circuitBreakers.length > 0 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-text-primary">Circuit Breakers</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {circuitBreakers.map((cb) => (
              <Card key={cb.name}>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {cb.tripped ? (
                        <ShieldAlert size={20} className="text-red-500" />
                      ) : (
                        <ShieldCheck size={20} className="text-green-600" />
                      )}
                      <div>
                        <h3 className="text-sm font-semibold text-text-primary">{cb.name}</h3>
                        <p className="text-xs text-text-muted">
                          Trip count: {cb.tripCount}
                          {cb.lastTripped && ` | Last: ${formatRelativeTime(cb.lastTripped)}`}
                        </p>
                      </div>
                    </div>
                    <Badge variant={cb.tripped ? "error" : "success"}>
                      {cb.tripped ? "Tripped" : "OK"}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
