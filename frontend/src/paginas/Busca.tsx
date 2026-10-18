import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Drawer,
  FormControlLabel,
  InputBase,
  Paper,
  Skeleton,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { Bot, ExternalLink, Filter, Search } from "lucide-react";

import { api, parametros } from "../api/cliente";
import type { RespostaBusca } from "../api/tipos";
import { Cabecalho, ChipClassificacao, Destaque, EstadoVazio, Erro, IconeArquivo, Pagina } from "../componentes/comuns";
import { cores, sombras } from "../tema";
import { data } from "../util/formatos";

const MODOS = [
  { valor: "hibrida", rotulo: "Tudo" },
  { valor: "texto", rotulo: "Palavras exatas" },
  { valor: "semantica", rotulo: "Por significado" },
  { valor: "nome", rotulo: "Nome do documento" },
];

export default function Busca() {
  const [params, setParams] = useSearchParams();
  const navegar = useNavigate();
  const [termo, setTermo] = useState(params.get("q") ?? "");
  const [filtrosAbertos, setFiltrosAbertos] = useState(false);
  const telaLarga = useMediaQuery("(min-width:1024px)");

  useEffect(() => setTermo(params.get("q") ?? ""), [params]);

  const consulta = {
    q: params.get("q"),
    modo: params.get("modo") ?? "hibrida",
    tipo: params.get("tipo"),
    setor: params.get("setor"),
    categoria: params.get("categoria"),
    palavra_chave: params.get("palavra_chave"),
    de: params.get("de"),
    ate: params.get("ate"),
  };

  const busca = useQuery({
    queryKey: ["busca", consulta],
    queryFn: () => api<RespostaBusca>(`/busca/${parametros(consulta)}`),
    enabled: !!consulta.q,
    placeholderData: keepPreviousData,
  });

  function mudar(chave: string, valor: string | null) {
    const novo = new URLSearchParams(params);
    if (valor) novo.set(chave, valor);
    else novo.delete(chave);
    setParams(novo);
  }

  function alternarLista(chave: string, valor: string) {
    const atual = (params.get(chave) ?? "").split(",").filter(Boolean);
    const novo = atual.includes(valor) ? atual.filter((v) => v !== valor) : [...atual, valor];
    mudar(chave, novo.join(",") || null);
  }

  function enviar(e: FormEvent) {
    e.preventDefault();
    mudar("q", termo.trim() || null);
  }

  const facetas = busca.data?.facetas;
  const marcado = (chave: string, v: string) => (params.get(chave) ?? "").split(",").includes(v);

  const painelFiltros = (
    <Box sx={{ width: { xs: 300, lg: "auto" }, p: { xs: 2.5, lg: 0 } }}>
      <Typography variant="h4" component="h2" sx={{ mb: 1 }}>Filtros</Typography>
      {facetas?.tipo?.length ? (
        <GrupoFiltro titulo="Tipo de arquivo">
          {facetas.tipo.map((f) => (
            <FormControlLabel key={f.tipo_arquivo} control={<Checkbox size="small" checked={marcado("tipo", f.tipo_arquivo)} onChange={() => alternarLista("tipo", f.tipo_arquivo)} />} label={`${f.tipo_arquivo.toUpperCase()} (${f.total})`} />
          ))}
        </GrupoFiltro>
      ) : null}
      {facetas?.setor?.length ? (
        <GrupoFiltro titulo="Setor responsável">
          {facetas.setor.map((f) => (
            <FormControlLabel key={f.setor_responsavel_id} control={<Checkbox size="small" checked={marcado("setor", String(f.setor_responsavel_id))} onChange={() => alternarLista("setor", String(f.setor_responsavel_id))} />} label={`${f.setor_responsavel__sigla} (${f.total})`} />
          ))}
        </GrupoFiltro>
      ) : null}
      {facetas?.categoria?.length ? (
        <GrupoFiltro titulo="Categoria">
          {facetas.categoria.map((f) => (
            <FormControlLabel key={f.categoria_id} control={<Checkbox size="small" checked={marcado("categoria", String(f.categoria_id))} onChange={() => alternarLista("categoria", String(f.categoria_id))} />} label={`${f.categoria__nome} (${f.total})`} />
          ))}
        </GrupoFiltro>
      ) : null}
      <GrupoFiltro titulo="Período do documento">
        <Box sx={{ display: "grid", gap: 1, mt: 0.5 }}>
          <TextField size="small" type="date" label="De" InputLabelProps={{ shrink: true }} value={params.get("de") ?? ""} onChange={(e) => mudar("de", e.target.value || null)} />
          <TextField size="small" type="date" label="Até" InputLabelProps={{ shrink: true }} value={params.get("ate") ?? ""} onChange={(e) => mudar("ate", e.target.value || null)} />
        </Box>
      </GrupoFiltro>
      <GrupoFiltro titulo="Palavra-chave">
        <TextField size="small" fullWidth placeholder="Ex.: férias" defaultValue={params.get("palavra_chave") ?? ""} onBlur={(e) => mudar("palavra_chave", e.target.value.trim() || null)} />
      </GrupoFiltro>
      <Typography variant="caption" component="p" sx={{ mt: 2 }}>
        Os filtros consideram apenas documentos autorizados para o seu perfil.
      </Typography>
    </Box>
  );

  return (
    <Pagina larga>
      <Cabecalho titulo="Busca inteligente" descricao="Pesquise ao mesmo tempo nos nomes, no conteúdo e no significado dos documentos." />

      <Box component="form" role="search" onSubmit={enviar} sx={{ display: "flex", gap: 1, alignItems: "center", p: 1, pl: 2, mb: 1.5, bgcolor: cores.superficie, border: `1px solid ${cores.bordaForte}`, borderRadius: 3, boxShadow: sombras.n2, "&:focus-within": { borderColor: cores.primaria } }}>
        <Search size={20} color={cores.textoSecundario} aria-hidden />
        <InputBase value={termo} onChange={(e) => setTermo(e.target.value)} placeholder="O que você procura?" sx={{ flex: 1, fontSize: 16, minHeight: 44 }} inputProps={{ "aria-label": "Termos da busca" }} autoFocus />
        <Button type="submit" variant="contained" disabled={!termo.trim()}>Buscar</Button>
      </Box>

      <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap", mb: 3 }}>
        <ToggleButtonGroup size="small" exclusive value={consulta.modo} onChange={(_, v) => v && mudar("modo", v === "hibrida" ? null : v)} aria-label="Modo de busca">
          {MODOS.map((m) => <ToggleButton key={m.valor} value={m.valor} sx={{ textTransform: "none", px: 1.5 }}>{m.rotulo}</ToggleButton>)}
        </ToggleButtonGroup>
        {!telaLarga && <Button startIcon={<Filter size={16} />} onClick={() => setFiltrosAbertos(true)}>Filtros</Button>}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "240px minmax(0, 1fr)" }, gap: 4 }}>
        {telaLarga ? <Box component="aside">{painelFiltros}</Box> : <Drawer open={filtrosAbertos} onClose={() => setFiltrosAbertos(false)} anchor="right">{painelFiltros}</Drawer>}

        <Box>
          {!consulta.q && <EstadoVazio icone={<Search size={32} />} titulo="Digite o que você procura" texto="Exemplos: “prazo para solicitar férias”, “modelo de requerimento”, “quem aprova diárias”." />}
          {busca.isError && <Erro erro={busca.error} />}
          {busca.data?.semantica_disponivel === false && (
            <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>A busca por significado está indisponível no momento. Os resultados consideram apenas palavras e nomes.</Alert>
          )}
          {busca.isLoading && <Skeleton variant="rounded" height={260} />}
          {busca.data && (
            <>
              <Typography variant="body2" sx={{ color: cores.textoSecundario, mb: 1.5 }} role="status">
                {busca.data.total_documentos === 0
                  ? "Nenhum documento autorizado corresponde à pesquisa."
                  : `${busca.data.total_documentos} documento${busca.data.total_documentos > 1 ? "s" : ""} autorizado${busca.data.total_documentos > 1 ? "s" : ""} encontrado${busca.data.total_documentos > 1 ? "s" : ""}`}
              </Typography>
              {busca.data.total_documentos === 0 && (
                <Paper variant="outlined">
                  <EstadoVazio
                    titulo="Sem resultados"
                    texto="Tente termos mais gerais, remova filtros ou pergunte ao assistente qual setor pode ajudar."
                    acao={<Button startIcon={<Bot size={16} />} onClick={() => navegar("/assistente", { state: { pergunta: consulta.q, nova: Date.now() } })}>Perguntar ao assistente</Button>}
                  />
                </Paper>
              )}
              <Box sx={{ display: "grid", gap: 1.5, opacity: busca.isFetching ? 0.7 : 1 }}>
                {busca.data.resultados.map((r) => (
                  <Paper key={r.documento.id} variant="outlined" component="article" sx={{ p: 2.25 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                      <IconeArquivo tipo={r.documento.tipo_arquivo} />
                      <Typography component="h3" sx={{ fontWeight: 600, fontSize: 16, flex: 1, color: cores.titulo }}>{r.documento.titulo}</Typography>
                      <ChipClassificacao valor={r.documento.classificacao} />
                    </Box>
                    <Typography variant="caption" component="p" sx={{ mb: 1.25 }}>
                      {r.documento.setor_responsavel.nome}, {r.documento.categoria ?? "sem categoria"}, atualizado em {data(r.documento.atualizado_em)}
                    </Typography>
                    {r.trechos.map((t) => (
                      <Box key={t.id} sx={{ pl: 1.5, borderLeft: `3px solid ${cores.primariaBorda}`, mb: 1 }}>
                        <Typography variant="body2" sx={{ color: cores.texto }}>
                          <Destaque texto={t.destaque} />
                        </Typography>
                        <Typography variant="caption">
                          {[t.pagina ? `Página ${t.pagina}` : null, t.secao || null].filter(Boolean).join(", ") || "Trecho"}
                          {t.origens.includes("semantica") && !t.origens.includes("texto") ? ", encontrado pelo significado" : ""}
                        </Typography>
                      </Box>
                    ))}
                    <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
                      <Button size="small" variant="outlined" startIcon={<ExternalLink size={14} />} onClick={() => navegar(`/documentos/${r.documento.id}${r.trechos[0]?.pagina ? `?pagina=${r.trechos[0].pagina}` : ""}`)}>Abrir documento</Button>
                      <Button size="small" startIcon={<Bot size={14} />} onClick={() => navegar("/assistente", { state: { documentoId: r.documento.id, documentoTitulo: r.documento.titulo, pergunta: consulta.q, nova: Date.now() } })}>Perguntar à IA sobre este resultado</Button>
                    </Box>
                  </Paper>
                ))}
              </Box>
            </>
          )}
        </Box>
      </Box>
    </Pagina>
  );
}

function GrupoFiltro({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <Box component="fieldset" sx={{ border: 0, p: 0, m: 0, mt: 2, display: "grid" }}>
      <Typography component="legend" sx={{ fontSize: 13, fontWeight: 600, color: cores.textoSecundario, mb: 0.5 }}>{titulo}</Typography>
      {children}
    </Box>
  );
}
