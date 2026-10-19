/**
 * Testes de ponta a ponta (ADR-017): navegador real contra backend com dados de demonstração e IA falsa.
 *   npm run e2e          (sobe backend e frontend sozinho)
 * Requer PostgreSQL com pgvector; banco em E2E_DATABASE_URL (padrão postgres://nexo:nexo@localhost:5432/nexo_e2e).
 */
import { defineConfig, devices } from "@playwright/test";

const portaBackend = process.env.E2E_PORTA_BACKEND ?? "8001";
const portaFrontend = process.env.E2E_PORTA_FRONTEND ?? "5174";
const base = `http://127.0.0.1:${portaFrontend}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1, // os testes compartilham o mesmo banco de demonstração
  retries: process.env.CI ? 1 : 0,
  timeout: 45_000,
  // No CI, "github" publica cada falha como anotação no próprio GitHub (o log completo fica fora do alcance local).
  reporter: process.env.CI ? [["github"], ["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: base,
    locale: "pt-BR",
    timezoneId: "America/Bahia",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 900 } }, grepInvert: /@celular/ },
    { name: "celular", use: { ...devices["Pixel 7"] }, grep: /@celular/ },
  ],
  webServer: [
    {
      command: "bash ../scripts/e2e-servidor.sh",
      url: `http://127.0.0.1:${portaBackend}/api/v1/saude/`,
      timeout: 180_000,
      reuseExistingServer: !process.env.CI,
      env: { E2E_PORTA_BACKEND: portaBackend, E2E_PORTA_FRONTEND: portaFrontend },
    },
    {
      command: `npx vite --port ${portaFrontend} --strictPort --host 127.0.0.1`,
      url: base,
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      env: { NEXO_BACKEND_URL: `http://127.0.0.1:${portaBackend}` },
    },
  ],
});
