export async function register() {
  // Only run on the server (not in Edge runtime)
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { registerAllJobs } = await import("./lib/jobs");
    const { startScheduler } = await import("./lib/scheduler");

    registerAllJobs();
    startScheduler();
  }
}
