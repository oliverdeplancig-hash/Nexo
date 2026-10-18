import { useState, type FormEvent } from "react";
import { Alert, Box, Button, TextField, Typography } from "@mui/material";

import MarcaInstitucional from "../componentes/MarcaInstitucional";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";

export default function Login() {
  const { entrar } = useAutenticacao();
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

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
    <Box sx={{ minHeight: "100dvh", display: "grid", gridTemplateColumns: { xs: "1fr", md: "minmax(0, 5fr) minmax(0, 6fr)" } }}>
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
          <Typography sx={{ fontSize: 40, fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.1 }}>Nexo</Typography>
          <Typography sx={{ mt: 2, fontSize: 18, lineHeight: 1.5, color: "#CBD5E1" }}>
            Conexão entre documentos, setores e pessoas. Encontre normas e procedimentos, entenda o que fazer e descubra
            quem pode ajudar.
          </Typography>
        </Box>
        <Typography sx={{ fontSize: 13, color: cores.barraLateralMudo }}>
          Acesso restrito a servidores autorizados. As consultas são registradas para auditoria.
        </Typography>
      </Box>

      <Box sx={{ display: "grid", placeItems: "center", px: 2, py: 6 }}>
        <Box component="form" onSubmit={enviar} sx={{ width: "100%", maxWidth: 380 }} noValidate>
          <Box sx={{ display: { md: "none" }, mb: 3 }}>
            <MarcaInstitucional tamanho={44} claro />
          </Box>
          <Typography variant="h2" component="h1">
            Entrar no Nexo
          </Typography>
          <Typography variant="body2" sx={{ color: cores.textoSecundario, mt: 0.5, mb: 3 }}>
            Use as credenciais fornecidas pela instituição.
          </Typography>
          {erro && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {erro}
            </Alert>
          )}
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
          <Button type="submit" variant="contained" fullWidth disabled={enviando || !usuario || !senha} sx={{ height: 44 }}>
            {enviando ? "Entrando…" : "Entrar"}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
