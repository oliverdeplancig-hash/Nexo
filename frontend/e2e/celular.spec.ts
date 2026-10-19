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
  await semViolacoesGraves(page, "/ajuda (celular)");
});

test("@celular nenhuma tela principal tem rolagem horizontal", async ({ page }) => {
  await entrar(page, "servidor.demo");
  // abre documentos antes, para a página inicial mostrar "recentes" e "continuar de onde parou"
  for (const tela of ["/documentos/1", "/documentos/2", "/", "/assistente", "/repositorio", "/busca?q=ferias", "/colecoes", "/setores", "/historico", "/ajuda", "/perfil"]) {
    await page.goto(tela);
    await page.waitForLoadState("networkidle");
    const extra = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(extra, `rolagem horizontal em ${tela}`).toBeLessThanOrEqual(0);
  }
});
