import { expect, test } from "@playwright/test";

import { entrar } from "./apoio";

test("revogar tira o documento da busca, mostra a faixa e pode ser desfeito", async ({ page }) => {
  await entrar(page, "admin.demo");
  await page.goto("/repositorio?q=protocolo");
  await page.getByRole("link", { name: /Manual do protocolo/ }).first().click();
  await page.getByRole("button", { name: "Revogar" }).click();
  const dialogo = page.getByRole("dialog");
  await dialogo.getByLabel("Motivo").fill("Revogado pelo teste de ponta a ponta");
  await dialogo.getByRole("button", { name: "Revogar" }).click();
  await expect(page.getByText(/Documento revogado em/)).toBeVisible();

  await page.goto("/busca?q=tramitacao%20protocolo");
  await expect(page.getByText(/Manual do protocolo/)).toHaveCount(0);
  await page.getByLabel("Incluir documentos revogados").check();
  await expect(page.getByText(/Manual do protocolo/).first()).toBeVisible();

  await page.getByRole("article").filter({ hasText: "Manual do protocolo" }).getByRole("button", { name: "Abrir documento" }).first().click();
  await page.getByRole("button", { name: "Restabelecer vigência" }).click();
  await expect(page.getByText(/Documento revogado em/)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Registrar revisão" })).toBeVisible();
});
