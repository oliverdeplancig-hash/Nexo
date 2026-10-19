import { Box, Button, Chip, Paper, Typography } from "@mui/material";
import { LogOut } from "lucide-react";

import { Cabecalho, Pagina, Rotulo, TituloSecao, Valor } from "../componentes/comuns";
import TrocarSenha from "../componentes/TrocarSenha";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";

const FUNCOES: Record<string, string> = {
  importar_documentos: "Cadastrar e importar documentos",
  gerir_colecoes: "Gerir pastas e coleções",
  gerir_regras: "Gerir o motor de respostas",
  gerir_setores: "Gerir o diretório de setores",
  admin_usuarios: "Administrar usuários",
  admin_permissoes: "Administrar perfis e permissões",
  ver_auditoria: "Consultar auditoria",
};

export default function Perfil() {
  const { usuario, sair } = useAutenticacao();
  if (!usuario) return null;
  return (
    <Pagina>
      <Cabecalho titulo="Perfil e configurações" acoes={<Button variant="outlined" startIcon={<LogOut size={16} />} onClick={sair}>Sair</Button>} />
      <Paper variant="outlined" sx={{ p: 3, maxWidth: 640 }}>
        <Box component="dl" sx={{ m: 0 }}>
          <Rotulo>Nome</Rotulo>
          <Valor>{usuario.nome}</Valor>
          <Rotulo>Usuário</Rotulo>
          <Valor>{usuario.username}</Valor>
          {usuario.matricula && (<><Rotulo>Matrícula</Rotulo><Valor>{usuario.matricula}</Valor></>)}
          {usuario.email && (<><Rotulo>E-mail</Rotulo><Valor>{usuario.email}</Valor></>)}
          <Rotulo>Setor</Rotulo>
          <Valor>{usuario.setor ? `${usuario.setor.nome} (${usuario.setor.sigla})` : "Sem setor vinculado"}</Valor>
          <Rotulo>Perfis de acesso</Rotulo>
          <Box component="dd" sx={{ m: 0, mt: 0.5, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
            {usuario.perfis.length ? usuario.perfis.map((p) => <Chip key={p.codigo} label={p.nome} size="small" />) : <Valor>Nenhum</Valor>}
          </Box>
          <Rotulo>Funções</Rotulo>
          <Valor>{usuario.funcoes.length ? usuario.funcoes.map((f) => FUNCOES[f] ?? f).join("; ") : "Consulta de documentos autorizados e uso do assistente"}</Valor>
        </Box>
        <Typography variant="caption" component="p" sx={{ mt: 3, color: cores.textoSecundario }}>
          Para alterar seus dados, setor ou perfis, procure a administração do sistema.
        </Typography>
      </Paper>
      <Paper variant="outlined" component="section" aria-label="Alterar senha" sx={{ p: 3, maxWidth: 640, mt: 3 }}>
        <TituloSecao>Alterar senha</TituloSecao>
        {usuario.pode_alterar_senha ? (
          <TrocarSenha />
        ) : (
          <Typography variant="body2" sx={{ color: cores.textoSecundario }}>
            Você entra com a conta Microsoft institucional. A senha é alterada na própria conta Microsoft.
          </Typography>
        )}
      </Paper>
    </Pagina>
  );
}
