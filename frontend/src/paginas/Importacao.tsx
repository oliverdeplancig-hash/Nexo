import { useRef, useState, type DragEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  IconButton,
  LinearProgress,
  ListItemText,
  MenuItem,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import { CheckCircle2, CircleAlert, CircleDashed, Loader2, RotateCcw, Upload, X } from "lucide-react";

import { api } from "../api/cliente";
import type { ItemFila, Paginado, Perfil, Setor } from "../api/tipos";
import { Cabecalho, IconeArquivo, Pagina, TituloSecao } from "../componentes/comuns";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";
import { dataHora, tamanho } from "../util/formatos";

const ETAPAS = [
  { chave: "recebido", rotulo: "Arquivo recebido" },
  { chave: "extraindo", rotulo: "Extração de conteúdo" },
  { chave: "metadados", rotulo: "Identificação de metadados" },
  { chave: "indexando", rotulo: "Indexação para pesquisa" },
  { chave: "disponivel", rotulo: "Disponibilização para consulta" },
];
const ACEITOS = ".pdf,.docx,.txt,.md,.html,.htm,.png,.jpg,.jpeg,.tif,.tiff";

interface Envio {
  arquivo: File;
  progresso: number;
  erro?: string;
  aviso?: string;
}

function lerCsrf() {
  return decodeURIComponent(document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] ?? "");
}

