import { expect, test } from "@playwright/test";

import { entrar } from "./apoio";

test("administrador vê a saúde do sistema; servidor não vê a aba", async ({ browser }) => {
  const admin = await browser.newPage();
  await entrar(admin, "admin.demo");
  await admin.goto("/administracao?aba=saude");
  const lista = admin.getByRole("list", { name: "Verificações" });
  await expect(lista).toContainText("Banco de dados");
  await expect(lista).toContainText("Cópias de segurança");
  await expect(lista).toContainText("Processamento de documentos");
  await expect(admin.getByRole("button", { name: "Verificar agora" })).toBeVisible();

  const servidor = await browser.newPage();
  await entrar(servidor, "servidor.demo");
  await servidor.goto("/administracao?aba=saude");
  await expect(servidor).toHaveURL(/\/$/); // sem função administrativa, volta ao início
});
