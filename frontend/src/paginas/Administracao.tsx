import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  InputAdornment,
  ListItemText,
  MenuItem,
  Paper,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { Check, KeyRound, Minus, Pencil, Plus, Search, ShieldAlert, Trash2 } from "lucide-react";

import { api } from "../api/cliente";
import type { Autorizacao, Credenciais, DocumentoLista, LinkEnviado, Paginado, Perfil, Setor, UsuarioAdmin } from "../api/tipos";
import { Cabecalho, Erro, Pagina } from "../componentes/comuns";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";
import { data, dataHora, rotuloAcao } from "../util/formatos";
import CopiasSeguranca from "./CopiasSeguranca";
import SaudeSistema from "./SaudeSistema";

const ACOES = ["consultar", "visualizar", "baixar", "editar", "compartilhar", "administrar"];

export default function Administracao() {
  const { tem } = useAutenticacao();
  const abas = [
    tem("admin_usuarios") && { valor: "usuarios", rotulo: "Usuários" },
    { valor: "perfis", rotulo: "Perfis e funções" },
    { valor: "documentos", rotulo: "Permissões por documento" },
    tem("admin_permissoes") && { valor: "copias", rotulo: "Cópias de segurança" },
    tem("admin_permissoes") && { valor: "saude", rotulo: "Saúde do sistema" },
  ].filter(Boolean) as { valor: string; rotulo: string }[];
  const [parametros] = useSearchParams();
  const pedida = parametros.get("aba");
  const [aba, setAba] = useState(abas.some((a) => a.valor === pedida) ? (pedida as string) : abas[0].valor);

  return (
    <Pagina larga>
      <Cabecalho titulo="Administração" descricao="Usuários, perfis e permissões. Alterações em permissões críticas são restritas e ficam registradas na auditoria." />
      <Tabs value={aba} onChange={(_, v) => setAba(v)} sx={{ borderBottom: `1px solid ${cores.borda}`, mb: 3, "& .MuiTab-root": { textTransform: "none", fontWeight: 500 } }}>
        {abas.map((a) => <Tab key={a.valor} value={a.valor} label={a.rotulo} />)}
      </Tabs>
      {aba === "usuarios" && <Usuarios />}
      {aba === "perfis" && <Perfis />}
      {aba === "documentos" && <PermissoesDocumento />}
      {aba === "copias" && <CopiasSeguranca />}
      {aba === "saude" && <SaudeSistema />}
    </Pagina>
  );
}

