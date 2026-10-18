import { expect, test } from "@playwright/test";

import { entrar, semViolacoesGraves } from "./apoio";

test("@celular navegação inferior, menu e ajuda funcionam no smartphone", async ({ page }) => {
  await entrar(page, "servidor.demo");
  const inferior = page.getByRole("navigation", { name: "Navegação rápida" });
  await expect(inferior).toBeVisible();
  await inferior.getByRole("button", { name: "Repositório" }).click();
  await expect(page).toHaveURL(/\/repositorio/);
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await page.getByRole("link", { name: "Pastas e coleções" }).click();
  await expect(page.getByRole("heading", { name: "Pastas e coleções" })).toBeVisible();
  await page.getByRole("link", { name: "Ajuda sobre esta tela" }).click();
  await expect(page.getByRole("button", { name: "Coleções (pastas)" })).toHaveAttribute("aria-expanded", "true");
  // sem rolagem horizontal
  const larguraExtra = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(larguraExtra).toBeLessThanOrEqual(0);
  await semViolacoesGraves(page, "/ajuda (celular)");
});
