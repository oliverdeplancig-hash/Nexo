import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Alert, Box, Chip, Drawer, IconButton, Paper, Typography, useMediaQuery } from "@mui/material";
import { BadgeCheck, FileText, FileType2, Globe2, Lock, ShieldAlert, Sparkles, X } from "lucide-react";

import type { Confianca } from "../api/tipos";
import { cores, fonteMono, medidas } from "../tema";
import { rotuloClassificacao } from "../util/formatos";

export function Pagina({ children, larga = false }: { children: ReactNode; larga?: boolean }) {
  return <Box sx={{ maxWidth: larga ? 1280 : 1080, mx: "auto", px: { xs: 2, md: 4 }, py: { xs: 2.5, md: 4 } }}>{children}</Box>;
}

export function Cabecalho({ titulo, descricao, acoes }: { titulo: string; descricao?: string; acoes?: ReactNode }) {
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, alignItems: "flex-end", justifyContent: "space-between", mb: 3 }}>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="h1" sx={{ fontSize: { xs: 24, md: 28 }, lineHeight: { xs: "32px", md: "36px" } }}>
          {titulo}
        </Typography>
        {descricao && (
          <Typography sx={{ color: cores.textoSecundario, mt: 0.5, maxWidth: "68ch" }} variant="body2">
            {descricao}
          </Typography>
        )}
      </Box>
      {acoes && <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>{acoes}</Box>}
    </Box>
  );
}

export function EstadoVazio({ icone, titulo, texto, acao }: { icone?: ReactNode; titulo: string; texto?: string; acao?: ReactNode }) {
  return (
    <Box sx={{ textAlign: "center", py: 6, px: 2, color: cores.textoSecundario }}>
      {icone && <Box sx={{ mb: 1.5, display: "inline-flex", color: "#94A3B8" }}>{icone}</Box>}
      <Typography variant="h4" sx={{ mb: 0.5 }}>
        {titulo}
      </Typography>
      {texto && (
        <Typography variant="body2" sx={{ maxWidth: 440, mx: "auto" }}>
          {texto}
        </Typography>
      )}
      {acao && <Box sx={{ mt: 2 }}>{acao}</Box>}
    </Box>
  );
}

export function Erro({ erro }: { erro: unknown }) {
  const msg = erro instanceof Error ? erro.message : "Não foi possível carregar os dados.";
  return (
    <Alert severity="error" variant="outlined" sx={{ my: 2 }}>
      {msg}
    </Alert>
  );
}

/** Markdown seguro: HTML bruto não é renderizado (react-markdown ignora por padrão). */
export function Markdown({ texto }: { texto: string }) {
  return (
    <Box
      sx={{
        maxWidth: "68ch",
        color: cores.texto,
        fontSize: 15,
        lineHeight: 1.65,
        "& p": { my: 1.25 },
        "& h1, & h2, & h3, & h4": { fontSize: 16, fontWeight: 600, color: cores.titulo, mt: 2, mb: 0.5 },
        "& ul, & ol": { pl: 3, my: 1 },
        "& li": { my: 0.5 },
        "& table": { borderCollapse: "collapse", my: 1.5, fontSize: 14, width: "100%" },
        "& th, & td": { border: `1px solid ${cores.borda}`, px: 1.25, py: 0.75, textAlign: "left" },
        "& th": { bgcolor: cores.fundo, fontWeight: 600 },
        "& code": { fontFamily: fonteMono, fontSize: 13, bgcolor: cores.bordaSutil, px: 0.5, borderRadius: 0.5 },
        "& blockquote": { borderLeft: `3px solid ${cores.primariaBorda}`, m: 0, pl: 2, color: cores.textoSecundario },
        "& a": { color: cores.primariaHover },
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: ({ href, children }) => <a href={href} rel="noopener noreferrer">{children}</a> }}>
        {realcarCitacoes(texto)}
      </ReactMarkdown>
    </Box>
  );
}

/** Converte [n] em `[n]` para estilizar as citações como código inline. */
function realcarCitacoes(texto: string) {
  return texto.replace(/\[(\d{1,2})\](?!\()/g, "`[$1]`");
}

const SELOS: Record<string, { rotulo: string; icone: ReactNode; c: { texto: string; fundo: string; borda: string } }> = {
  verificada: { rotulo: "Resposta aprovada", icone: <BadgeCheck size={14} />, c: cores.verificado },
  fundamentada: { rotulo: "Com fontes citadas", icone: <Sparkles size={14} />, c: cores.semantico },
  cautela: { rotulo: "Confira com atenção", icone: <ShieldAlert size={14} />, c: cores.cautela },
};

export function SeloConfianca({ confianca }: { confianca: Confianca }) {
  const selo = SELOS[confianca];
  if (!selo) return null;
  return (
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.5,
        px: 1,
        py: 0.25,
        borderRadius: 99,
        fontSize: 12,
        fontWeight: 600,
        color: selo.c.texto,
        bgcolor: selo.c.fundo,
        border: `1px solid ${selo.c.borda}`,
      }}
    >
      {selo.icone}
      {selo.rotulo}
    </Box>
  );
}

