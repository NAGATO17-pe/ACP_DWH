import { test, expect } from "@playwright/test";

test.describe("Login page", () => {
  test("muestra el formulario de login", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /Portal MDM/i })).toBeVisible();
    await expect(page.getByLabel(/correo/i)).toBeVisible();
    await expect(page.getByLabel(/contraseña/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /iniciar sesión/i })).toBeVisible();
  });

  test("muestra error de validación con email inválido", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/correo/i).fill("no-es-email");
    await page.getByLabel(/contraseña/i).fill("password123");
    await page.getByLabel(/contraseña/i).blur();
    // Trigger form submit
    await page.getByRole("button", { name: /iniciar sesión/i }).click();
    await expect(page.getByRole("alert").first()).toBeVisible();
  });

  test("muestra error de validación con contraseña corta", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/correo/i).fill("user@empresa.com");
    await page.getByLabel(/contraseña/i).fill("123");
    await page.getByLabel(/contraseña/i).blur();
    await expect(page.getByText(/mínimo 8 caracteres/i)).toBeVisible();
  });

  test("usuario autenticado es redirigido fuera del login", async ({ page }) => {
    // Inject cookie before navigating
    await page.context().addCookies([
      {
        name: "mdm_session",
        value: buildMockJwt("admin"),
        domain: "localhost",
        path: "/",
        httpOnly: true,
        secure: false,
        sameSite: "Lax",
      },
    ]);
    await page.goto("/login");
    await expect(page).not.toHaveURL(/\/login/);
  });
});

function buildMockJwt(role: string) {
  const b64 = (o: object) => Buffer.from(JSON.stringify(o)).toString("base64url");
  const h = b64({ alg: "HS256", typ: "JWT" });
  const p = b64({ sub: "test", role, exp: Math.floor(Date.now() / 1000) + 3600 });
  return `${h}.${p}.sig`;
}
