import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Módulo Admin — Entidades", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin", "Carmen Vega");
    await page.goto("/entities");
  });

  test("carga la tabla de entidades", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /Entidades MDM/i })).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();
  });

  test("muestra filtros por tipo de entidad", async ({ page }) => {
    const tabs = ["Todas", "Clientes", "Productos", "Proveedores", "Ubicaciones"];
    for (const label of tabs) {
      await expect(page.getByRole("tab", { name: label })).toBeVisible();
    }
  });

  test("filtra por tipo al hacer clic en tab", async ({ page }) => {
    await page.getByRole("tab", { name: "Clientes" }).click();
    const count = page.getByText(/registros/i);
    await expect(count).toBeVisible();
  });

  test("filtra por texto en el buscador", async ({ page }) => {
    await page.getByPlaceholder(/buscar/i).fill("Andes");
    await expect(page.getByRole("table")).toBeVisible();
    const rows = page.getByRole("row");
    // Header row + at least one match
    expect(await rows.count()).toBeGreaterThan(1);
  });

  test("pagina correctamente", async ({ page }) => {
    const nextBtn = page.getByRole("button", { name: /siguiente/i });
    if (await nextBtn.isEnabled()) {
      await nextBtn.click();
      await expect(page.getByText(/página 2/i)).toBeVisible();
    }
  });
});