function Usuarios() {
  const [busca, setBusca] = useState("");
  const [edicao, setEdicao] = useState<Partial<UsuarioAdmin> | null>(null);
  const [credenciais, setCredenciais] = useState<Credenciais | null>(null);
  const [linkEnviado, setLinkEnviado] = useState<LinkEnviado | null>(null);
  // Link para criar a senha (ADR-027) só existe com o envio de e-mail configurado.
  const provedores = useQuery({ queryKey: ["provedores"], queryFn: () => api<{ link_por_email?: boolean }>("/auth/provedores/") });
  const linkDisponivel = !!provedores.data?.link_por_email;
  const [novaSenhaPara, setNovaSenhaPara] = useState<UsuarioAdmin | null>(null);
  const usuarios = useQuery({ queryKey: ["usuarios", busca], queryFn: () => api<Paginado<UsuarioAdmin>>(`/usuarios/?q=${encodeURIComponent(busca)}&tamanho=50`) });
  const setores = useQuery({ queryKey: ["setores", "todos"], queryFn: () => api<Paginado<Setor>>("/setores/?tamanho=100") });
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Paginado<Perfil>>("/perfis/") });
  const nomePerfil = (id: number) => perfis.data?.results.find((p) => p.id === id)?.nome ?? id;

  return (
    <>
      <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
        <TextField size="small" placeholder="Buscar por usuário ou nome" value={busca} onChange={(e) => setBusca(e.target.value)} InputProps={{ startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment> }} sx={{ flex: "1 1 280px", maxWidth: 420 }} />
        <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => setEdicao({ is_active: true, perfis: [] })} sx={{ ml: "auto" }}>Cadastrar usuário</Button>
      </Box>
      {usuarios.isError && <Erro erro={usuarios.error} />}
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Usuário</TableCell>
              <TableCell>Nome</TableCell>
              <TableCell>Setor</TableCell>
              <TableCell>Perfis</TableCell>
              <TableCell>Situação</TableCell>
              <TableCell>Último acesso</TableCell>
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {usuarios.data?.results.map((u) => (
              <TableRow key={u.id} hover>
                <TableCell sx={{ fontWeight: 500 }}>{u.username}</TableCell>
                <TableCell>{u.nome_exibicao || `${u.first_name} ${u.last_name}`.trim() || "—"}</TableCell>
                <TableCell>{u.setor_nome ?? "—"}</TableCell>
                <TableCell>
                  <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>{u.perfis.map((p) => <Chip key={p} size="small" label={nomePerfil(p)} />)}</Box>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                    <Chip size="small" label={u.is_active ? "Ativo" : "Desativado"} sx={{ bgcolor: u.is_active ? cores.verificado.fundo : cores.bordaSutil, color: u.is_active ? cores.verificado.texto : cores.textoSecundario }} />
                    {u.senha_temporaria && <Chip size="small" variant="outlined" label="Aguardando 1º acesso" title="Ainda não criou a própria senha" />}
                  </Box>
                </TableCell>
                <TableCell>{dataHora(u.last_login)}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => setEdicao(u)} aria-label={`Editar ${u.username}`}><Pencil size={16} /></IconButton>
                  {!u.tem_login_microsoft && (
                    <IconButton size="small" onClick={() => setNovaSenhaPara(u)} aria-label={`Gerar nova senha para ${u.username}`} title="Gerar nova senha">
                      <KeyRound size={16} />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {edicao && (
        <DialogoUsuario
          usuario={edicao}
          setores={setores.data?.results ?? []}
          perfis={perfis.data?.results ?? []}
          aoFechar={() => setEdicao(null)}
          aoGerarCredenciais={setCredenciais}
          aoEnviarLink={setLinkEnviado}
          linkDisponivel={linkDisponivel}
        />
      )}
      {novaSenhaPara && (
        <DialogoNovaSenha
          usuario={novaSenhaPara}
          aoFechar={() => setNovaSenhaPara(null)}
          aoGerar={setCredenciais}
          aoEnviarLink={setLinkEnviado}
          linkDisponivel={linkDisponivel}
        />
      )}
      {credenciais && <DialogoCredenciais credenciais={credenciais} aoFechar={() => setCredenciais(null)} />}
      {linkEnviado && <DialogoLinkEnviado link={linkEnviado} aoFechar={() => setLinkEnviado(null)} />}
    </>
  );
}

function DialogoUsuario({
  usuario,
  setores,
  perfis,
  aoFechar,
  aoGerarCredenciais,
  aoEnviarLink,
  linkDisponivel,
}: {
  usuario: Partial<UsuarioAdmin>;
  setores: Setor[];
  perfis: Perfil[];
  aoFechar: () => void;
  aoGerarCredenciais: (c: Credenciais) => void;
  aoEnviarLink: (l: LinkEnviado) => void;
  linkDisponivel: boolean;
}) {
  const [modoSenha, setModoSenha] = useState<"link" | "gerar" | "manual">(linkDisponivel ? "link" : "gerar");
  const queryClient = useQueryClient();
  const [f, setF] = useState({
    username: usuario.username ?? "",
    nome_exibicao: usuario.nome_exibicao ?? "",
    email: usuario.email ?? "",
    matricula: usuario.matricula ?? "",
    setor: usuario.setor ? String(usuario.setor) : "",
    perfis: (usuario.perfis ?? []).map(String),
    is_active: usuario.is_active ?? true,
    senha: "",
  });
  const salvar = useMutation({
    mutationFn: () => {
      const corpo: Record<string, unknown> = { ...f, setor: f.setor ? Number(f.setor) : null, perfis: f.perfis.map(Number) };
      if (!usuario.id && modoSenha === "gerar") {
        corpo.gerar_senha = true;
        delete corpo.senha;
      }
      if (!usuario.id && modoSenha === "link") {
        corpo.enviar_link = true;
        delete corpo.senha;
      }
      if (!corpo.senha) delete corpo.senha;
      return api<UsuarioAdmin & { credenciais?: Credenciais; link?: LinkEnviado }>(usuario.id ? `/usuarios/${usuario.id}/` : "/usuarios/", {
        method: usuario.id ? "PATCH" : "POST",
        json: corpo,
      });
    },
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey: ["usuarios"] });
      if (r.credenciais) aoGerarCredenciais(r.credenciais);
      if (r.link) aoEnviarLink(r.link);
      aoFechar();
    },
  });
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="sm">
      <DialogTitle>{usuario.id ? `Editar ${usuario.username}` : "Cadastrar usuário"}</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
        {salvar.isError && <Alert severity="error">{(salvar.error as Error).message}</Alert>}
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2 }}>
          <TextField label="Usuário" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} disabled={!!usuario.id} />
          <TextField label="Matrícula" value={f.matricula} onChange={(e) => setF({ ...f, matricula: e.target.value })} />
        </Box>
        <TextField label="Nome de exibição" value={f.nome_exibicao} onChange={(e) => setF({ ...f, nome_exibicao: e.target.value })} />
        <TextField label="E-mail institucional" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        <TextField select label="Setor" value={f.setor} onChange={(e) => setF({ ...f, setor: e.target.value })}>
          <MenuItem value="">Sem setor</MenuItem>
          {setores.map((s) => <MenuItem key={s.id} value={String(s.id)}>{s.sigla} — {s.nome}</MenuItem>)}
        </TextField>
        <TextField
          select
          label="Perfis"
          value={f.perfis}
          onChange={(e) => setF({ ...f, perfis: e.target.value as unknown as string[] })}
          SelectProps={{ multiple: true, renderValue: (v) => (v as string[]).map((id) => perfis.find((p) => String(p.id) === id)?.nome).join(", ") }}
        >
          {perfis.map((p) => (
            <MenuItem key={p.id} value={String(p.id)}>
              <Checkbox size="small" checked={f.perfis.includes(String(p.id))} />
              <ListItemText primary={p.nome} secondary={p.descricao} />
            </MenuItem>
          ))}
        </TextField>
        {!usuario.id && (
          <TextField select id="usuario-modo-senha" label="Senha de acesso" value={modoSenha} onChange={(e) => setModoSenha(e.target.value as "link" | "gerar" | "manual")}>
            {linkDisponivel && <MenuItem value="link">Enviar link para a pessoa criar a senha (recomendado)</MenuItem>}
            <MenuItem value="gerar">Gerar senha e enviar por e-mail</MenuItem>
            <MenuItem value="manual">Definir a senha inicial</MenuItem>
          </TextField>
        )}
        {!usuario.id && modoSenha === "link" ? (
          <Alert severity="info" variant="outlined">
            A pessoa recebe no e-mail acima um link para criar a própria senha. Nenhuma senha passa pelo e-mail nem por você.
          </Alert>
        ) : !usuario.id && modoSenha === "gerar" ? (
          <Alert severity="info" variant="outlined">
            O Nexo gera uma senha temporária e envia usuário, senha e endereço para o e-mail acima. No primeiro acesso a pessoa
            cria a própria senha. Se o e-mail não puder ser enviado, a senha aparece para você entregar.
          </Alert>
        ) : (
          <TextField
            label={usuario.id ? "Nova senha provisória (opcional)" : "Senha inicial"}
            type="password"
            value={f.senha}
            onChange={(e) => setF({ ...f, senha: e.target.value })}
            helperText="Mínimo de 10 caracteres. A pessoa cria a própria senha no próximo acesso."
            autoComplete="new-password"
          />
        )}
        <FormControlLabel control={<Switch checked={f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} />} label="Conta ativa" />
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button
          variant="contained"
          onClick={() => salvar.mutate()}
          disabled={
            !f.username ||
            salvar.isPending ||
            (!usuario.id && modoSenha !== "manual" && !f.email.trim()) ||
            (!usuario.id && modoSenha === "manual" && !f.senha)
          }
        >
          {!usuario.id && modoSenha !== "manual" ? "Salvar e enviar acesso" : "Salvar usuário"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** Gera nova senha temporária para quem esqueceu a senha (ADR-018). */
function DialogoNovaSenha({
  usuario,
  aoFechar,
  aoGerar,
  aoEnviarLink,
  linkDisponivel,
}: {
  usuario: UsuarioAdmin;
  aoFechar: () => void;
  aoGerar: (c: Credenciais) => void;
  aoEnviarLink: (l: LinkEnviado) => void;
  linkDisponivel: boolean;
}) {
  const queryClient = useQueryClient();
  const link = useMutation({
    mutationFn: () => api<LinkEnviado>(`/usuarios/${usuario.id}/enviar-link/`, { method: "POST" }),
    onSuccess: (l) => {
      queryClient.invalidateQueries({ queryKey: ["usuarios"] });
      aoEnviarLink(l);
      aoFechar();
    },
  });
  const gerar = useMutation({
    mutationFn: () => api<Credenciais>(`/usuarios/${usuario.id}/gerar-senha/`, { method: "POST" }),
    onSuccess: (c) => {
      queryClient.invalidateQueries({ queryKey: ["usuarios"] });
      aoGerar(c);
      aoFechar();
    },
  });
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>Gerar nova senha para {usuario.username}?</DialogTitle>
      <DialogContent>
        {gerar.isError && <Alert severity="error" sx={{ mb: 2 }}>{(gerar.error as Error).message}</Alert>}
        {link.isError && <Alert severity="error" sx={{ mb: 2 }}>{(link.error as Error).message}</Alert>}
        <Typography variant="body2">
          A senha atual deixa de valer agora. O Nexo gera uma senha temporária
          {usuario.email ? ` e a envia para ${usuario.email}` : " (o usuário não tem e-mail: você verá a senha para entregar)"}. No próximo acesso a
          pessoa cria a própria senha.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        {linkDisponivel && usuario.email && (
          <Button onClick={() => link.mutate()} disabled={link.isPending || gerar.isPending}>Enviar link para criar senha</Button>
        )}
        <Button variant="contained" onClick={() => gerar.mutate()} disabled={gerar.isPending || link.isPending}>Gerar nova senha</Button>
      </DialogActions>
    </Dialog>
  );
}

