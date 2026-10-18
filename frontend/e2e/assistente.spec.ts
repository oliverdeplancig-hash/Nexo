import { expect, test } from "@playwright/test";

import { entrar } from "./apoio";

test("servidor pergunta, recebe resposta aprovada com fonte e avalia; a gestão vê a lacuna", async ({ browser }) => {
  const servidor = await browser.newPage();
  await entrar(servidor, "servidor.demo");
  await servidor.goto("/assistente");
  const campo = servidor.getByPlaceholder(/Digite sua pergunta/);
  await campo.fill("Como solicito férias?");
  await campo.press("Enter");
  const resposta = servidor.getByRole("article", { name: "Resposta do assistente" }).last();
  await expect(resposta).toContainText("antecedência mínima de 30 dias", { timeout: 30_000 });
  await expect(resposta.getByText("Resposta aprovada")).toBeVisible();
  await expect(resposta.getByRole("region", { name: "Fontes consultadas" })).toContainText("Procedimento de solicitação de férias");

  // pergunta sem resposta nos documentos + avaliação negativa
  await campo.fill("Qual o cardápio do refeitório nesta semana?");
  await campo.press("Enter");
  const semFonte = servidor.getByRole("article", { name: "Resposta do assistente" }).last();
  await expect(semFonte).toContainText("Não encontrei fontes suficientes", { timeout: 30_000 });
  await semFonte.getByRole("button", { name: "Resposta não ajudou" }).click();
  await servidor.getByRole("button", { name: "Não respondeu à pergunta" }).click();
  await servidor.getByRole("button", { name: "Enviar" }).click();
  await expect(semFonte.getByRole("button", { name: "Resposta não ajudou" })).toHaveAttribute("aria-pressed", "true");

  const gestao = await browser.newPage();
  await entrar(gestao, "ti.demo");
  await gestao.goto("/motor?aba=lacunas");
  const lacuna = gestao.getByRole("article").filter({ hasText: "cardápio do refeitório" });
  await expect(lacuna).toBeVisible();
  await expect(lacuna).toContainText("Não útil: Não respondeu à pergunta");
  await expect(lacuna).not.toContainText("Servidor (demo)"); // sem identificar quem perguntou
});
