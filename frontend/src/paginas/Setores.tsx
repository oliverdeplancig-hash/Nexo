import { useState, type FormEvent } from "react";
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
  FormControlLabel,
  InputBase,
  Paper,
  Skeleton,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { Clock, MessageCircleQuestion, Pencil, Plus, Search } from "lucide-react";

import { api } from "../api/cliente";
import type { Paginado, Setor } from "../api/tipos";
import { Cabecalho, EstadoVazio, Erro, Pagina } from "../componentes/comuns";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores, sombras } from "../tema";

const EXEMPLOS = [
  "Preciso de informações sobre determinado procedimento.",
  "Quem é responsável por este assunto?",
  "Onde devo solicitar acesso a um documento?",
];

export default function Setores() {
  const { tem } = useAutenticacao();
  const [pergunta, setPergunta] = useState("");
  const [enviada, setEnviada] = useState("");
  const [edicao, setEdicao] = useState<Partial<Setor> | null>(null);

  const todos = useQuery({ queryKey: ["setores", "todos"], queryFn: () => api<Paginado<Setor>>("/setores/?tamanho=100") });
  const sugestoes = useQuery({
    queryKey: ["setores", "ajuda", enviada],
    queryFn: () => api<Setor[]>(`/setores/quem-pode-ajudar/?pergunta=${encodeURIComponent(enviada)}`),
    enabled: !!enviada,
  });

  function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviada(pergunta.trim());
  }

  const lista = enviada ? sugestoes.data : todos.data?.results;
  const carregando = enviada ? sugestoes.isLoading : todos.isLoading;

  return (
    <Pagina larga>
      <Cabecalho
        titulo="Setores e contatos"
        descricao="Descubra qual setor atende cada assunto e como solicitar informações ou acesso."
        acoes={tem("gerir_setores") ? <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => setEdicao({})}>Cadastrar setor</Button> : undefined}
      />

      <Box component="form" role="search" onSubmit={enviar} sx={{ display: "flex", gap: 1, alignItems: "center", p: 1, pl: 2, bgcolor: cores.superficie, border: `1px solid ${cores.bordaForte}`, borderRadius: 3, boxShadow: sombras.n2, "&:focus-within": { borderColor: cores.primaria } }}>
        <MessageCircleQuestion size={20} color={cores.textoSecundario} aria-hidden />
        <InputBase value={pergunta} onChange={(e) => setPergunta(e.target.value)} placeholder="Qual setor pode me ajudar?" sx={{ flex: 1, fontSize: 16, minHeight: 44 }} inputProps={{ "aria-label": "Descreva sua demanda" }} />
        <Button type="submit" variant="contained" startIcon={<Search size={16} />} disabled={!pergunta.trim()}>Encontrar</Button>
      </Box>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1.25, mb: 3 }}>
        {EXEMPLOS.map((e) => (
          <Chip key={e} label={e} variant="outlined" onClick={() => { setPergunta(e); setEnviada(e); }} />
        ))}
        {enviada && <Chip label="Ver todos os setores" color="primary" variant="outlined" onClick={() => { setEnviada(""); setPergunta(""); }} />}
      </Box>

      {(todos.isError || sugestoes.isError) && <Erro erro={todos.error ?? sugestoes.error} />}
      {carregando && <Skeleton variant="rounded" height={240} />}
      {lista && !lista.length && (
        <Paper variant="outlined">
          <EstadoVazio titulo="Nenhum setor corresponde à sua descrição" texto="Descreva a demanda com outras palavras ou consulte a lista completa." />
        </Paper>
      )}

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr", xl: "repeat(3, 1fr)" }, gap: 1.5 }}>
        {lista?.map((s) => (
          <Paper key={s.id} variant="outlined" component="article" sx={{ p: 2.5, display: "flex", flexDirection: "column", gap: 1 }}>
            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
              <Box sx={{ flex: 1 }}>
                <Typography component="h2" sx={{ fontWeight: 600, fontSize: 16, color: cores.titulo }}>{s.nome}</Typography>
                <Typography variant="caption">{s.sigla}</Typography>
              </Box>
              {tem("gerir_setores") && (
                <Button size="small" startIcon={<Pencil size={14} />} onClick={() => setEdicao(s)}>Editar</Button>
              )}
            </Box>
            {s.descricao && <Typography variant="body2">{s.descricao}</Typography>}
            {s.competencias && (
              <Box>
                <Typography sx={{ fontSize: 12, fontWeight: 600, color: cores.textoSecundario }}>Competências</Typography>
                <Typography variant="body2" sx={{ color: cores.textoSecundario }}>{s.competencias}</Typography>
              </Box>
            )}
            {s.tipos_demanda.length > 0 && (
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                {s.tipos_demanda.map((t) => <Chip key={t} label={t} size="small" />)}
              </Box>
            )}
            {s.servicos.length > 0 && (
              <Typography variant="body2" sx={{ color: cores.textoSecundario }}>Serviços: {s.servicos.join("; ")}</Typography>
            )}
            <Box sx={{ mt: "auto", pt: 1, borderTop: `1px solid ${cores.bordaSutil}`, display: "grid", gap: 0.5 }}>
              <Typography variant="body2">
                {s.canal_contato ? <>Contato: <strong>{s.canal_contato}</strong></> : <Box component="span" sx={{ color: cores.textoSecundario }}>Canal de contato não cadastrado ou restrito</Box>}
              </Typography>
              {s.horario_atendimento && (
                <Typography variant="caption" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}><Clock size={12} /> {s.horario_atendimento}</Typography>
              )}
              {s.orientacao_acesso && <Typography variant="body2" sx={{ color: cores.textoSecundario }}>{s.orientacao_acesso}</Typography>}
            </Box>
          </Paper>
        ))}
      </Box>

      {edicao && <DialogoSetor setor={edicao} aoFechar={() => setEdicao(null)} />}
    </Pagina>
  );
}

