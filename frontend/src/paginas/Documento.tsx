import { useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Skeleton,
  Snackbar,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  ArrowLeft,
  Bot,
  ChevronLeft,
  ChevronRight,
  ClipboardCopy,
  Download,
  FileUp,
  ListTree,
  Search,
  Share2,
  Sparkles,
  Star,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { api } from "../api/cliente";
import type { DocumentoDetalhe, Paginado, SetorResumo, Trecho } from "../api/tipos";
import { ChipClassificacao, Erro, IconeArquivo, Rotulo, Valor } from "../componentes/comuns";
import { cores, fonteMono } from "../tema";
import { data, dataHora, rotuloAcao, tamanho } from "../util/formatos";

export default function Documento() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const navegar = useNavigate();
  const queryClient = useQueryClient();
  const [modo, setModo] = useState<"original" | "texto">("original");
  const [zoom, setZoom] = useState(100);
  const [busca, setBusca] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [compartilhar, setCompartilhar] = useState(false);
  const buscaRef = useRef<HTMLInputElement>(null);
  const versaoRef = useRef<HTMLInputElement>(null);
  const pagina = Number(params.get("pagina") ?? "1");

  const doc = useQuery({ queryKey: ["documento", id], queryFn: () => api<DocumentoDetalhe>(`/documentos/${id}/`) });
  const trechos = useQuery({
    queryKey: ["documento", id, "conteudo"],
    queryFn: () => api<Trecho[]>(`/documentos/${id}/conteudo/`),
    enabled: !!doc.data,
  });

  const favorito = useMutation({
    mutationFn: (valor: boolean) => api(`/documentos/${id}/favorito/`, { method: valor ? "POST" : "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documento", id] }),
  });

  const novaVersao = useMutation({
    mutationFn: (arquivo: File) => {
      const corpo = new FormData();
      corpo.append("arquivo", arquivo);
      return api<{ id?: number; erro?: string }>(`/ingestao/documentos/${id}/nova-versao/`, { method: "POST", body: corpo });
    },
    onSuccess: (r) => setAviso(r.erro ?? "Nova versão enviada. Ela substituirá esta quando o processamento terminar."),
    onError: (e: Error) => setAviso(e.message),
  });

  const filtrados = useMemo(() => {
    const lista = trechos.data ?? [];
    if (!busca.trim()) return lista;
    const t = busca.trim().toLowerCase();
    return lista.filter((x) => x.texto.toLowerCase().includes(t));
  }, [trechos.data, busca]);

  if (doc.isError) {
    return (
      <Box sx={{ p: 4, maxWidth: 720, mx: "auto" }}>
        <Erro erro={doc.error} />
        <Button startIcon={<ArrowLeft size={16} />} onClick={() => navegar("/repositorio")}>
          Voltar ao repositório
        </Button>
      </Box>
    );
  }
  if (!doc.data) return <Skeleton variant="rectangular" height="80vh" sx={{ m: 4 }} />;

  const d = doc.data;
  const pode = (a: string) => d.acoes_permitidas.includes(a as never);
  const pdf = d.tipo_arquivo === "pdf";
  const totalPaginas = d.total_paginas ?? 1;
  const irPara = (p: number) => {
    const novo = new URLSearchParams(params);
    novo.set("pagina", String(Math.min(Math.max(1, p), totalPaginas)));
    setParams(novo, { replace: true });
  };

  async function copiarReferencia() {
    const r = await api<{ referencia: string }>(`/documentos/${id}/referencia/`);
    await navigator.clipboard?.writeText(r.referencia);
    setAviso("Referência copiada.");
  }

  const perguntar = (pergunta?: string) =>
    navegar("/assistente", { state: { documentoId: d.id, documentoTitulo: d.titulo, pergunta, nova: Date.now() } });

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 360px" }, minHeight: "100dvh" }}>
      {/* Coluna principal: visualizador */}
      <Box sx={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", px: { xs: 1.5, md: 3 }, py: 1.25, borderBottom: `1px solid ${cores.borda}`, bgcolor: cores.superficie }}>
          <IconButton onClick={() => navegar(-1)} aria-label="Voltar">
            <ArrowLeft size={18} />
          </IconButton>
          <IconeArquivo tipo={d.tipo_arquivo} />
          <Typography variant="h4" component="h1" noWrap sx={{ flex: 1, minWidth: 120 }}>
            {d.titulo}
          </Typography>
          {pdf && (
            <ToggleButtonGroup size="small" exclusive value={modo} onChange={(_, v) => v && setModo(v)} aria-label="Modo de visualização">
              <ToggleButton value="original">Original</ToggleButton>
              <ToggleButton value="texto">Texto</ToggleButton>
            </ToggleButtonGroup>
          )}
          {(modo === "texto" || !pdf) && (
            <>
              <Tooltip title="Diminuir texto"><IconButton size="small" onClick={() => setZoom((z) => Math.max(80, z - 10))} aria-label="Diminuir zoom"><ZoomOut size={18} /></IconButton></Tooltip>
              <Typography variant="caption" sx={{ minWidth: 40, textAlign: "center" }}>{zoom}%</Typography>
              <Tooltip title="Aumentar texto"><IconButton size="small" onClick={() => setZoom((z) => Math.min(160, z + 10))} aria-label="Aumentar zoom"><ZoomIn size={18} /></IconButton></Tooltip>
            </>
          )}
          {pdf && modo === "original" && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <IconButton size="small" onClick={() => irPara(pagina - 1)} disabled={pagina <= 1} aria-label="Página anterior"><ChevronLeft size={18} /></IconButton>
              <Typography variant="body2">Página {pagina} de {totalPaginas}</Typography>
              <IconButton size="small" onClick={() => irPara(pagina + 1)} disabled={pagina >= totalPaginas} aria-label="Próxima página"><ChevronRight size={18} /></IconButton>
            </Box>
          )}
        </Box>

        {pdf && modo === "original" ? (
          <Box
            component="iframe"
            key={pagina}
            title={`Documento ${d.titulo}`}
            src={`/api/v1/documentos/${d.id}/arquivo/#page=${pagina}`}
            sx={{ flex: 1, width: "100%", minHeight: { xs: "70vh", lg: "calc(100dvh - 60px)" }, border: 0, bgcolor: "#E2E8F0" }}
          />
        ) : (
          <Box sx={{ flex: 1, px: { xs: 2, md: 4 }, py: 3, bgcolor: "#EEF2F6" }}>
            <TextField
              inputRef={buscaRef}
              size="small"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Pesquisar neste documento"
              InputProps={{ startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment> }}
              sx={{ mb: 2, maxWidth: 420, width: "100%" }}
              inputProps={{ "aria-label": "Pesquisar no documento" }}
            />
            {busca && <Typography variant="caption" component="p" sx={{ mb: 1 }}>{filtrados.length} trecho(s) encontrado(s)</Typography>}
            <Paper variant="outlined" sx={{ maxWidth: 820, mx: "auto", p: { xs: 2.5, md: 5 }, fontSize: `${(15 * zoom) / 100}px` }}>
              {trechos.isLoading && <Skeleton height={300} />}
              {filtrados.map((t, i) => (
                <Box key={t.id} id={`trecho-${t.id}`} sx={{ mb: 2.5 }}>
                  {(t.pagina || t.secao) && (i === 0 || filtrados[i - 1].secao !== t.secao || filtrados[i - 1].pagina !== t.pagina) && (
                    <Typography sx={{ fontSize: 12, color: cores.textoSecundario, fontWeight: 600, mb: 0.5 }}>
                      {[t.pagina ? `Página ${t.pagina}` : null, t.secao || null].filter(Boolean).join(", ")}
                    </Typography>
                  )}
                  <Typography component="div" sx={{ whiteSpace: "pre-wrap", fontSize: "inherit", lineHeight: 1.7 }}>
                    <TextoComBusca texto={t.texto} termo={busca} />
                  </Typography>
                </Box>
              ))}
            </Paper>
          </Box>
        )}
      </Box>

      {/* Painel lateral */}
      <Box component="aside" aria-label="Informações do documento" sx={{ borderLeft: { lg: `1px solid ${cores.borda}` }, bgcolor: cores.superficie, p: 2.5, position: { lg: "sticky" }, top: 0, height: { lg: "100dvh" }, overflowY: "auto" }}>
        <Box sx={{ display: "grid", gap: 1 }}>
          <Button variant="contained" startIcon={<Bot size={16} />} onClick={() => perguntar()}>
            Perguntar à IA sobre este documento
          </Button>
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
            <Button variant="outlined" startIcon={<Sparkles size={16} />} onClick={() => perguntar("Resuma este documento.")}>Resumir</Button>
            <Button
              variant="outlined"
              startIcon={<ListTree size={16} />}
              onClick={() => {
                setModo("texto");
                setTimeout(() => buscaRef.current?.focus(), 50);
              }}
            >
              Buscar trechos
            </Button>
          </Box>
          <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
            <Tooltip title={d.favorito ? "Remover dos favoritos" : "Adicionar aos favoritos"}>
              <IconButton onClick={() => favorito.mutate(!d.favorito)} aria-pressed={d.favorito} aria-label="Favorito">
                <Star size={18} fill={d.favorito ? "#F59E0B" : "none"} color={d.favorito ? "#F59E0B" : "currentColor"} />
              </IconButton>
            </Tooltip>
            <Tooltip title="Copiar referência">
              <IconButton onClick={copiarReferencia} aria-label="Copiar referência"><ClipboardCopy size={18} /></IconButton>
            </Tooltip>
            {pode("baixar") && (
              <Tooltip title="Baixar">
                <IconButton component="a" href={`/api/v1/documentos/${d.id}/arquivo/?download=1`} aria-label="Baixar"><Download size={18} /></IconButton>
              </Tooltip>
            )}
            {pode("compartilhar") && (
              <Tooltip title="Compartilhar">
                <IconButton onClick={() => setCompartilhar(true)} aria-label="Compartilhar"><Share2 size={18} /></IconButton>
              </Tooltip>
            )}
            {pode("editar") && (
              <Tooltip title="Enviar nova versão">
                <IconButton onClick={() => versaoRef.current?.click()} aria-label="Enviar nova versão"><FileUp size={18} /></IconButton>
              </Tooltip>
            )}
            <input ref={versaoRef} type="file" hidden accept=".pdf,.docx,.txt,.md,.html,.htm" onChange={(e) => e.target.files?.[0] && novaVersao.mutate(e.target.files[0])} />
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />
        {d.status !== "disponivel" && <Alert severity={d.status === "falha" ? "error" : "info"} sx={{ mb: 1 }}>{d.mensagem_erro || "Documento em processamento."}</Alert>}
        <Box component="dl" sx={{ m: 0 }}>
          <Rotulo>Nome completo</Rotulo>
          <Valor>{d.titulo}</Valor>
          {d.descricao && (<><Rotulo>Descrição</Rotulo><Valor>{d.descricao}</Valor></>)}
          <Rotulo>Tipo do arquivo</Rotulo>
          <Valor>{d.tipo_arquivo.toUpperCase()}, {tamanho(d.tamanho_bytes)}{d.total_paginas ? `, ${d.total_paginas} página(s)` : ""}</Valor>
          <Rotulo>Setor responsável</Rotulo>
          <Valor>{d.setor_responsavel.nome} ({d.setor_responsavel.sigla})</Valor>
          <Rotulo>Categoria documental</Rotulo>
          <Valor>{d.categoria ?? "—"}</Valor>
          {d.numero_referencia && (<><Rotulo>Referência</Rotulo><Valor>{d.numero_referencia}</Valor></>)}
          <Rotulo>Data do documento</Rotulo>
          <Valor>{data(d.data_documento)}</Valor>
          <Rotulo>Publicação no repositório</Rotulo>
          <Valor>{dataHora(d.disponibilizado_em)}</Valor>
          <Rotulo>Última atualização</Rotulo>
          <Valor>{dataHora(d.atualizado_em)}</Valor>
          <Rotulo>Versão</Rotulo>
          <Valor>{d.versao}</Valor>
          {d.responsavel && (<><Rotulo>Responsável pela manutenção</Rotulo><Valor>{d.responsavel}</Valor></>)}
          {d.classificacao && (<><Rotulo>Classificação de acesso</Rotulo><Box component="dd" sx={{ m: 0, mt: 0.5 }}><ChipClassificacao valor={d.classificacao} /></Box></>)}
          {d.palavras_chave.length > 0 && (
            <>
              <Rotulo>Palavras-chave</Rotulo>
              <Box component="dd" sx={{ m: 0, mt: 0.5, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                {d.palavras_chave.map((p) => <Chip key={p} label={p} size="small" variant="outlined" />)}
              </Box>
            </>
          )}
          <Rotulo>Suas permissões</Rotulo>
          <Valor>{d.acoes_permitidas.map((a) => rotuloAcao[a]).join(", ")}</Valor>
          <Rotulo>Integridade (SHA-256)</Rotulo>
          <Valor mono>
            <Box component="span" sx={{ fontFamily: fonteMono, fontSize: 12 }}>{d.hash_sha256.slice(0, 16)}…</Box>
          </Valor>
          {!d.indexacao_semantica && d.status === "disponivel" && (
            <Alert severity="warning" variant="outlined" sx={{ mt: 2 }}>Disponível apenas para busca textual até a indexação semântica ser concluída.</Alert>
          )}
        </Box>
      </Box>

      <DialogoCompartilhar aberto={compartilhar} aoFechar={() => setCompartilhar(false)} documentoId={d.id} acoes={d.acoes_permitidas} aoConcluir={(m) => setAviso(m)} />
      <Snackbar open={!!aviso} autoHideDuration={4000} onClose={() => setAviso(null)} message={aviso} />
    </Box>
  );
}

