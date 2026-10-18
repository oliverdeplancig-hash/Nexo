import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { FlaskConical, Pencil, Plus, Send, Trash2 } from "lucide-react";

import { api } from "../api/cliente";
import type { DocumentoLista, Paginado, Regra, ResumoLacunas, Setor } from "../api/tipos";
import { Cabecalho, Erro, Markdown, Pagina, TituloSecao } from "../componentes/comuns";
import { cores, fonteMono } from "../tema";
import { dataHora } from "../util/formatos";
import Lacunas from "./Lacunas";

const TIPOS = { procedimento: "Procedimento", faq: "Pergunta frequente", roteamento: "Encaminhamento", orientacao_acesso: "Orientação de acesso" };
const STATUS = { rascunho: "Rascunho", publicada: "Publicada", arquivada: "Arquivada" };

interface Simulacao {
  decisao: "responder" | "desambiguar" | "nao_aplicavel";
  pontuacao: number;
  rastro: { limiar: number; tokens: string[]; motivo: string; candidatos?: { codigo: string; titulo: string; pontuacao: number; criterio: string; exemplo_mais_proximo?: string }[] };
  regra?: { codigo: string; titulo: string };
  resposta?: { conteudo: string; modo: string };
}

export default function Regras() {
  const queryClient = useQueryClient();
  const [edicao, setEdicao] = useState<Partial<Regra> | null>(null);
  const [lacunaEmEdicao, setLacunaEmEdicao] = useState<number | null>(null);
  const [parametros, setParametros] = useSearchParams();
  const aba = parametros.get("aba") === "lacunas" ? "lacunas" : "regras";
  const resumoLacunas = useQuery({ queryKey: ["lacunas", "resumo"], queryFn: () => api<ResumoLacunas>("/lacunas/resumo/?dias=30") });
  const [pergunta, setPergunta] = useState("");
  const regras = useQuery({ queryKey: ["regras"], queryFn: () => api<Paginado<Regra>>("/motor/regras/?tamanho=100") });
  const simular = useMutation({ mutationFn: () => api<Simulacao>("/motor/regras/simular/", { method: "POST", json: { pergunta } }) });
  const publicar = useMutation({
    mutationFn: (id: number) => api(`/motor/regras/${id}/publicar/`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["regras"] }),
  });
  const arquivar = useMutation({
    mutationFn: (id: number) => api(`/motor/regras/${id}/`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["regras"] }),
  });

  return (
    <Pagina larga>
      <Cabecalho
        titulo="Motor de respostas"
        descricao="Respostas aprovadas que o assistente devolve exatamente como cadastradas, sem IA, quando a pergunta corresponde a uma regra publicada."
        acoes={<Button variant="contained" startIcon={<Plus size={16} />} onClick={() => setEdicao({ tipo: "faq", frases_exemplo: [], palavras_chave: [], termos_obrigatorios: [], termos_excludentes: [], padroes_regex: [], etapas: [], fontes: [], prioridade: 0 })}>Nova regra</Button>}
      />

      <Tabs value={aba} onChange={(_, v) => setParametros(v === "lacunas" ? { aba: "lacunas" } : {}, { replace: true })} sx={{ mb: 3, borderBottom: `1px solid ${cores.borda}` }}>
        <Tab value="regras" label="Regras" />
        <Tab
          value="lacunas"
          label={
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              Lacunas do assistente
              {!!resumoLacunas.data?.lacunas_pendentes && (
                <Box
                  component="span"
                  aria-label={`${resumoLacunas.data.lacunas_pendentes} pendentes`}
                  sx={{ minWidth: 22, height: 22, px: 0.75, borderRadius: 99, bgcolor: cores.cautela.fundo, color: cores.cautela.texto, border: `1px solid ${cores.cautela.borda}`, fontSize: 12, fontWeight: 600, display: "grid", placeItems: "center" }}
                >
                  {resumoLacunas.data.lacunas_pendentes > 99 ? "99+" : resumoLacunas.data.lacunas_pendentes}
                </Box>
              )}
            </Box>
          }
        />
      </Tabs>

      {aba === "lacunas" && (
        <Lacunas
          regras={regras.data?.results ?? []}
          aoEditarRegra={(regra, lacunaId) => {
            setLacunaEmEdicao(lacunaId);
            setEdicao(regra);
          }}
        />
      )}

      {aba === "regras" && (
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 400px" }, gap: 3 }}>
        <Box>
          {regras.isError && <Erro erro={regras.error} />}
          <TableContainer component={Paper} variant="outlined">
            <Table size="small" aria-label="Regras">
              <TableHead>
                <TableRow>
                  <TableCell>Código</TableCell>
                  <TableCell>Título</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Setor</TableCell>
                  <TableCell>Situação</TableCell>
                  <TableCell>Versão</TableCell>
                  <TableCell align="right">Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {regras.data?.results.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell sx={{ fontFamily: fonteMono, fontSize: 13 }}>{r.codigo}</TableCell>
                    <TableCell sx={{ fontWeight: 500 }}>
                      {r.titulo}
                      {r.fontes.some((f) => f.documento_vigencia === "revogado") && (
                        <Chip
                          size="small"
                          variant="outlined"
                          label="Fonte revogada: revise"
                          title="Um documento que fundamenta esta regra foi revogado. Atualize a resposta e a fonte."
                          sx={{ ml: 1, height: 20, fontSize: 11, color: cores.erro, borderColor: cores.erro }}
                        />
                      )}
                    </TableCell>
                    <TableCell>{TIPOS[r.tipo]}</TableCell>
                    <TableCell>{r.setor_responsavel_sigla ?? "—"}</TableCell>
                    <TableCell>
                      <Chip size="small" label={STATUS[r.status]} sx={{ bgcolor: r.status === "publicada" ? cores.verificado.fundo : cores.bordaSutil, color: r.status === "publicada" ? cores.verificado.texto : cores.textoSecundario }} />
                    </TableCell>
                    <TableCell>{r.versao ? `v${r.versao}, ${dataHora(r.publicada_em)}` : "—"}</TableCell>
                    <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                      <IconButton size="small" onClick={() => setEdicao(r)} aria-label={`Editar ${r.codigo}`}><Pencil size={16} /></IconButton>
                      {r.status !== "publicada" && (
                        <Button size="small" startIcon={<Send size={14} />} onClick={() => publicar.mutate(r.id)}>Publicar</Button>
                      )}
                      {r.status !== "arquivada" && (
                        <IconButton size="small" onClick={() => arquivar.mutate(r.id)} aria-label={`Arquivar ${r.codigo}`}><Trash2 size={16} /></IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Typography variant="caption" component="p" sx={{ mt: 1.5 }}>
            Editar uma regra publicada a devolve para rascunho; ela só volta a responder depois de publicada novamente. Cada publicação gera uma versão rastreável.
          </Typography>
        </Box>

        <Paper variant="outlined" sx={{ p: 2.5, alignSelf: "start" }}>
          <TituloSecao>Simulador</TituloSecao>
          <Typography variant="body2" sx={{ color: cores.textoSecundario, mb: 1.5 }}>Teste como o motor decide uma pergunta, com a pontuação de cada regra.</Typography>
          <TextField fullWidth size="small" multiline minRows={2} placeholder="Ex.: como solicito minhas férias?" value={pergunta} onChange={(e) => setPergunta(e.target.value)} />
          <Button sx={{ mt: 1 }} variant="outlined" startIcon={<FlaskConical size={16} />} disabled={!pergunta.trim()} onClick={() => simular.mutate()}>Simular</Button>
          {simular.data && (
            <Box sx={{ mt: 2 }}>
              <Alert severity={simular.data.decisao === "responder" ? "success" : simular.data.decisao === "desambiguar" ? "warning" : "info"}>
                {simular.data.decisao === "responder" && `Responde com ${simular.data.regra?.codigo} (pontuação ${simular.data.pontuacao}).`}
                {simular.data.decisao === "desambiguar" && "Regras muito próximas: o assistente pedirá para o servidor escolher."}
                {simular.data.decisao === "nao_aplicavel" && "Nenhuma regra atinge o limiar: a pergunta segue para a busca nos documentos."}
              </Alert>
              <Typography sx={{ fontFamily: fonteMono, fontSize: 12, color: cores.textoSecundario, mt: 1 }}>
                termos: {simular.data.rastro.tokens.join(" ")}; limiar {simular.data.rastro.limiar}
              </Typography>
              {simular.data.rastro.candidatos?.map((c) => (
                <Box key={c.codigo} sx={{ display: "flex", gap: 1, alignItems: "baseline", mt: 0.75 }}>
                  <Typography sx={{ fontFamily: fonteMono, fontSize: 13, minWidth: 64 }}>{c.codigo}</Typography>
                  <Box sx={{ flex: 1, height: 6, bgcolor: cores.bordaSutil, borderRadius: 99, overflow: "hidden" }}>
                    <Box sx={{ width: `${Math.min(100, c.pontuacao * 100)}%`, height: "100%", bgcolor: c.pontuacao >= simular.data!.rastro.limiar ? cores.verificado.forte : "#94A3B8" }} />
                  </Box>
                  <Typography sx={{ fontSize: 13, minWidth: 44, textAlign: "right" }}>{c.pontuacao.toFixed(2).replace(".", ",")}</Typography>
                </Box>
              ))}
              {simular.data.resposta && (
                <Box sx={{ mt: 2, p: 1.5, border: `1px solid ${cores.borda}`, borderRadius: 2 }}>
                  <Markdown texto={simular.data.resposta.conteudo} />
                </Box>
              )}
            </Box>
          )}
        </Paper>
      </Box>

      )}

      {edicao && (
        <EditorRegra
          regra={edicao}
          lacunaId={lacunaEmEdicao}
          aoFechar={() => {
            setEdicao(null);
            setLacunaEmEdicao(null);
          }}
        />
      )}
    </Pagina>
  );
}

const linhas = (v: string) => v.split("\n").map((x) => x.trim()).filter(Boolean);
const virgulas = (v: string) => v.split(",").map((x) => x.trim()).filter(Boolean);

function EditorRegra({ regra, lacunaId, aoFechar }: { regra: Partial<Regra>; lacunaId?: number | null; aoFechar: () => void }) {
  const queryClient = useQueryClient();
  const setores = useQuery({ queryKey: ["setores", "todos"], queryFn: () => api<Paginado<Setor>>("/setores/?tamanho=100") });
  const [termoDoc, setTermoDoc] = useState("");
  const documentos = useQuery({ queryKey: ["documentos", "regra", termoDoc], queryFn: () => api<Paginado<DocumentoLista>>(`/documentos/?q=${encodeURIComponent(termoDoc)}&tamanho=10`) });
  const [f, setF] = useState({
    codigo: regra.codigo ?? "",
    titulo: regra.titulo ?? "",
    tipo: regra.tipo ?? "faq",
    frases_exemplo: (regra.frases_exemplo ?? []).join("\n"),
    palavras_chave: (regra.palavras_chave ?? []).join(", "),
    termos_obrigatorios: (regra.termos_obrigatorios ?? []).join(", "),
    termos_excludentes: (regra.termos_excludentes ?? []).join(", "),
    padroes_regex: (regra.padroes_regex ?? []).join("\n"),
    resposta: regra.resposta ?? "",
    etapas: (regra.etapas ?? []).map((e) => `${e.titulo} | ${e.descricao}`).join("\n"),
    setor_responsavel: regra.setor_responsavel ? String(regra.setor_responsavel) : "",
    prioridade: String(regra.prioridade ?? 0),
    vigencia_inicio: regra.vigencia_inicio ?? "",
    vigencia_fim: regra.vigencia_fim ?? "",
  });
  const [fontes, setFontes] = useState(regra.fontes ?? []);

  const salvar = useMutation({
    mutationFn: () =>
      api<Regra>(regra.id ? `/motor/regras/${regra.id}/` : "/motor/regras/", {
        method: regra.id ? "PATCH" : "POST",
        json: {
          ...f,
          frases_exemplo: linhas(f.frases_exemplo),
          palavras_chave: virgulas(f.palavras_chave),
          termos_obrigatorios: virgulas(f.termos_obrigatorios),
          termos_excludentes: virgulas(f.termos_excludentes),
          padroes_regex: linhas(f.padroes_regex),
          etapas: linhas(f.etapas).map((l) => {
            const [titulo, ...resto] = l.split("|");
            return { titulo: titulo.trim(), descricao: resto.join("|").trim() };
          }),
          setor_responsavel: f.setor_responsavel ? Number(f.setor_responsavel) : null,
          prioridade: Number(f.prioridade) || 0,
          vigencia_inicio: f.vigencia_inicio || null,
          vigencia_fim: f.vigencia_fim || null,
          fontes: fontes.map((x) => ({ documento: x.documento, pagina: x.pagina, secao: x.secao, trecho_citado: x.trecho_citado })),
        },
      }),
    onSuccess: async (salva) => {
      // Veio de uma lacuna do assistente: registra que ela foi tratada com esta regra.
      if (lacunaId) {
        await api(`/lacunas/${lacunaId}/tratar/`, {
          method: "POST",
          json: { regra: salva.id, observacao: regra.id ? "Regra ajustada." : "Regra criada." },
        });
        queryClient.invalidateQueries({ queryKey: ["lacunas"] });
      }
      queryClient.invalidateQueries({ queryKey: ["regras"] });
      aoFechar();
    },
  });

  const campo = (chave: keyof typeof f, rotulo: string, extra: object = {}) => (
    <TextField label={rotulo} value={f[chave]} onChange={(e) => setF({ ...f, [chave]: e.target.value })} fullWidth size="small" {...extra} />
  );

  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="md">
      <DialogTitle>{regra.id ? `Editar ${regra.codigo}` : "Nova regra"}</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
        {lacunaId && (
          <Alert severity="info">
            Ao salvar, a lacuna é marcada como tratada. A regra fica em rascunho e só responde depois de publicada.
          </Alert>
        )}
        {salvar.isError && <Alert severity="error">{(salvar.error as Error).message}</Alert>}
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "140px 1fr 200px" }, gap: 2 }}>
          {campo("codigo", "Código", { placeholder: "MD-010" })}
          {campo("titulo", "Título")}
          <TextField select size="small" label="Tipo" value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value as Regra["tipo"] })}>
            {Object.entries(TIPOS).map(([v, r]) => <MenuItem key={v} value={v}>{r}</MenuItem>)}
          </TextField>
        </Box>
        {campo("frases_exemplo", "Perguntas de exemplo", { multiline: true, minRows: 3, helperText: "Uma por linha. Quanto mais variações reais, melhor o casamento." })}
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" }, gap: 2 }}>
          {campo("palavras_chave", "Palavras-chave", { helperText: "Reforçam a pontuação." })}
          {campo("termos_obrigatorios", "Termos obrigatórios", { helperText: "Todos precisam aparecer." })}
          {campo("termos_excludentes", "Termos excludentes", { helperText: "Se algum aparecer, não responde." })}
        </Box>
        {campo("resposta", "Resposta (Markdown)", { multiline: true, minRows: 4, helperText: "Variáveis: {usuario_nome}, {setor_usuario}, {setor_responsavel}." })}
        {campo("etapas", "Etapas do procedimento", { multiline: true, minRows: 3, helperText: "Uma por linha, no formato: Título | Descrição." })}
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 120px 1fr 1fr" }, gap: 2 }}>
          <TextField select size="small" label="Setor responsável" value={f.setor_responsavel} onChange={(e) => setF({ ...f, setor_responsavel: e.target.value })}>
            <MenuItem value="">Nenhum</MenuItem>
            {(setores.data?.results ?? []).map((s) => <MenuItem key={s.id} value={String(s.id)}>{s.sigla} — {s.nome}</MenuItem>)}
          </TextField>
          {campo("prioridade", "Prioridade", { type: "number" })}
          {campo("vigencia_inicio", "Vigente de", { type: "date", InputLabelProps: { shrink: true } })}
          {campo("vigencia_fim", "Vigente até", { type: "date", InputLabelProps: { shrink: true } })}
        </Box>
        {campo("padroes_regex", "Expressões regulares (avançado)", { multiline: true, minRows: 1, helperText: "Uma por linha. Aplicadas ao texto normalizado (minúsculas, sem acentos)." })}

        <Box>
          <Typography sx={{ fontWeight: 600, fontSize: 14, mb: 1 }}>Fundamento documental</Typography>
          {fontes.map((fonte, i) => (
            <Box key={i} sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 90px 1fr auto" }, gap: 1, mb: 1, alignItems: "center" }}>
              <Typography variant="body2" noWrap>{fonte.documento_titulo ?? `Documento ${fonte.documento}`}</Typography>
              <TextField size="small" label="Página" value={fonte.pagina ?? ""} onChange={(e) => setFontes(fontes.map((x, j) => (j === i ? { ...x, pagina: e.target.value ? Number(e.target.value) : null } : x)))} />
              <TextField size="small" label="Seção ou trecho citado" value={fonte.trecho_citado} onChange={(e) => setFontes(fontes.map((x, j) => (j === i ? { ...x, trecho_citado: e.target.value } : x)))} />
              <IconButton onClick={() => setFontes(fontes.filter((_, j) => j !== i))} aria-label="Remover fonte"><Trash2 size={16} /></IconButton>
            </Box>
          ))}
          <Autocomplete
            size="small"
            options={documentos.data?.results ?? []}
            getOptionLabel={(o) => o.titulo}
            filterOptions={(x) => x}
            onInputChange={(_, v) => setTermoDoc(v)}
            onChange={(_, v) => v && setFontes([...fontes, { documento: v.id, documento_titulo: v.titulo, pagina: null, secao: "", trecho_citado: "" }])}
            value={null}
            renderInput={(p) => <TextField {...p} label="Adicionar documento como fonte" />}
            sx={{ maxWidth: 480 }}
          />
          <Typography variant="caption" component="p" sx={{ mt: 0.75 }}>Quem não puder consultar a fonte recebe apenas o encaminhamento ao setor, sem o conteúdo da resposta.</Typography>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button variant="contained" onClick={() => salvar.mutate()} disabled={!f.codigo || !f.titulo || !f.resposta || salvar.isPending}>Salvar como rascunho</Button>
      </DialogActions>
    </Dialog>
  );
}
