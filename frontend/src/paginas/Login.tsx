import { useEffect, useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Divider,
  TextField,
  Typography,
} from "@mui/material";

import MarcaInstitucional from "../componentes/MarcaInstitucional";
import { api } from "../api/cliente";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";

interface Provedores {
  senha_local: boolean;
  microsoft: { ativo: boolean; rotulo: string };
}

/** Mensagens para os códigos devolvidos pelo retorno do login Microsoft (apps/contas/entra.py). */
const ERROS_LOGIN_INSTITUCIONAL: Record<string, string> = {
  cancelado: "O login na conta Microsoft foi cancelado.",
  dominio: "Use o e-mail institucional para entrar no Nexo.",
  locatario: "Esta conta Microsoft não pertence à instituição.",
  sem_cadastro:
    "Seu acesso ao Nexo ainda não foi liberado. Procure o administrador do sistema.",
  inativo:
    "Seu acesso ao Nexo está desativado. Procure o administrador do sistema.",
  conflito:
    "Já existe um usuário com este e-mail. Procure o administrador do sistema.",
  expirado: "A tentativa de login expirou. Tente novamente.",
  estado_invalido:
    "A tentativa de login não pôde ser confirmada. Tente novamente.",
  indisponivel:
    "O login institucional não respondeu. Tente novamente em instantes.",
  desativado: "O login institucional não está configurado neste servidor.",
  token_invalido:
    "A resposta da Microsoft não pôde ser validada. Tente novamente ou procure a TI.",
  troca_codigo:
    "O login institucional está mal configurado no servidor. Procure a TI.",
  microsoft: "A Microsoft recusou o login. Tente novamente ou procure a TI.",
};

function MarcaMicrosoft() {
  // Quatro quadrados do botão padrão "Entrar com a Microsoft" (diretrizes de marca da Microsoft).
  return (
    <Box
      component="svg"
      viewBox="0 0 21 21"
      sx={{ width: 18, height: 18 }}
      aria-hidden
    >
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </Box>
  );
}

export default function Login() {
  const { entrar } = useAutenticacao();
  const local = useLocation();
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState(() => {
    const codigo = new URLSearchParams(local.search).get("erro");
    return codigo
      ? (ERROS_LOGIN_INSTITUCIONAL[codigo] ??
          "Não foi possível entrar com a conta institucional.")
      : "";
  });
  const [enviando, setEnviando] = useState(false);
  const [provedores, setProvedores] = useState<Provedores | null>(null);

  useEffect(() => {
    api<Provedores>("/auth/provedores/")
      .then(setProvedores)
      .catch(() =>
        setProvedores({
          senha_local: true,
          microsoft: { ativo: false, rotulo: "" },
        }),
      );
  }, []);

  const destino = (
    (local.state as { de?: string } | null)?.de ?? "/"
  ).startsWith("/")
    ? ((local.state as { de?: string } | null)?.de ?? "/")
    : "/";
  const senhaLocal = provedores?.senha_local ?? true;
  const microsoft = provedores?.microsoft.ativo ?? false;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      await entrar(usuario.trim(), senha);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível entrar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100dvh",
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "minmax(0, 5fr) minmax(0, 6fr)" },
      }}
    >
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "space-between",
          bgcolor: cores.barraLateral,
          color: cores.barraLateralTexto,
          p: 6,
        }}
      >
        <MarcaInstitucional tamanho={48} />
        <Box sx={{ maxWidth: 420 }}>
          <Typography
            sx={{
              fontSize: 40,
              fontWeight: 700,
              letterSpacing: "-0.03em",
              lineHeight: 1.1,
            }}
          >
            Nexo
          </Typography>
          <Typography
            sx={{ mt: 2, fontSize: 18, lineHeight: 1.5, color: "#CBD5E1" }}
          >
            Conexão entre documentos, setores e pessoas. Encontre normas e
            procedimentos, entenda o que fazer e descubra quem pode ajudar.
          </Typography>
        </Box>
        <Typography sx={{ fontSize: 13, color: cores.barraLateralMudo }}>
          Acesso restrito a servidores autorizados. As consultas são registradas
          para auditoria.
        </Typography>
      </Box>

      <Box sx={{ display: "grid", placeItems: "center", px: 2, py: 6 }}>
        <Box
          component="form"
          onSubmit={enviar}
          sx={{ width: "100%", maxWidth: 380 }}
          noValidate
        >
          <Box sx={{ display: { md: "none" }, mb: 3 }}>
            <MarcaInstitucional tamanho={44} claro />
          </Box>
          <Typography variant="h2" component="h1">
            Entrar no Nexo
          </Typography>
          <Typography
            variant="body2"
            sx={{ color: cores.textoSecundario, mt: 0.5, mb: 3 }}
          >
            {microsoft
              ? "Use a sua conta institucional."
              : "Use as credenciais fornecidas pela instituição."}
          </Typography>
          {erro && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {erro}
            </Alert>
          )}
          {microsoft && (
            <Button
              variant="outlined"
              fullWidth
              href={`/api/v1/auth/microsoft/?destino=${encodeURIComponent(destino)}`}
              startIcon={<MarcaMicrosoft />}
              sx={{
                height: 44,
                mb: senhaLocal ? 2 : 0,
                color: cores.texto,
                borderColor: "#8C8C8C",
              }}
            >
              {provedores?.microsoft.rotulo}
            </Button>
          )}
          {microsoft && senhaLocal && (
            <Divider sx={{ mb: 2, fontSize: 13, color: cores.textoSecundario }}>
              ou com usuário e senha
            </Divider>
          )}
          {senhaLocal && (
            <>
              <TextField
                label="Usuário"
                fullWidth
                autoComplete="username"
                value={usuario}
                onChange={(e) => setUsuario(e.target.value)}
                sx={{ mb: 2 }}
                required
                autoFocus
              />
              <TextField
                label="Senha"
                type="password"
                fullWidth
                autoComplete="current-password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                sx={{ mb: 3 }}
                required
              />
              <Button
                type="submit"
                variant="contained"
                fullWidth
                disabled={enviando || !usuario || !senha}
                sx={{ height: 44 }}
              >
                {enviando ? "Entrando…" : "Entrar"}
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Box>
  );
}
