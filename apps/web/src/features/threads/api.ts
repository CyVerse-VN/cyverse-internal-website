import { z } from "zod";

export class ThreadsApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ThreadsApiError";
  }
}

export async function threadsApi<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/threads${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    let message = response.status === 401 ? "Your session expired. Sign in again." : "The Threads request could not be completed.";
    try {
      const body: unknown = await response.json();
      const error = z.object({ detail: z.string() }).safeParse(body);
      if (error.success) message = error.data.detail;
    } catch {
      // Keep a safe message if an upstream service returns a non-JSON error.
    }
    throw new ThreadsApiError(message, response.status);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error("The Threads service returned an unexpected response.");
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw new Error("The Threads service returned an unexpected response.");
  return parsed.data;
}