export function IconeArquivo({ tipo, tamanho = 18 }: { tipo: string; tamanho?: number }) {
  const cor = tipo === "pdf" ? "#B91C1C" : tipo === "docx" ? "#1D4ED8" : "#475569";
  return (
    <Box component="span" sx={{ display: "inline-flex", color: cor }} aria-hidden>
      {tipo === "pdf" ? <FileType2 size={tamanho} /> : <FileText size={tamanho} />}
    </Box>
  );
}

export function ChipClassificacao({ valor }: { valor: string | null }) {
  if (!valor) return null;
  const restrito = valor !== "geral";
  return (
    <Chip
      size="small"
      variant="outlined"
      icon={restrito ? <Lock size={12} /> : <Globe2 size={12} />}
      label={rotuloClassificacao[valor] ?? valor}
      sx={{
        height: 22,
        fontSize: 12,
        color: restrito ? cores.cautela.texto : cores.verificado.texto,
        borderColor: restrito ? cores.cautela.borda : cores.verificado.borda,
        bgcolor: restrito ? cores.cautela.fundo : cores.verificado.fundo,
        "& .MuiChip-icon": { color: "inherit" },
      }}
    />
  );
}

/** Renderiza os marcadores \u0002…\u0003 da busca como <mark>. Nunca usa HTML do servidor. */
export function Destaque({ texto }: { texto: string }) {
  const partes = texto.split(/(\u0002[^\u0003]*\u0003)/g);
  return (
    <>
      {partes.map((p, i) =>
        p.startsWith("\u0002") ? (
          <Box component="mark" key={i} sx={{ bgcolor: "#FEF3C7", color: "inherit", px: 0.25, borderRadius: 0.5 }}>
            {p.slice(1, -1)}
          </Box>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

export function Cartao({ children, sx, ...resto }: { children: ReactNode; sx?: object; [k: string]: unknown }) {
  return (
    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, ...sx }} {...resto}>
      {children}
    </Paper>
  );
}

export function TituloSecao({ children, acao }: { children: ReactNode; acao?: ReactNode }) {
  return (
    <Box sx={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 2, mb: 1.5 }}>
      <Typography variant="h3" component="h2" sx={{ fontSize: 18 }}>
        {children}
      </Typography>
      {acao}
    </Box>
  );
}

/** Painel contextual: fixo à direita no desktop, gaveta sobreposta em telas menores. */
export function PainelContextual({
  aberto,
  aoFechar,
  titulo,
  subtitulo,
  children,
}: {
  aberto: boolean;
  aoFechar: () => void;
  titulo: string;
  subtitulo?: string;
  children: ReactNode;
}) {
  const fixo = useMediaQuery("(min-width:1280px)");
  const conteudo = (
    <Box sx={{ width: { xs: "100vw", sm: medidas.painel }, maxWidth: "100vw", height: "100%", display: "flex", flexDirection: "column", bgcolor: cores.superficie }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, p: 2.5, borderBottom: `1px solid ${cores.borda}` }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h4" component="h2">
            {titulo}
          </Typography>
          {subtitulo && <Typography variant="caption">{subtitulo}</Typography>}
        </Box>
        <IconButton onClick={aoFechar} aria-label="Fechar painel" size="small">
          <X size={18} />
        </IconButton>
      </Box>
      <Box sx={{ flex: 1, overflowY: "auto", p: 2.5 }}>{children}</Box>
    </Box>
  );
  if (fixo) {
    return aberto ? (
      <Box component="aside" aria-label={titulo} sx={{ width: medidas.painel, flexShrink: 0, borderLeft: `1px solid ${cores.borda}`, position: "sticky", top: 0, height: "100dvh" }}>
        {conteudo}
      </Box>
    ) : null;
  }
  return (
    <Drawer anchor="right" open={aberto} onClose={aoFechar}>
      {conteudo}
    </Drawer>
  );
}

export function Rotulo({ children }: { children: ReactNode }) {
  return (
    <Typography component="dt" sx={{ fontSize: 12, fontWeight: 600, color: cores.textoSecundario, mt: 1.5 }}>
      {children}
    </Typography>
  );
}

export function Valor({ children, mono = false }: { children: ReactNode; mono?: boolean }) {
  return (
    <Typography component="dd" sx={{ m: 0, fontSize: 14, color: cores.texto, fontFamily: mono ? fonteMono : undefined, wordBreak: "break-word" }}>
      {children}
    </Typography>
  );
}
