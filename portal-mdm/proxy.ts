import { NextResponse, type NextRequest } from "next/server";
import { decodeJwt } from "jose";
import {
  isPublicPath,
  isRoleAllowed,
  isValidRole,
  ROLE_HOME,
} from "@/lib/auth/rbac";

const COOKIE = process.env.JWT_COOKIE_NAME ?? "mdm_session";

/**
 * Edge-friendly auth + RBAC gate.
 * Note: this performs an *optimistic* JWT decode (no signature verification).
 * Full verification happens server-side in route handlers and Server Components
 * via lib/auth/session.ts. See Next.js docs: app/guides/authentication.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) return NextResponse.next();

  const token = request.cookies.get(COOKIE)?.value;
  if (!token) return redirectToLogin(request);

  let role: unknown;
  let exp: number | undefined;
  try {
    const claims = decodeJwt(token);
    role = claims.role;
    exp = typeof claims.exp === "number" ? claims.exp : undefined;
  } catch {
    return redirectToLogin(request);
  }

  if (exp && exp * 1000 < Date.now()) return redirectToLogin(request);
  if (!isValidRole(role)) return redirectToLogin(request);

  if (pathname === "/" || !isRoleAllowed(role, pathname)) {
    return NextResponse.redirect(new URL(ROLE_HOME[role], request.url));
  }

  return NextResponse.next();
}

function redirectToLogin(request: NextRequest) {
  const url = new URL("/login", request.url);
  url.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = {
  // Run on app routes; skip Next internals and static assets.
  matcher: ["/((?!_next/|api/auth/|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
