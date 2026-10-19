import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import { Alert, Box, Button, Link, TextField, Typography } from "@mui/material";

import MarcaInstitucional from "../componentes/MarcaInstitucional";
import { api, ErroApi } from "../api/cliente";
import { cores } from "../tema";

/** Recuperação de senha pelo próprio usuário (ADR-024). */
function Moldura({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <Box sx={{ minHeight: "100dvh", display: "grid", placeItems: "center", px: 2, py: 6 }}>
      <Box sx={{ width: "100%", maxWidth: 400, display: "grid", gap: 2 }}>
        <MarcaInstitucional tamanho={44} claro />
        <Typography variant="h2" component="h1">
          {titulo}
        </Typography>
        {children}
        <Link component={RouterLink} to="/entrar" sx={{ fontSize: 14 }}>
          Voltar para a entrada
        </Link>
      </Box>
    </Box>
  );
}

export function EsqueciSenha() {
  const [identificacao, setIdentificacao] = useState("");
  const [resposta, setResposta] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const r = await api<{ detail: string }>("/auth/esqueci-senha/", { method: "POST", json: { identificacao: identificacao.trim() } });
      setResposta(r.detail);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível enviar agora.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Moldura titulo="Esqueci minha senha">
      {resposta ? (
        <Alert severity="info">{resposta}</Alert>
      ) : (
        <Box component="form" onSubmit={enviar} noValidate sx={{ display: "grid", gap: 2 }}>
          <Typography variant="body2" sx={{ color: cores.textoSecundario }}>
            Informe o seu usuário ou o e-mail cadastrado. Enviaremos um link para você criar uma nova senha.
          </Typography>
          {erro && <Alert severity="error">{erro}</Alert>}
          <TextField
            label="Usuário ou e-mail"
            autoComplete="username"
            value={identificacao}
            onChange={(e) => setIdentificacao(e.target.value)}
            required
            autoFocus
          />
          <Button type="submit" variant="contained" disabled={enviando || !identificacao.trim()} sx={{ height: 44 }}>
            {enviando ? "Enviando…" : "Enviar link"}
          </Button>
        </Box>
      )}
    </Moldura>
  );
}

export function RedefinirSenha() {
  const [parametros] = useSearchParams();
  const u = parametros.get("u") ?? "";
  const t = parametros.get("t") ?? "";
  const [situacao, setSituacao] = useState<"verificando" | "valido" | "invalido" | "concluido">("verificando");
  const [mensagem, setMensagem] = useState("");
  const [usuario, setUsuario] = useState("");
  const [f, setF] = useState({ nova: "", confirmacao: "" });
  const [erroSenha, setErroSenha] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api<{ usuario: string }>("/auth/redefinir-senha/", { method: "POST", json: { u, t } })
      .then((r) => {
        setUsuario(r.usuario);
        setSituacao("valido");
      })
      .catch((err) => {
        setMensagem(err instanceof Error ? err.message : "Link inválido.");
        setSituacao("invalido");
      });
  }, [u, t]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErroSenha("");
    setEnviando(true);
    try {
      const r = await api<{ detail: string }>("/auth/redefinir-senha/", { method: "POST", json: { u, t, nova_senha: f.nova } });
      setMensagem(r.detail);
      setSituacao("concluido");
    } catch (err) {
      const dados = err instanceof ErroApi ? (err.dados as { nova_senha?: string[] } | undefined) : undefined;
      if (dados?.nova_senha) setErroSenha(dados.nova_senha.join(" "));
      else {
        setMensagem(err instanceof Error ? err.message : "Não foi possível criar a senha.");
        setSituacao("invalido");
      }
    } finally {
      setEnviando(false);
    }
  }

  const diferentes = f.confirmacao.length > 0 && f.nova !== f.confirmacao;
  return (
    <Moldura titulo="Criar nova senha">
      {situacao === "verificando" && <Typography variant="body2">Conferindo o link…</Typography>}
      {situacao === "invalido" && (
        <Alert severity="error" action={<Button component={RouterLink} to="/esqueci-senha" color="inherit" size="small">Pedir novo</Button>}>
          {mensagem}
        </Alert>
      )}
      {situacao === "concluido" && (
        <Alert severity="success" action={<Button component={RouterLink} to="/entrar" color="inherit" size="small">Entrar</Button>}>
          {mensagem}
        </Alert>
      )}
      {situacao === "valido" && (
        <Box component="form" onSubmit={enviar} noValidate sx={{ display: "grid", gap: 2 }}>
          <Typography variant="body2" sx={{ color: cores.textoSecundario }}>
            Usuário: <strong>{usuario}</strong>. Depois de criar a senha, as outras sessões abertas são encerradas.
          </Typography>
          <TextField
            label="Nova senha"
            type="password"
            autoComplete="new-password"
            value={f.nova}
            onChange={(e) => setF({ ...f, nova: e.target.value })}
            error={!!erroSenha}
            helperText={erroSenha || "No mínimo 10 caracteres, sem ser só números nem parecida com seu nome ou usuário."}
            required
            autoFocus
          />
          <TextField
            label="Repita a nova senha"
            type="password"
            autoComplete="new-password"
            value={f.confirmacao}
            onChange={(e) => setF({ ...f, confirmacao: e.target.value })}
            error={diferentes}
            helperText={diferentes ? "As senhas não conferem." : " "}
            required
          />
          <Button type="submit" variant="contained" disabled={enviando || f.nova.length < 10 || f.nova !== f.confirmacao} sx={{ height: 44 }}>
            {enviando ? "Salvando…" : "Criar senha"}
          </Button>
        </Box>
      )}
    </Moldura>
  );
}
