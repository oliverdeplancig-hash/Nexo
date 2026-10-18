export type Acao = "consultar" | "visualizar" | "baixar" | "editar" | "compartilhar" | "administrar";
export type Classificacao = "geral" | "setor" | "restrito";

export interface Paginado<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Usuario {
  id: number;
  username: string;
  nome: string;
  email: string;
  matricula: string;
  setor: { id: number; nome: string; sigla: string } | null;
  perfis: { codigo: string; nome: string }[];
  funcoes: string[];
}

export interface SetorResumo {
  id: number;
  sigla: string;
  nome: string;
}

export interface Setor extends SetorResumo {
  setor_superior: number | null;
  descricao: string;
  competencias: string;
  tipos_demanda: string[];
  servicos: string[];
  procedimentos_relacionados: string[];
  canal_contato: string | null;
  horario_atendimento: string;
  orientacao_acesso: string;
  palavras_chave: string[];
  contato_visivel_para_todos: boolean;
  ativo: boolean;
  atualizado_em: string;
  pontuacao?: number;
  termos_encontrados?: string[];
}

export interface DocumentoLista {
  id: number;
  titulo: string;
  tipo_arquivo: string;
  setor_responsavel: SetorResumo;
  categoria: string | null;
  responsavel: string | null;
  classificacao: Classificacao | null;
  status: string;
  versao: number;
  data_documento: string | null;
  numero_referencia: string;
  atualizado_em: string;
  acoes_permitidas: Acao[];
  favorito: boolean;
}

export interface Colecao {
  id: number;
  nome: string;
  descricao: string;
  superior: number | null;
  setor: number | null;
  pessoal: boolean;
  total_documentos: number | null;
  atualizado_em: string;
}

export interface DocumentoDetalhe extends DocumentoLista {
  descricao: string;
  palavras_chave: string[];
  nome_arquivo_original: string;
  tamanho_bytes: number;
  hash_sha256: string;
  total_paginas: number | null;
  disponibilizado_em: string | null;
  criado_em: string;
  colecoes: Colecao[];
  indexacao_semantica: boolean;
  mensagem_erro: string;
}

export interface Trecho {
  id: number;
  ordem: number;
  pagina: number | null;
  secao: string;
  texto: string;
}

export interface Fonte {
  numero?: number;
  documento_id: number;
  trecho_id?: number;
  titulo: string;
  tipo_arquivo: string;
  pagina: number | null;
  secao: string;
  trecho: string;
  versao: number;
  atualizado_em: string;
  pode_abrir: boolean;
  citada: boolean;
  similaridade?: number;
}

export interface SetorSugerido {
  id: number;
  sigla: string;
  nome: string;
  descricao?: string;
  canal_contato: string | null;
  horario_atendimento: string;
  orientacao_acesso: string;
  pontuacao?: number;
}

export type Origem = "deterministico" | "rag" | "extrativo" | "sem_fontes" | "desambiguacao" | "erro";
export type Confianca = "verificada" | "fundamentada" | "cautela" | "";

export interface Mensagem {
  id: number;
  papel: "usuario" | "assistente";
  conteudo: string;
  origem: Origem | "";
  confianca: Confianca;
  etapas: { titulo: string; descricao: string }[];
  setor: SetorSugerido | null;
  setores_sugeridos: SetorSugerido[];
  sugestoes: string[];
  fontes: Fonte[];
  rastro: Record<string, unknown>;
  interrompida: boolean;
  duracao_ms: number | null;
  criada_em: string;
}

export interface Conversa {
  id: number;
  titulo: string;
  documento_contexto: number | null;
  documento_contexto_titulo: string | null;
  arquivada: boolean;
  criada_em: string;
  ultima_mensagem_em: string;
}

export interface ResultadoBusca {
  documento: DocumentoLista;
  pontuacao: number;
  trechos: { id: number; pagina: number | null; secao: string; destaque: string; origens: string[]; similaridade: number | null }[];
}

export interface RespostaBusca {
  consulta: string;
  modo: string;
  total_documentos: number;
  resultados: ResultadoBusca[];
  facetas: {
    tipo?: { tipo_arquivo: string; total: number }[];
    setor?: { setor_responsavel_id: number; setor_responsavel__sigla: string; total: number }[];
    categoria?: { categoria_id: number; categoria__nome: string; total: number }[];
  };
  semantica_disponivel: boolean | null;
}

export interface EventoAuditoria {
  id: number;
  ocorrido_em: string;
  tipo: string;
  tipo_rotulo: string;
  resultado: "SUCESSO" | "FALHA" | "NEGADO";
  usuario_login: string;
  setor_sigla: string;
  objeto_tipo: string;
  objeto_id: string;
  objeto_descricao: string;
  ip: string | null;
  detalhes: Record<string, unknown>;
  hash: string;
}

export interface Notificacao {
  id: number;
  tipo: string;
  titulo: string;
  texto: string;
  link: string;
  lida: boolean;
  criada_em: string;
}

export interface Perfil {
  id: number;
  codigo: string;
  nome: string;
  descricao: string;
  funcoes: string[];
}

export interface UsuarioAdmin {
  id: number;
  username: string;
  nome_exibicao: string;
  first_name: string;
  last_name: string;
  email: string;
  matricula: string;
  setor: number | null;
  setor_nome: string | null;
  perfis: number[];
  is_active: boolean;
  last_login: string | null;
  date_joined: string;
}

export interface Autorizacao {
  id: number;
  documento: number;
  usuario: number | null;
  setor: number | null;
  perfil: number | null;
  destinatario: string;
  acoes: Acao[];
  acoes_efetivas: Acao[];
  valido_ate: string | null;
  motivo: string;
  concedido_por_nome: string | null;
  criado_em: string;
}

export interface Regra {
  id: number;
  codigo: string;
  titulo: string;
  tipo: "procedimento" | "faq" | "roteamento" | "orientacao_acesso";
  frases_exemplo: string[];
  palavras_chave: string[];
  termos_obrigatorios: string[];
  termos_excludentes: string[];
  padroes_regex: string[];
  resposta: string;
  etapas: { titulo: string; descricao: string }[];
  setor_responsavel: number | null;
  setor_responsavel_sigla: string | null;
  setores_alvo: number[];
  perfis_alvo: number[];
  prioridade: number;
  status: "rascunho" | "publicada" | "arquivada";
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
  versao: number;
  publicada_em: string | null;
  fontes: { id?: number; documento: number; documento_titulo?: string; pagina: number | null; secao: string; trecho_citado: string }[];
  atualizado_em: string;
}

export interface ItemFila {
  id: number;
  titulo: string;
  arquivo: string;
  tamanho_bytes: number;
  status: string;
  mensagem_erro: string;
  criado_em: string;
  etapas: { etapa: string; situacao: "ok" | "aviso" | "erro"; mensagem: string; ocorrido_em: string }[];
}
