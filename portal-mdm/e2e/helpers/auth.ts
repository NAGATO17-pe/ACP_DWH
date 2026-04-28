import type { Page } from "@playwright/test";

/**
 * Inject a fake JWT cookie so Playwright tests don't need a real FastAPI.
 * The cookie bypasses the login page; proxy.ts does an optimistic decode.
 *
 * Payload: { sub, role, exp: now + 8h }
 * Signed with an empty secret (HS256) — only valid for tests.
 */
function buildFakeJwt(role: "analyst" | "admin" | "executive", name: string): string {
  const encode = (obj: object) =>
    Buffer.from(JSON.stringify(obj))
      .toString("base64url");

  const header = encode({ alg: "HS256", typ: "JWT" });
  const exp = Math.floor(Date.now() / 1000) + 8 * 3600;
  const payload = encode({ sub: "test-user", role, name, exp });
  // Signature is placeholder — proxy.ts uses optimistic decode without verification
  const sig = "test-sig";
  return `${header}.${payload}.${sig}`;
}

export async function loginAs(
  page: Page,
  role: "analyst" | "admin" | "executive",
  name = "Test User",
) {
  await page.context().addCookies([
    {
      name: process.env.JWT_COOKIE_NAME ?? "mdm_session",
      value: buildFakeJwt(role, name),
      domain: "localhost",
      path: "/",
      httpOnly: true,
      secure: false,
      sameSite: "Lax",
    },
  ]);
}
