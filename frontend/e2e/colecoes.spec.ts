import { expect, test } from "@playwright/test";

import { entrar, unico } from "./apoio";

test("servidor cria coleção pessoal, organiza documentos e exclui sem apagar documentos", async ({ page }) => {
  const nome = unico("Leituras");
  await entrar(page, "servidor.demo");
  await page.goto("/repositorio");
  await page.getByRole("checkbox", { name: "Selecionar todos" }).check();
  await page.getByRole("button", { name: "Adicionar à coleção" }).click();
  await page.getByRole("button", { name: "Nova coleção" }).click();
  await page.locator("#colecao-nome").fill(nome);
  await page.getByRole("button", { name: "Criar coleção" }).click();
  await expect(page.getByText(/adicionado\(s\) a “/)).toBeVisible();

  await page.goto("/colecoes");
  await page.getByRole("link", { name: new RegExp(nome) }).click();
  await expect(page.getByText(`Coleção: ${nome}`)).toBeVisible();
  const linhas = page.getByRole("table", { name: "Documentos" }).getByRole("row");
  const antes = (await linhas.count()) - 1;
  expect(antes).toBeGreaterThan(0);

  await page.getByRole("checkbox").nth(1).check();
  await page.getByRole("button", { name: "Remover da coleção" }).click();
  await expect(page.getByText("removido(s) da coleção")).toBeVisible();
  await expect(linhas).toHaveCount(antes); // cabeçalho + (antes - 1)

  await page.getByRole("button", { name: "Excluir", exact: true }).click();
  await page.getByRole("button", { name: "Excluir coleção" }).click();
  await expect(page).toHaveURL(/\/colecoes$/);
  await expect(page.getByText(nome)).toHaveCount(0);
  await page.goto("/repositorio");
  await expect(page.getByRole("link", { name: /Procedimento de solicitação de férias/ }).first()).toBeVisible();
});
