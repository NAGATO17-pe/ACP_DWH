/**
 * Thin fetch wrapper for the FastAPI backend.
 * - Server-side: forwards the JWT cookie automatically.
 * - Client-side: relies on the httpOnly cookie set at /api/auth/login.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

type Json = Record<string, unknown> | unknown[] | string | number | boolean | null;

interface ApiOptions extends Omit<RequestInit, "body"> {
  body?: Json;
  /** Forwarded JWT (server-side calls). Client calls leave undefined. */
  token?: string;
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { body, token, headers, ...rest } = options;

  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: {
      "content-type": "application/json",
      accept: "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: rest.cache ?? "no-store",
  });

  const text = await res.text();
  const parsed: unknown = text ? safeJson(text) : null;

  if (!res.ok) {
    const message =
      (parsed && typeof parsed === "object" && "detail" in parsed
        ? String((parsed as { detail: unknown }).detail)
        : res.statusText) || "Request failed";
    throw new ApiError(res.status, message, parsed);
  }

  return parsed as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