export default function Importacao() {
  const { usuario } = useAutenticacao();
  const queryClient = useQueryClient();
  const entrada = useRef<HTMLInputElement>(null);
  const [arquivos, setArquivos] = useState<Envio[]>([]);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [mensagem, setMensagem] = useState<{ tipo: "success" | "error"; texto: string } | null>(null);
  const [f, setF] = useState({
    titulo: "",
    descricao: "",
    categoria: "",
    setor_responsavel: usuario?.setor ? String(usuario.setor.id) : "",
    palavras_chave: "",
    data_documento: "",
    revisar_em: "",
    numero_referencia: "",
    classificacao: "setor",
    permite_download_geral: false,
    setores_autorizados: [] as string[],
    perfis_autorizados: [] as string[],
    autorizados_baixam: false,
  });

  const setores = useQuery({ queryKey: ["setores", "todos"], queryFn: () => api<Paginado<Setor>>("/setores/?tamanho=100") });
  const categorias = useQuery({ queryKey: ["categorias"], queryFn: () => api<{ id: number; nome: string }[]>("/categorias/") });
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Paginado<Perfil>>("/perfis/").catch(() => ({ results: [] as Perfil[] }) as Paginado<Perfil>) });
  const fila = useQuery({
    queryKey: ["fila"],
    queryFn: () => api<ItemFila[]>("/ingestao/fila/"),
    refetchInterval: (q) => (q.state.data?.some((d) => !["disponivel", "falha", "arquivado"].includes(d.status)) ? 3000 : false),
  });

  function adicionar(lista: FileList | null) {
    if (!lista) return;
    const novos = Array.from(lista).map((arquivo) => {
      const ext = `.${arquivo.name.split(".").pop()?.toLowerCase()}`;
      return { arquivo, progresso: 0, erro: ACEITOS.split(",").includes(ext) ? undefined : "Formato não suportado." };
    });
    setArquivos((a) => [...a, ...novos]);
  }

  function aoSoltar(e: DragEvent) {
    e.preventDefault();
    setArrastando(false);
    adicionar(e.dataTransfer.files);
  }

  async function enviar() {
    setEnviando(true);
    setMensagem(null);
    const validos = arquivos.filter((a) => !a.erro);
    for (const envio of validos) {
      const corpo = new FormData();
      corpo.append("arquivos", envio.arquivo);
      Object.entries(f).forEach(([k, v]) => {
        if (Array.isArray(v)) v.forEach((x) => corpo.append(k, x));
        else if (k === "titulo" && validos.length > 1) return;
        else corpo.append(k, String(v));
      });
      // XHR para acompanhar o progresso individual do envio
      await new Promise<void>((resolver) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/v1/ingestao/importar/");
        xhr.withCredentials = true;
        xhr.setRequestHeader("X-CSRFToken", lerCsrf());
        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable) atualizar(envio, { progresso: Math.round((ev.loaded / ev.total) * 100) });
        };
        xhr.onload = () => {
          try {
            const r = JSON.parse(xhr.responseText);
            const item = r.resultados?.[0];
            atualizar(envio, { progresso: 100, erro: item?.erro ?? (xhr.status >= 400 ? r.detail ?? "Falha no envio." : undefined), aviso: item?.aviso });
          } catch {
            atualizar(envio, { progresso: 100, erro: "Resposta inválida do servidor." });
          }
          resolver();
        };
        xhr.onerror = () => {
          atualizar(envio, { erro: "Falha de conexão durante o envio." });
          resolver();
        };
        xhr.send(corpo);
      });
    }
    setEnviando(false);
    setMensagem({ tipo: "success", texto: "Envio concluído. Acompanhe o processamento abaixo — o documento só fica disponível para busca e chat ao final." });
    queryClient.invalidateQueries({ queryKey: ["fila"] });
  }

  function atualizar(envio: Envio, dados: Partial<Envio>) {
    setArquivos((lista) => lista.map((a) => (a === envio ? Object.assign(envio, dados) && { ...envio } : a)));
  }

  const campo = (chave: keyof typeof f, rotulo: string, extra: object = {}) => (
    <TextField label={rotulo} value={f[chave] as string} onChange={(e) => setF({ ...f, [chave]: e.target.value })} fullWidth size="small" {...extra} />
  );

  return (
    <Pagina larga>
      <Cabecalho titulo="Cadastro e importação de documentos" descricao="Envie um ou mais arquivos com os mesmos metadados e permissões. Formatos aceitos: PDF, DOCX, TXT, MD, HTML e imagens digitalizadas (PNG, JPG, TIFF), lidas por OCR." />

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 420px" }, gap: 3 }}>
        <Box sx={{ display: "grid", gap: 2.5, alignContent: "start" }}>
          <Box
            onDragOver={(e) => { e.preventDefault(); setArrastando(true); }}
            onDragLeave={() => setArrastando(false)}
            onDrop={aoSoltar}
            onClick={() => entrada.current?.click()}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && entrada.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Selecionar arquivos"
            sx={{ p: 4, textAlign: "center", borderRadius: 3, cursor: "pointer", border: `2px dashed ${arrastando ? cores.primaria : cores.bordaForte}`, bgcolor: arrastando ? cores.primariaFundo : cores.superficie }}
          >
            <Upload size={28} color={cores.primaria} />
            <Typography sx={{ fontWeight: 600, mt: 1 }}>Arraste os arquivos aqui ou clique para selecionar</Typography>
            <Typography variant="caption">Até 50 MB por arquivo</Typography>
            <input ref={entrada} type="file" multiple hidden accept={ACEITOS} onChange={(e) => { adicionar(e.target.files); e.target.value = ""; }} />
          </Box>

          {arquivos.length > 0 && (
            <Paper variant="outlined" sx={{ p: 0 }}>
              {arquivos.map((a, i) => (
                <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.25, borderTop: i ? `1px solid ${cores.bordaSutil}` : 0 }}>
                  <IconeArquivo tipo={a.arquivo.name.split(".").pop() ?? ""} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography noWrap sx={{ fontSize: 14, fontWeight: 500 }}>{a.arquivo.name}</Typography>
                    <Typography variant="caption" sx={{ color: a.erro ? cores.erro : undefined }}>{a.erro ?? a.aviso ?? tamanho(a.arquivo.size)}</Typography>
                    {a.progresso > 0 && a.progresso < 100 && <LinearProgress variant="determinate" value={a.progresso} sx={{ mt: 0.5 }} />}
                  </Box>
                  {a.progresso === 100 && !a.erro ? <CheckCircle2 size={18} color={cores.verificado.forte} /> : (
                    <IconButton size="small" onClick={() => setArquivos((l) => l.filter((x) => x !== a))} aria-label={`Remover ${a.arquivo.name}`} disabled={enviando}><X size={16} /></IconButton>
                  )}
                </Box>
              ))}
            </Paper>
          )}

          <Paper variant="outlined" sx={{ p: 2.5, display: "grid", gap: 2 }}>
            <TituloSecao>Metadados</TituloSecao>
            {campo("titulo", "Título", { helperText: arquivos.length > 1 ? "Com vários arquivos, o título de cada um vem do nome do arquivo." : "Se vazio, usa o nome do arquivo.", disabled: arquivos.length > 1 })}
            {campo("descricao", "Descrição", { multiline: true, minRows: 2 })}
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2 }}>
              <TextField select size="small" label="Categoria" value={f.categoria} onChange={(e) => setF({ ...f, categoria: e.target.value })}>
                <MenuItem value="">Sem categoria</MenuItem>
                {(categorias.data ?? []).map((c) => <MenuItem key={c.id} value={String(c.id)}>{c.nome}</MenuItem>)}
              </TextField>
              <TextField select size="small" label="Setor responsável" value={f.setor_responsavel} onChange={(e) => setF({ ...f, setor_responsavel: e.target.value })} required>
                {(setores.data?.results ?? []).map((s) => <MenuItem key={s.id} value={String(s.id)}>{s.sigla} — {s.nome}</MenuItem>)}
              </TextField>
              {campo("data_documento", "Data do documento", { type: "date", InputLabelProps: { shrink: true } })}
              {campo("revisar_em", "Próxima revisão", { type: "date", InputLabelProps: { shrink: true }, helperText: "Opcional. Quem mantém o documento é avisado 30 dias antes." })}
              {campo("numero_referencia", "Número ou código de referência", { helperText: "Se vazio, o Nexo tenta identificar no texto." })}
            </Box>
            {campo("palavras_chave", "Palavras-chave", { helperText: "Separe por vírgulas. Se vazio, serão sugeridas automaticamente." })}
          </Paper>
        </Box>

        <Box sx={{ display: "grid", gap: 2.5, alignContent: "start" }}>
          <Paper variant="outlined" sx={{ p: 2.5, display: "grid", gap: 2 }}>
            <TituloSecao>Acesso</TituloSecao>
            <TextField select size="small" label="Classificação de acesso" value={f.classificacao} onChange={(e) => setF({ ...f, classificacao: e.target.value })}>
              <MenuItem value="geral">Geral — todos os servidores</MenuItem>
              <MenuItem value="setor">Restrito ao setor responsável</MenuItem>
              <MenuItem value="restrito">Restrito — somente autorizados</MenuItem>
            </TextField>
            {f.classificacao === "geral" && (
              <FormControlLabel control={<Checkbox checked={f.permite_download_geral} onChange={(e) => setF({ ...f, permite_download_geral: e.target.checked })} />} label="Permitir download a todos" />
            )}
            <TextField
              select
              size="small"
              label="Setores autorizados"
              SelectProps={{ multiple: true, renderValue: (v) => (v as string[]).map((id) => setores.data?.results.find((s) => String(s.id) === id)?.sigla).join(", ") }}
              value={f.setores_autorizados}
              onChange={(e) => setF({ ...f, setores_autorizados: e.target.value as unknown as string[] })}
            >
              {(setores.data?.results ?? []).map((s) => (
                <MenuItem key={s.id} value={String(s.id)}>
                  <Checkbox size="small" checked={f.setores_autorizados.includes(String(s.id))} />
                  <ListItemText primary={`${s.sigla} — ${s.nome}`} />
                </MenuItem>
              ))}
            </TextField>
            {!!perfis.data?.results.length && (
              <TextField
                select
                size="small"
                label="Perfis autorizados"
                SelectProps={{ multiple: true, renderValue: (v) => (v as string[]).map((id) => perfis.data?.results.find((p) => String(p.id) === id)?.nome).join(", ") }}
                value={f.perfis_autorizados}
                onChange={(e) => setF({ ...f, perfis_autorizados: e.target.value as unknown as string[] })}
              >
                {perfis.data.results.map((p) => (
                  <MenuItem key={p.id} value={String(p.id)}>
                    <Checkbox size="small" checked={f.perfis_autorizados.includes(String(p.id))} />
                    <ListItemText primary={p.nome} />
                  </MenuItem>
                ))}
              </TextField>
            )}
            <FormControlLabel control={<Checkbox checked={f.autorizados_baixam} onChange={(e) => setF({ ...f, autorizados_baixam: e.target.checked })} />} label="Autorizados também podem baixar" />
            <Typography variant="caption">Responsável pela manutenção: você ({usuario?.nome}). Pode ser alterado depois na tela do documento.</Typography>
          </Paper>

          {mensagem && <Alert severity={mensagem.tipo}>{mensagem.texto}</Alert>}
          <Button variant="contained" size="large" disabled={enviando || !arquivos.some((a) => !a.erro && a.progresso === 0) || !f.setor_responsavel} onClick={enviar} startIcon={<Upload size={18} />}>
            {enviando ? "Enviando…" : "Enviar para processamento"}
          </Button>
        </Box>
      </Box>

      <Box sx={{ mt: 5 }}>
        <TituloSecao>Status de processamento</TituloSecao>
        <Box sx={{ display: "grid", gap: 1.25 }}>
          {fila.data?.length === 0 && <Typography variant="body2" sx={{ color: cores.textoSecundario }}>Nenhum envio seu ainda.</Typography>}
          {fila.data?.map((d) => <LinhaProcessamento key={d.id} item={d} aoReprocessar={() => api(`/ingestao/documentos/${d.id}/reprocessar/`, { method: "POST" }).then(() => fila.refetch())} />)}
        </Box>
      </Box>
    </Pagina>
  );
}