function TextoComBusca({ texto, termo }: { texto: string; termo: string }) {
  if (!termo.trim()) return <>{texto}</>;
  const escapado = termo.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const partes = texto.split(new RegExp(`(${escapado})`, "gi"));
  return (
    <>
      {partes.map((p, i) =>
        p.toLowerCase() === termo.trim().toLowerCase() ? (
          <Box component="mark" key={i} sx={{ bgcolor: "#FEF3C7", color: "inherit", borderRadius: 0.5 }}>{p}</Box>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

function DialogoCompartilhar({
  aberto,
  aoFechar,
  documentoId,
  acoes,
  aoConcluir,
}: {
  aberto: boolean;
  aoFechar: () => void;
  documentoId: number;
  acoes: string[];
  aoConcluir: (m: string) => void;
}) {
  const [tipo, setTipo] = useState<"setor" | "usuario">("setor");
  const [destino, setDestino] = useState("");
  const [acao, setAcao] = useState("visualizar");
  const [validade, setValidade] = useState("");
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState("");
  const setores = useQuery({ queryKey: ["setores", "todos"], queryFn: () => api<Paginado<SetorResumo>>("/setores/?tamanho=100"), enabled: aberto });

  async function salvar() {
    setErro("");
    try {
      await api(`/documentos/${documentoId}/compartilhar/`, {
        method: "POST",
        json: { [tipo]: Number(destino), acoes: [acao], valido_ate: validade ? `${validade}T23:59:59` : null, motivo },
      });
      aoConcluir("Compartilhamento registrado.");
      aoFechar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  return (
    <Dialog open={aberto} onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>Compartilhar documento</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
        {erro && <Alert severity="error">{erro}</Alert>}
        <ToggleButtonGroup exclusive size="small" value={tipo} onChange={(_, v) => v && setTipo(v)}>
          <ToggleButton value="setor">Com um setor</ToggleButton>
          <ToggleButton value="usuario">Com um servidor</ToggleButton>
        </ToggleButtonGroup>
        {tipo === "setor" ? (
          <TextField select label="Setor" value={destino} onChange={(e) => setDestino(e.target.value)}>
            {(setores.data?.results ?? []).map((s) => <MenuItem key={s.id} value={String(s.id)}>{s.sigla} — {s.nome}</MenuItem>)}
          </TextField>
        ) : (
          <TextField label="Código do usuário" value={destino} onChange={(e) => setDestino(e.target.value.replace(/\D/g, ""))} helperText="Identificador interno do servidor." />
        )}
        <TextField select label="Permissão" value={acao} onChange={(e) => setAcao(e.target.value)}>
          {["visualizar", "baixar"].filter((a) => acoes.includes(a)).map((a) => <MenuItem key={a} value={a}>{rotuloAcao[a]}</MenuItem>)}
        </TextField>
        <TextField type="date" label="Válido até" InputLabelProps={{ shrink: true }} value={validade} onChange={(e) => setValidade(e.target.value)} />
        <TextField label="Justificativa" value={motivo} onChange={(e) => setMotivo(e.target.value)} multiline minRows={2} />
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button variant="contained" onClick={salvar} disabled={!destino}>Compartilhar</Button>
      </DialogActions>
    </Dialog>
  );
}
