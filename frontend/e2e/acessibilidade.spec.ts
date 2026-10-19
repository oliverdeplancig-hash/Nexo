import { test } from "@playwright/test";

import { entrar, semViolacoesGraves } from "./apoio";

test("telas sem login: entrada e recuperação de senha", async ({ page }) => {
  for (const tela of ["/entrar", "/esqueci-senha", "/redefinir-senha?u=x&t=y", "/ativar-conta?u=x&t=y"]) {
    await page.goto(tela);
    await page.waitForLoadState("networkidle");
    await semViolacoesGraves(page, tela);
  }
});

for (const [usuario, telas] of [
  ["servidor.demo", ["/", "/assistente", "/repositorio", "/busca?q=ferias", "/colecoes", "/setores", "/ajuda", "/documentos/1"]],
  ["admin.demo", ["/administracao", "/administracao?aba=saude", "/perfil", "/motor", "/motor?aba=lacunas", "/painel-acervo", "/auditoria", "/importacao"]],
] as const) {
  test(`telas de ${usuario}`, async ({ page }) => {
    await entrar(page, usuario);
    for (const tela of telas) {
      await page.goto(tela);
      await page.waitForLoadState("networkidle");
      await semViolacoesGraves(page, tela);
    }
  });
}