function LinhaProcessamento({ item, aoReprocessar }: { item: ItemFila; aoReprocessar: () => void }) {
  const concluidas = new Set(item.etapas.filter((e) => e.situacao !== "erro").map((e) => e.etapa));
  const falhou = item.status === "falha";
  const avisos = item.etapas.filter((e) => e.situacao === "aviso");
  const atual = ETAPAS.findIndex((e) => e.chave === item.status);
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <Typography sx={{ fontWeight: 600, fontSize: 14, flex: 1 }}>{item.titulo}</Typography>
        <Typography variant="caption">{dataHora(item.criado_em)}</Typography>
        {falhou && <Button size="small" startIcon={<RotateCcw size={14} />} onClick={aoReprocessar}>Tentar novamente</Button>}
      </Box>
      <Box component="ol" sx={{ listStyle: "none", p: 0, m: 0, mt: 1.25, display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(5, 1fr)" }, gap: 1 }}>
        {ETAPAS.map((e, i) => {
          const feita = concluidas.has(e.chave) || (atual > i && !falhou);
          const emAndamento = !falhou && item.status === e.chave && e.chave !== "disponivel";
          const erroAqui = falhou && !feita && (i === 0 || concluidas.has(ETAPAS[i - 1].chave));
          return (
            <Box component="li" key={e.chave} sx={{ display: "flex", alignItems: "center", gap: 0.75, fontSize: 13, color: feita ? cores.texto : cores.textoSecundario }}>
              {erroAqui ? <CircleAlert size={16} color={cores.erro} /> : feita && !emAndamento ? <CheckCircle2 size={16} color={cores.verificado.forte} /> : emAndamento ? <Loader2 size={16} className="girando" color={cores.primaria} /> : <CircleDashed size={16} />}
              <span>{i + 1}. {e.rotulo}</span>
            </Box>
          );
        })}
      </Box>
      {falhou && <Alert severity="error" sx={{ mt: 1.25 }}>{item.mensagem_erro}</Alert>}
      {avisos.map((a, i) => <Alert key={i} severity="warning" sx={{ mt: 1.25 }}>{a.mensagem}</Alert>)}
    </Paper>
  );
}
