import { Box, Button, Paper, Typography } from "@mui/material";
import { LogOut } from "lucide-react";

import MarcaInstitucional from "../componentes/MarcaInstitucional";
import TrocarSenha from "../componentes/TrocarSenha";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";

/** Primeiro acesso com senha temporária: só dá para criar a senha ou sair (ADR-018). */
export default function PrimeiroAcesso() {
  const { usuario, sair } = useAutenticacao();
  return (
    <Box component="main" sx={{ minHeight: "100dvh", display: "grid", placeItems: "center", bgcolor: cores.fundo, px: 2, py: 6 }}>
      <Paper variant="outlined" sx={{ p: { xs: 3, sm: 4 }, width: "100%", maxWidth: 480 }}>
        <Box sx={{ mb: 3 }}>
          <MarcaInstitucional tamanho={40} claro />
        </Box>
        <Typography variant="h2" component="h1">
          Crie a sua senha
        </Typography>
        <Typography variant="body2" sx={{ color: cores.textoSecundario, mt: 0.5, mb: 3 }}>
          Olá, {usuario?.nome}. Este é o seu primeiro acesso como <strong>{usuario?.username}</strong>.
        </Typography>
        <TrocarSenha obrigatoria />
        <Button sx={{ mt: 3 }} startIcon={<LogOut size={16} />} onClick={sair}>
          Sair
        </Button>
      </Paper>
    </Box>
  );
}
