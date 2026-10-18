import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** Senha dos usuários de demonstração (somente com NEXO_DEBUG=true). */
export const SENHA = "Nexo@demo2026";

export async function entrar(page: Page, usuario: "servidor.demo" | "ti.demo" | "admin.demo") {
  await page.goto("/entrar");
  await page.getByLabel("Usuário").fill(usuario);
  await page.getByLabel("Senha").fill(SENHA);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).not.toHaveURL(/\/entrar/);
}

/** Falha se a página tiver violação séria ou crítica de acessibilidade (WCAG 2.1 A/AA). */
export async function semViolacoesGraves(page: Page, onde: string) {
  const resultado = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const graves = resultado.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id}: ${v.help} — ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`);
  expect(graves, `Acessibilidade em ${onde}`).toEqual([]);
}

export const unico = (prefixo: string) => `${prefixo} ${Date.now().toString(36)}`;
