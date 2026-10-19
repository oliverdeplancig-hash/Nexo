import { expect, test } from "@playwright/test";

// Sem e-mail configurado (como na suíte), a recuperação fica desligada e a tela explica o que fazer (ADR-024).
test("sem e-mail configurado, a entrada não oferece a recuperação e o link inválido orienta", async ({ page }) => {
  await page.goto("/entrar");
  await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Esqueci minha senha" })).toHaveCount(0);

  await page.goto("/esqueci-senha");
  await page.getByLabel("Usuário ou e-mail").fill("servidor.demo");
  await page.getByRole("button", { name: "Enviar link" }).click();
  await expect(page.getByRole("alert")).toContainText("Procure o administrador");

  await page.goto("/redefinir-senha?u=x&t=y");
  await expect(page.getByRole("alert")).toContainText(/não está ativa|não vale mais/);
  await expect(page.getByRole("link", { name: "Voltar para a entrada" })).toBeVisible();
});
