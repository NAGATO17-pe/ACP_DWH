import { cookies } from "next/headers";
import { jwtVerify, decodeJwt } from "jose";
import { isValidRole, type Role } from "./rbac";

export const JWT_COOKIE_NAME = process.env.JWT_COOKIE_NAME ?? "mdm_session";

export interface SessionPayload {
  sub: string;
  role: Role;
  name?: string;
  email?: string;
  exp?: number;
}

/**
 * Server-side session reader. Validates the JWT signature when
 * `JWT_PUBLIC_SECRET` is configured; otherwise decodes without verifying
 * (intended for local dev against a trusted FastAPI backend).
 */
export async function getSession(): Promise<SessionPayload | null> {
  const store = await cookies();
  const token = store.get(JWT_COOKIE_NAME)?.value;
  if (!token) return null;

  try {
    const secret = process.env.JWT_PUBLIC_SECRET;
    const claims = secret
      ? (
          await jwtVerify(
            token,
            new TextEncoder().encode(secret),
            // Algorithms accepted from FastAPI backend
            { algorithms: ["HS256", "HS512"] },
          )
        ).payload
      : decodeJwt(token);

    if (!isValidRole(claims.role)) return null;

    return {
      sub: String(claims.sub ?? ""),
      role: claims.role,
      name: typeof claims.name === "string" ? claims.name : undefined,
      email: typeof claims.email === "string" ? claims.email : undefined,
      exp: typeof claims.exp === "number" ? claims.exp : undefined,
    };
  } catch {
    return null;
  }
}
