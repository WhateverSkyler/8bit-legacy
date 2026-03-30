import "server-only";
import * as cron from "node-cron";
import { db } from "@db/index";
import { automationRuns } from "@db/schema";
import { desc, eq } from "drizzle-orm";

export interface ScheduledJob {
  name: string;
  cron: string;
  handler: () => Promise<{ itemsProcessed: number; itemsChanged: number; metadata?: Record<string, unknown> }>;
  enabled: boolean;
  description: string;
}

// In-memory lock to prevent overlapping runs of the same job
const runningJobs = new Map<string, boolean>();

// Track cron task references for cleanup
const cronTasks = new Map<string, ReturnType<typeof cron.schedule>>();

// Registered job definitions (handlers added by each phase)
const jobRegistry = new Map<string, ScheduledJob>();

/**
 * Register a job definition. Call this from each phase's initialization.
 * The job won't run until startScheduler() is called.
 */
export function registerJob(job: ScheduledJob): void {
  jobRegistry.set(job.name, job);
}

/**
 * Enable or disable a registered job at runtime.
 */
export function setJobEnabled(name: string, enabled: boolean): void {
  const job = jobRegistry.get(name);
  if (job) {
    job.enabled = enabled;
  }
}

/**
 * Execute a job manually (outside its cron schedule).
 * Respects the lock — won't run if already running.
 */
export async function runJobNow(
  name: string
): Promise<{ success: boolean; runId?: number; error?: string }> {
  const job = jobRegistry.get(name);
  if (!job) return { success: false, error: `Job "${name}" not found` };
  return executeJob(job);
}

/**
 * Core job execution with locking, logging, and error handling.
 */
async function executeJob(
  job: ScheduledJob
): Promise<{ success: boolean; runId?: number; error?: string }> {
  if (runningJobs.get(job.name)) {
    return { success: false, error: `Job "${job.name}" is already running` };
  }

  runningJobs.set(job.name, true);
  const startedAt = new Date().toISOString();

  // Create automation run record
  const run = db
    .insert(automationRuns)
    .values({ jobName: job.name, startedAt, status: "running" })
    .returning()
    .get();

  try {
    const result = await job.handler();

    db.update(automationRuns)
      .set({
        finishedAt: new Date().toISOString(),
        status: "success",
        itemsProcessed: result.itemsProcessed,
        itemsChanged: result.itemsChanged,
        metadataJson: result.metadata ? JSON.stringify(result.metadata) : null,
      })
      .where(eq(automationRuns.id, run.id))
      .run();

    return { success: true, runId: run.id };
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : String(err);
    console.error(`[Scheduler] Job "${job.name}" failed:`, errorMessage);

    db.update(automationRuns)
      .set({
        finishedAt: new Date().toISOString(),
        status: "failed",
        errorMessage,
      })
      .where(eq(automationRuns.id, run.id))
      .run();

    return { success: false, runId: run.id, error: errorMessage };
  } finally {
    runningJobs.set(job.name, false);
  }
}

/**
 * Start all registered and enabled cron jobs.
 * Safe to call multiple times — existing tasks are destroyed first.
 */
export function startScheduler(): void {
  // Clean up existing tasks
  for (const [, task] of cronTasks) {
    task.stop();
  }
  cronTasks.clear();

  for (const [name, job] of jobRegistry) {
    if (!job.enabled) continue;

    if (!cron.validate(job.cron)) {
      console.error(`[Scheduler] Invalid cron for "${name}": ${job.cron}`);
      continue;
    }

    const task = cron.schedule(
      job.cron,
      async () => {
        console.log(`[Scheduler] Running "${name}" at ${new Date().toISOString()}`);
        await executeJob(job);
      },
      { timezone: "America/New_York" }
    );

    cronTasks.set(name, task);
    console.log(`[Scheduler] Registered "${name}" — ${job.cron}`);
  }

  console.log(`[Scheduler] Started with ${cronTasks.size} active jobs`);
}

/**
 * Stop all scheduled jobs.
 */
export function stopScheduler(): void {
  for (const [, task] of cronTasks) {
    task.stop();
  }
  cronTasks.clear();
  console.log("[Scheduler] Stopped all jobs");
}

/**
 * Get status of all registered jobs for the dashboard.
 */
export function getSchedulerStatus(): Array<{
  name: string;
  cron: string;
  enabled: boolean;
  running: boolean;
  description: string;
  lastRun?: { id: number; status: string; finishedAt: string | null; itemsProcessed: number | null; itemsChanged: number | null };
}> {
  const statuses = [];

  for (const [name, job] of jobRegistry) {
    // Get last run from DB
    const lastRuns = db
      .select()
      .from(automationRuns)
      .where(eq(automationRuns.jobName, name))
      .orderBy(desc(automationRuns.startedAt))
      .limit(1)
      .all();

    const lastRun = lastRuns[0];

    statuses.push({
      name,
      cron: job.cron,
      enabled: job.enabled,
      running: runningJobs.get(name) ?? false,
      description: job.description,
      lastRun: lastRun
        ? {
            id: lastRun.id,
            status: lastRun.status,
            finishedAt: lastRun.finishedAt,
            itemsProcessed: lastRun.itemsProcessed,
            itemsChanged: lastRun.itemsChanged,
          }
        : undefined,
    });
  }

  return statuses;
}
