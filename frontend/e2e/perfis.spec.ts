import { expect, test } from "@playwright/test";

import { entrar, SENHA } from "./apoio";

const GOVERNANCA = ["Painel do acervo", "Importar documentos", "Motor de respostas", "Administração", "Auditoria"];

const ESPERADO: Record<string, string[]> = {
  "servidor.demo": [],
  "ti.demo": ["Painel do acervo", "Importar documentos", "Motor de respostas"],
  "admin.demo": GOVERNANCA,
};

for (const [usuario, itens] of Object.entries(ESPERADO)) {
  test(`menu de ${usuario} mostra só o que o perfil permite`, async ({ page }) => {
    await entrar(page, usuario as never);
    const menu = page.getByRole("navigation").first();
    for (const item of ["Assistente IA", "Repositório documental", "Pastas e coleções", "Ajuda"]) {
      await expect(menu.getByRole("link", { name: item, exact: true })).toBeVisible();
    }
    for (const item of GOVERNANCA) {
      const link = menu.getByRole("link", { name: item, exact: true });
      if (itens.includes(item)) await expect(link).toBeVisible();
      else await expect(link).toHaveCount(0);
    }
  });
}

test("rota administrativa é recusada para o servidor", async ({ page }) => {
  await entrar(page, "servidor.demo");
  await page.goto("/auditoria");
  await expect(page).not.toHaveURL(/\/auditoria/);
});

test("senha errada mostra erro e não entra", async ({ page }) => {
  await page.goto("/entrar");
  await page.getByLabel("Usuário").fill("servidor.demo");
  await page.getByLabel("Senha").fill(SENHA + "x");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByText("Usuário ou senha inválidos.")).toBeVisible();
  await expect(page).toHaveURL(/\/entrar/);
});
