import { expect, test } from "@playwright/test";

import { entrar } from "./apoio";

test("administrador cadastra usuário com senha gerada; no 1º acesso a pessoa cria a própria senha", async ({ browser }) => {
  const login = `novo.${Date.now().toString(36)}`;
  const admin = await browser.newPage();
  await entrar(admin, "admin.demo");
  await admin.goto("/administracao");
  await admin.getByRole("button", { name: "Cadastrar usuário" }).click();
  const dialogo = admin.getByRole("dialog");
  await dialogo.getByLabel("Usuário").fill(login);
  await dialogo.getByLabel("Nome de exibição").fill("Pessoa de Teste");
  await dialogo.getByLabel("E-mail institucional").fill(`${login}@exemplo.test`);
  await dialogo.getByRole("button", { name: "Salvar e enviar acesso" }).click();

  // sem servidor de e-mail no ambiente de testes: a senha aparece uma única vez para quem cadastrou
  const acesso = admin.getByRole("dialog", { name: "Acesso criado" });
  await expect(acesso).toContainText("não está configurado");
  const senha = (await acesso.getByText(/Senha temporária:/).locator("strong").textContent())!.trim();
  expect(senha).toHaveLength(14);
  await acesso.getByRole("button", { name: "Concluir" }).click();
  await expect(admin.getByRole("row").filter({ hasText: login })).toContainText("Aguardando 1º acesso");

  const pessoa = await browser.newPage();
  await pessoa.goto("/entrar");
  await pessoa.getByLabel("Usuário").fill(login);
  await pessoa.getByLabel("Senha").fill(senha);
  await pessoa.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(pessoa.getByRole("heading", { name: "Crie a sua senha" })).toBeVisible();
  await pessoa.locator("#senha-atual").fill(senha);
  await pessoa.locator("#senha-nova").fill("Minha-Senha-Pessoal-2026");
  await pessoa.locator("#senha-confirmacao").fill("Minha-Senha-Pessoal-2026");
  await pessoa.getByRole("button", { name: "Criar senha e continuar" }).click();
  await expect(pessoa.getByRole("heading", { name: /Olá/ })).toBeVisible();

  // a senha temporária não vale mais; a nova vale
  const outra = await browser.newPage();
  await outra.goto("/entrar");
  await outra.getByLabel("Usuário").fill(login);
  await outra.getByLabel("Senha").fill(senha);
  await outra.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(outra.getByText("Usuário ou senha inválidos.")).toBeVisible();
  await outra.getByLabel("Senha").fill("Minha-Senha-Pessoal-2026");
  await outra.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(outra.getByRole("heading", { name: /Olá/ })).toBeVisible();
});

test("servidor altera a própria senha no perfil", async ({ page }) => {
  await entrar(page, "servidor.demo");
  await page.goto("/perfil");
  const secao = page.getByRole("region", { name: "Alterar senha" });
  await expect(secao.locator("#senha-atual")).toBeVisible();
  await expect(secao.getByRole("button", { name: "Alterar senha" })).toBeDisabled();
});