/** Confirmação do link enviado (ADR-027): não há senha para mostrar. */
function DialogoLinkEnviado({ link, aoFechar }: { link: LinkEnviado; aoFechar: () => void }) {
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>Link enviado</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2 }}>
        {link.enviado_por_email ? (
          <Alert severity="success">
            Enviamos para {link.destino_email} um link para criar a senha
            {link.expira_em ? `, válido até ${dataHora(link.expira_em)}` : ""}. O link funciona uma vez só.
          </Alert>
        ) : (
          <Alert severity="warning">{link.aviso || "O e-mail não foi enviado."}</Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button variant="contained" onClick={aoFechar}>Concluir</Button>
      </DialogActions>
    </Dialog>
  );
}

/** Mostra a senha gerada UMA vez; ela não pode ser consultada depois. */
function DialogoCredenciais({ credenciais, aoFechar }: { credenciais: Credenciais; aoFechar: () => void }) {
  const [copiado, setCopiado] = useState(false);
  const texto = `Usuário: ${credenciais.usuario}\nSenha temporária: ${credenciais.senha_temporaria}`;
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>Acesso criado</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2 }}>
        {credenciais.enviado_por_email ? (
          <Alert severity="success">Usuário e senha temporária enviados para {credenciais.destino_email}.</Alert>
        ) : (
          <Alert severity="warning">{credenciais.aviso || "O e-mail não foi enviado. Entregue a senha por um meio seguro."}</Alert>
        )}
        <Box sx={{ p: 2, borderRadius: 2, bgcolor: cores.fundo, border: `1px solid ${cores.borda}`, fontFamily: "\"JetBrains Mono\", monospace", fontSize: 14, display: "grid", gap: 0.5 }}>
          <span>Usuário: <strong>{credenciais.usuario}</strong></span>
          <span>Senha temporária: <strong>{credenciais.senha_temporaria}</strong></span>
        </Box>
        <Typography variant="body2" color="text.secondary">
          {credenciais.expira_em ? `A senha vale até ${dataHora(credenciais.expira_em)}. ` : ""}
          Esta é a única vez que a senha aparece. No primeiro acesso a pessoa cria a própria senha.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(texto);
              setCopiado(true);
            } catch {
              setCopiado(false);
            }
          }}
        >
          {copiado ? "Copiado" : "Copiar"}
        </Button>
        <Button variant="contained" onClick={aoFechar}>Concluir</Button>
      </DialogActions>
    </Dialog>
  );
}

