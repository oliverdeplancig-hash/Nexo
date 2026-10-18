/** Datas DD/MM/AAAA e horários em 24 h, conforme o padrão do projeto. */

const fusoHorario = undefined; // usa o fuso do navegador

export function data(valor?: string | null): string {
  if (!valor) return "—";
  const d = valor.length === 10 ? new Date(`${valor}T12:00:00`) : new Date(valor);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: fusoHorario });
}

export function dataHora(valor?: string | null): string {
  if (!valor) return "—";
  const d = new Date(valor);
  return `${data(valor)} ${d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
}

export function relativo(valor?: string | null): string {
  if (!valor) return "—";
  const d = new Date(valor);
  const hoje = new Date();
  const ontem = new Date();
  ontem.setDate(hoje.getDate() - 1);
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", hour12: false });
  if (d.toDateString() === hoje.toDateString()) return `Hoje, ${hora}`;
  if (d.toDateString() === ontem.toDateString()) return `Ontem, ${hora}`;
  return data(valor);
}

export function tamanho(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
}

export const rotuloClassificacao: Record<string, string> = {
  geral: "Geral",
  setor: "Restrito ao setor",
  restrito: "Restrito",
};

export const rotuloStatus: Record<string, string> = {
  recebido: "Arquivo recebido",
  extraindo: "Extração de conteúdo",
  metadados: "Identificação de metadados",
  indexando: "Indexação para pesquisa",
  disponivel: "Disponível para consulta",
  falha: "Falha no processamento",
  arquivado: "Arquivado",
};

export const rotuloAcao: Record<string, string> = {
  consultar: "Consultar",
  visualizar: "Visualizar",
  baixar: "Baixar",
  editar: "Editar",
  compartilhar: "Compartilhar",
  administrar: "Administrar",
};