function DialogoSetor({ setor, aoFechar }: { setor: Partial<Setor>; aoFechar: () => void }) {
  const queryClient = useQueryClient();
  const [f, setF] = useState({
    nome: setor.nome ?? "",
    sigla: setor.sigla ?? "",
    descricao: setor.descricao ?? "",
    competencias: setor.competencias ?? "",
    tipos_demanda: (setor.tipos_demanda ?? []).join(", "),
    servicos: (setor.servicos ?? []).join(", "),
    palavras_chave: (setor.palavras_chave ?? []).join(", "),
    canal_contato: setor.canal_contato ?? "",
    horario_atendimento: setor.horario_atendimento ?? "",
    orientacao_acesso: setor.orientacao_acesso ?? "",
    contato_visivel_para_todos: setor.contato_visivel_para_todos ?? true,
  });
  const lista = (v: string) => v.split(",").map((x) => x.trim()).filter(Boolean);
  const salvar = useMutation({
    mutationFn: () =>
      api(setor.id ? `/setores/${setor.id}/` : "/setores/", {
        method: setor.id ? "PATCH" : "POST",
        json: { ...f, tipos_demanda: lista(f.tipos_demanda), servicos: lista(f.servicos), palavras_chave: lista(f.palavras_chave) },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["setores"] });
      aoFechar();
    },
  });
  const campo = (chave: keyof typeof f, rotulo: string, extra: object = {}) => (
    <TextField label={rotulo} value={f[chave] as string} onChange={(e) => setF({ ...f, [chave]: e.target.value })} fullWidth {...extra} />
  );
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="sm">
      <DialogTitle>{setor.id ? "Editar setor" : "Cadastrar setor"}</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
        {salvar.isError && <Alert severity="error">{(salvar.error as Error).message}</Alert>}
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 140px", gap: 2 }}>
          {campo("nome", "Nome")}
          {campo("sigla", "Sigla")}
        </Box>
        {campo("descricao", "Descrição resumida")}
        {campo("competencias", "Competências", { multiline: true, minRows: 2 })}
        {campo("tipos_demanda", "Tipos de demanda atendidos", { helperText: "Separe por vírgulas." })}
        {campo("servicos", "Serviços prestados", { helperText: "Separe por vírgulas." })}
        {campo("palavras_chave", "Palavras-chave para o assistente", { helperText: "Ajudam a encaminhar perguntas a este setor." })}
        {campo("canal_contato", "Canal institucional de contato")}
        {campo("horario_atendimento", "Horário de atendimento")}
        {campo("orientacao_acesso", "Orientação para solicitar informações ou acesso", { multiline: true, minRows: 2 })}
        <FormControlLabel control={<Switch checked={f.contato_visivel_para_todos} onChange={(e) => setF({ ...f, contato_visivel_para_todos: e.target.checked })} />} label="Contato visível para todos os servidores" />
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button variant="contained" onClick={() => salvar.mutate()} disabled={!f.nome || !f.sigla || salvar.isPending}>Salvar setor</Button>
      </DialogActions>
    </Dialog>
  );
}