function Perfis() {
  const { tem } = useAutenticacao();
  const queryClient = useQueryClient();
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Paginado<Perfil>>("/perfis/") });
  const funcoes = useQuery({ queryKey: ["funcoes"], queryFn: () => api<{ valor: string; rotulo: string; critica: boolean }[]>("/funcoes/") });
  const editavel = tem("admin_permissoes");
  const alternar = useMutation({
    mutationFn: ({ perfil, funcao }: { perfil: Perfil; funcao: string }) =>
      api(`/perfis/${perfil.id}/`, {
        method: "PATCH",
        json: { funcoes: perfil.funcoes.includes(funcao) ? perfil.funcoes.filter((f) => f !== funcao) : [...perfil.funcoes, funcao] },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["perfis"] }),
  });
  return (
    <>
      {!editavel && <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>Somente administradores de permissões podem alterar perfis.</Alert>}
      {alternar.isError && <Erro erro={alternar.error} />}
      <TableContainer component={Paper} variant="outlined">
        <Table size="small" aria-label="Matriz de perfis e funções">
          <TableHead>
            <TableRow>
              <TableCell>Perfil</TableCell>
              {funcoes.data?.map((f) => (
                <TableCell key={f.valor} align="center" sx={{ minWidth: 110 }}>
                  <Box sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}>
                    {f.rotulo}
                    {f.critica && <Tooltip title="Função crítica"><ShieldAlert size={14} color={cores.cautela.forte} /></Tooltip>}
                  </Box>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {perfis.data?.results.map((p) => (
              <TableRow key={p.id}>
                <TableCell>
                  <Typography sx={{ fontWeight: 600, fontSize: 14 }}>{p.nome}</Typography>
                  <Typography variant="caption">{p.descricao}</Typography>
                </TableCell>
                {funcoes.data?.map((f) => (
                  <TableCell key={f.valor} align="center">
                    <Checkbox size="small" checked={p.funcoes.includes(f.valor)} disabled={!editavel || alternar.isPending} onChange={() => alternar.mutate({ perfil: p, funcao: f.valor })} inputProps={{ "aria-label": `${f.rotulo} para ${p.nome}` }} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Typography variant="caption" component="p" sx={{ mt: 1.5 }}>
        Funções administrativas não dão acesso ao conteúdo dos documentos. O acesso documental é definido pela classificação de cada documento e pelas autorizações abaixo.
      </Typography>
    </>
  );
}

function PermissoesDocumento() {
  const queryClient = useQueryClient();
  const [termo, setTermo] = useState("");
  const [documento, setDocumento] = useState<DocumentoLista | null>(null);
  const [nova, setNova] = useState({ tipo: "setor", destino: "", acoes: ["visualizar"] as string[], valido_ate: "", motivo: "" });
  const opcoes = useQuery({ queryKey: ["documentos", "admin", termo], queryFn: () => api<Paginado<DocumentoLista>>(`/documentos/?q=${encodeURIComponent(termo)}&tamanho=15`) });
  const matriz = useQuery({
    queryKey: ["matriz", documento?.id],
    queryFn: () => api<{ documento: { id: number; titulo: string; classificacao: string }; autorizacoes: Autorizacao[] }>(`/acesso/documentos/${documento!.id}/matriz/`),
    enabled: !!documento,
    retry: false,
  });
  const setores = useQuery({ queryKey: ["setores", "todos"], queryFn: () => api<Paginado<Setor>>("/setores/?tamanho=100") });
  const perfis = useQuery({ queryKey: ["perfis"], queryFn: () => api<Paginado<Perfil>>("/perfis/") });

  const conceder = useMutation({
    mutationFn: () =>
      api(`/acesso/documentos/${documento!.id}/matriz/`, {
        method: "POST",
        json: { [nova.tipo]: Number(nova.destino), acoes: nova.acoes, valido_ate: nova.valido_ate ? `${nova.valido_ate}T23:59:59` : null, motivo: nova.motivo },
      }),
    onSuccess: () => {
      setNova({ ...nova, destino: "", motivo: "" });
      queryClient.invalidateQueries({ queryKey: ["matriz", documento?.id] });
    },
  });
  const revogar = useMutation({
    mutationFn: (id: number) => api(`/acesso/autorizacoes/${id}/`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["matriz", documento?.id] }),
  });

  return (
    <>
      <Autocomplete
        options={opcoes.data?.results ?? []}
        getOptionLabel={(o) => o.titulo}
        value={documento}
        onChange={(_, v) => setDocumento(v)}
        onInputChange={(_, v) => setTermo(v)}
        filterOptions={(x) => x}
        renderInput={(p) => <TextField {...p} label="Documento" placeholder="Digite o nome do documento" />}
        sx={{ maxWidth: 560, mb: 3 }}
        noOptionsText="Nenhum documento encontrado"
      />
      {matriz.isError && <Erro erro={matriz.error} />}
      {matriz.data && (
        <>
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            Classificação atual: <strong>{matriz.data.documento.classificacao}</strong>. As linhas abaixo somam permissões a essa classificação.
          </Typography>
          <TableContainer component={Paper} variant="outlined" sx={{ mb: 3 }}>
            <Table size="small" aria-label="Matriz de permissões">
              <TableHead>
                <TableRow>
                  <TableCell>Destinatário</TableCell>
                  {ACOES.map((a) => <TableCell key={a} align="center">{rotuloAcao[a]}</TableCell>)}
                  <TableCell>Validade</TableCell>
                  <TableCell>Concedido por</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {matriz.data.autorizacoes.length === 0 && (
                  <TableRow><TableCell colSpan={ACOES.length + 4} sx={{ color: cores.textoSecundario }}>Nenhuma autorização explícita.</TableCell></TableRow>
                )}
                {matriz.data.autorizacoes.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell sx={{ fontWeight: 500 }}>{a.destinatario}</TableCell>
                    {ACOES.map((acao) => (
                      <TableCell key={acao} align="center">
                        {a.acoes.includes(acao as never) ? (
                          <Check size={16} color={cores.verificado.forte} aria-label="Concedida" />
                        ) : a.acoes_efetivas.includes(acao as never) ? (
                          <Tooltip title="Implícita por outra ação"><Box component="span" sx={{ color: cores.semantico.forte, display: "inline-flex" }}><Check size={14} /></Box></Tooltip>
                        ) : (
                          <Minus size={14} color="#CBD5E1" aria-label="Não concedida" />
                        )}
                      </TableCell>
                    ))}
                    <TableCell>{a.valido_ate ? data(a.valido_ate) : "Sem prazo"}</TableCell>
                    <TableCell>{a.concedido_por_nome ?? "—"}</TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => revogar.mutate(a.id)} aria-label={`Revogar ${a.destinatario}`}><Trash2 size={16} /></IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <Paper variant="outlined" sx={{ p: 2.5, display: "grid", gap: 2, maxWidth: 720 }}>
            <Typography variant="h4" component="h2">Conceder permissão</Typography>
            {conceder.isError && <Alert severity="error">{(conceder.error as Error).message}</Alert>}
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "160px 1fr" }, gap: 2 }}>
              <TextField select size="small" label="Para" value={nova.tipo} onChange={(e) => setNova({ ...nova, tipo: e.target.value, destino: "" })}>
                <MenuItem value="setor">Setor</MenuItem>
                <MenuItem value="perfil">Perfil</MenuItem>
                <MenuItem value="usuario">Usuário (código)</MenuItem>
              </TextField>
              {nova.tipo === "usuario" ? (
                <TextField size="small" label="Código do usuário" value={nova.destino} onChange={(e) => setNova({ ...nova, destino: e.target.value.replace(/\D/g, "") })} />
              ) : (
                <TextField select size="small" label={nova.tipo === "setor" ? "Setor" : "Perfil"} value={nova.destino} onChange={(e) => setNova({ ...nova, destino: e.target.value })}>
                  {(nova.tipo === "setor" ? setores.data?.results.map((s) => ({ id: s.id, nome: `${s.sigla} — ${s.nome}` })) : perfis.data?.results.map((p) => ({ id: p.id, nome: p.nome })))?.map((o) => (
                    <MenuItem key={o.id} value={String(o.id)}>{o.nome}</MenuItem>
                  ))}
                </TextField>
              )}
            </Box>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              {ACOES.map((a) => (
                <FormControlLabel key={a} control={<Checkbox size="small" checked={nova.acoes.includes(a)} onChange={() => setNova({ ...nova, acoes: nova.acoes.includes(a) ? nova.acoes.filter((x) => x !== a) : [...nova.acoes, a] })} />} label={rotuloAcao[a]} />
              ))}
            </Box>
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "200px 1fr" }, gap: 2 }}>
              <TextField size="small" type="date" label="Válido até" InputLabelProps={{ shrink: true }} value={nova.valido_ate} onChange={(e) => setNova({ ...nova, valido_ate: e.target.value })} />
              <TextField size="small" label="Justificativa" value={nova.motivo} onChange={(e) => setNova({ ...nova, motivo: e.target.value })} />
            </Box>
            <Box>
              <Button variant="contained" onClick={() => conceder.mutate()} disabled={!nova.destino || !nova.acoes.length || conceder.isPending}>Conceder permissão</Button>
            </Box>
          </Paper>
        </>
      )}
    </>
  );
}
