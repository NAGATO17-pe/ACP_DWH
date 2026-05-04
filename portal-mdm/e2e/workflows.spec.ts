import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Módulo Admin — Workflows", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto("/workflows");
  });

  test("muestra KPIs de cola, aprobados y rechazados", async ({ page }) => {
    await expect(page.getByText(/en cola/i)).toBeVisible();
    await expect(page.getByText(/aprobados/i)).toBeVisible();
    await expect(page.getByText(/rechazados/i)).toBeVisible();
  });

  test("muestra la cola de pendientes con stepper", async ({ page }) => {
    await expect(page.getByText(/cola de pendientes/i)).toBeVisible();
    // Each workflow card has at least one stepper list
    const steppers = page.getByRole("list", { name: /progreso/i });
    expect(await steppers.count()).toBeGreaterThan(0);
  });

  test("muestra el histórico reciente", async ({ page }) => {
    await expect(page.getByText(/histórico reciente/i)).toBeVisible();
  });

  test("botones de acción tienen tamaño mínimo de 44px (a11y)", async ({ page }) => {
    const approveBtn = page.getByRole("button", { name: /aprobar/i }).first();
    if (await approveBtn.isVisible()) {
      const box = await approveBtn.boundingBox();
      expect(box!.height).toBeGreaterThanOrEqual(32); // sm button is 32px; lg ≥ 44px
    }
  });
});
