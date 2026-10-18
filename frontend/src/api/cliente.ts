/** Cliente HTTP do Nexo: sessão por cookie + CSRF no cabeçalho. */

export class ErroApi extends Error {
  constructor(public status: number, message: string, public dados?: unknown) {
    super(message);
  }
}

function lerCookie(nome: string): string {
  const par = document.cookie.split("; ").find((c) => c.startsWith(`${nome}=`));
  return par ? decodeURIComponent(par.split("=")[1]) : "";
}

let csrfGarantido = false;
async function garantirCsrf() {
  if (csrfGarantido && lerCookie("csrftoken")) return;
  await fetch("/api/v1/auth/csrf/", { credentials: "same-origin" });
  csrfGarantido = true;
}

function mensagemDeErro(status: number, corpo: unknown): string {
  if (corpo && typeof corpo === "object") {
    const c = corpo as Record<string, unknown>;
    if (typeof c.detail === "string") return c.detail;
    const primeiro = Object.values(c)[0];
    if (Array.isArray(primeiro) && typeof primeiro[0] === "string") return primeiro[0];
    if (typeof primeiro === "string") return primeiro;
  }
  if (status === 403) return "Seu perfil não tem permissão para esta operação.";
  if (status === 404) return "Conteúdo não encontrado ou indisponível para o seu perfil.";
  if (status >= 500) return "O servidor não respondeu como esperado. Tente novamente em instantes.";
  return "Não foi possível concluir a operação.";
}

export async function api<T = unknown>(caminho: string, opcoes: RequestInit & { json?: unknown } = {}): Promise<T> {
  const metodo = (opcoes.method ?? "GET").toUpperCase();
  const cabecalhos = new Headers(opcoes.headers);
  let corpo = opcoes.body;
  if (opcoes.json !== undefined) {
    cabecalhos.set("Content-Type", "application/json");
    corpo = JSON.stringify(opcoes.json);
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(metodo)) {
    await garantirCsrf();
    cabecalhos.set("X-CSRFToken", lerCookie("csrftoken"));
  }
  let resposta: Response;
  try {
    resposta = await fetch(`/api/v1${caminho}`, { ...opcoes, method: metodo, headers: cabecalhos, body: corpo, credentials: "same-origin" });
  } catch {
    throw new ErroApi(0, "Sem conexão com o servidor. Verifique a rede e tente novamente.");
  }
  if (resposta.status === 204) return undefined as T;
  const tipo = resposta.headers.get("content-type") ?? "";
  const dados = tipo.includes("application/json") ? await resposta.json() : await resposta.text();
  if (!resposta.ok) {
    if (resposta.status === 401 || (resposta.status === 403 && caminho === "/auth/eu/")) {
      window.dispatchEvent(new CustomEvent("nexo:sessao-expirada"));
    }
    throw new ErroApi(resposta.status, mensagemDeErro(resposta.status, dados), dados);
  }
  return dados as T;
}

export function parametros(obj: Record<string, string | number | undefined | null | boolean>): string {
  const p = new URLSearchParams();
  Object.entries(obj).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== false) p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : "";
}
