export type Role = "analyst" | "admin" | "executive";

export const ROLES: Role[] = ["analyst", "admin", "executive"];

/**
 * Path prefixes each role is allowed to access.
 * Anything outside its prefixes redirects to the role's home.
 */
export const ROLE_ALLOWED_PREFIXES: Record<Role, string[]> = {
  analyst: ["/explore", "/models", "/reports"],
  admin: ["/entities", "/workflows", "/quality", "/audit"],
  executive: ["/overview"],
};

export const ROLE_HOME: Record<Role, string> = {
  analyst: "/explore",
  admin: "/entities",
  executive: "/overview",
};

/** Routes available to any authenticated user (regardless of role). */
export const SHARED_AUTHENTICATED_PREFIXES = ["/api/auth/logout"];

/** Public routes (skip auth check entirely). */
export const PUBLIC_PREFIXES = ["/login", "/api/auth/login"];

export function isRoleAllowed(role: Role, pathname: string): boolean {
  if (SHARED_AUTHENTICATED_PREFIXES.some((p) => pathname.startsWith(p))) {
    return true;
  }
  return ROLE_ALLOWED_PREFIXES[role].some((p) => pathname.startsWith(p));
}

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));
}

export function isValidRole(value: unknown): value is Role {
  return typeof value === "string" && (ROLES as string[]).includes(value);
}
