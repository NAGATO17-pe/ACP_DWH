import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Módulo Analista", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "analyst", "Andrea Salas");
  });

  test("el home del analista es /explore", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/explore/);
  });

  test("muestra KPIs en la página de exploración", async ({ page }) => {
    await page.goto("/explore");
    await expect(page.getByText(/datasets disponibles/i)).toBeVisible();
    await expect(page.getByText(/modelos en producción/i)).toBeVisible();
  });

  test("lista de modelos muestra catálogo de cards", async ({ page }) => {
    await page.goto("/models");
    await expect(page.getByRole("heading", { name: /modelos predictivos/i })).toBeVisible();
    const links = page.getByRole("link").filter({ hasText: /XGBoost|LightGBM|Random Forest/i });
    expect(await links.count()).toBeGreaterThan(0);
  });

  test("detalle de modelo muestra tabs de métricas", async ({ page }) => {
    await page.goto("/models/MDL-001");
    await expect(page.getByRole("tab", { name: /métricas/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /importancia/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /confusión/i })).toBeVisible();
  });

  test("analista no puede acceder a /entities (redirige a /explore)", async ({ page }) => {
    await page.goto("/entities");
    await expect(page).toHaveURL(/\/explore/);
  });
});
