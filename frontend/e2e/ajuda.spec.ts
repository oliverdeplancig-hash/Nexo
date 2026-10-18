import { expect, test } from "@playwright/test";

import { entrar } from "./apoio";

test("ajuda do servidor não mostra tópicos de administração", async ({ page }) => {
  await entrar(page, "servidor.demo");
  await page.goto("/ajuda");
  await expect(page.getByRole("heading", { name: "Encontrar informação" })).toBeVisible();
  for (const grupo of ["Gestão documental", "Administração", "Auditoria"]) {
    await expect(page.getByRole("heading", { name: grupo, exact: true })).toHaveCount(0);
  }
});

test("ajuda do administrador mostra todos os grupos", async ({ page }) => {
  await entrar(page, "admin.demo");
  await page.goto("/ajuda");
  for (const grupo of ["Gestão documental", "Administração", "Auditoria"]) {
    await expect(page.getByRole("heading", { name: grupo, exact: true })).toBeVisible();
  }
});

test("o botão ? abre o tópico da tela atual", async ({ page }) => {
  await entrar(page, "servidor.demo");
  await page.goto("/colecoes");
  await page.getByRole("link", { name: "Ajuda sobre esta tela" }).click();
  await expect(page.getByRole("button", { name: "Coleções (pastas)" })).toHaveAttribute("aria-expanded", "true");
});

test("busca na ajuda ignora acentos", async ({ page }) => {
  await entrar(page, "servidor.demo");
  await page.goto("/ajuda");
  await page.getByLabel("Buscar na ajuda").fill("colecao");
  await expect(page.getByRole("button", { name: "Coleções (pastas)" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Perguntar ao assistente" }).first()).toBeVisible();
});
