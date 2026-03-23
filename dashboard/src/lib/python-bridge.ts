import "server-only";
import { spawn } from "child_process";
import { join } from "path";

const SCRIPTS_DIR = join(process.cwd(), "..", "scripts");

interface PythonResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

/**
 * Run a Python script from the scripts/ directory.
 * Used for pricecharting-scraper.py and social-generator.py.
 */
export async function runPython(
  script: string,
  args: string[] = [],
  timeoutMs: number = 30000
): Promise<PythonResult> {
  const scriptPath = join(SCRIPTS_DIR, script);

  return new Promise((resolve, reject) => {
    const proc = spawn("python3", [scriptPath, ...args], {
      cwd: SCRIPTS_DIR,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
      },
      timeout: timeoutMs,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      resolve({ stdout, stderr, exitCode: code ?? 1 });
    });

    proc.on("error", (err) => {
      reject(new Error(`Failed to run ${script}: ${err.message}`));
    });
  });
}

/**
 * Run the social post generator and return parsed JSON.
 */
export async function generateSocialPosts(
  batch: number = 10,
  type?: string
): Promise<unknown[]> {
  const args = ["--batch", batch.toString(), "--json"];
  if (type) args.push("--type", type);

  const result = await runPython("social-generator.py", args);

  if (result.exitCode !== 0) {
    console.error("social-generator.py stderr:", result.stderr);
    throw new Error(`Social generator failed: ${result.stderr}`);
  }

  try {
    return JSON.parse(result.stdout);
  } catch {
    throw new Error("Failed to parse social generator output as JSON");
  }
}

/**
 * Search PriceCharting via the scraper script.
 */
export async function searchPriceCharting(
  query: string
): Promise<unknown[]> {
  const result = await runPython(
    "pricecharting-scraper.py",
    ["--search", query],
    15000
  );

  if (result.exitCode !== 0) {
    console.error("pricecharting-scraper.py stderr:", result.stderr);
    return [];
  }

  // The scraper outputs formatted text, not JSON.
  // Parse the table output into structured data.
  // For now, return the raw text — we'll enhance this later.
  return [{ raw: result.stdout }];
}
