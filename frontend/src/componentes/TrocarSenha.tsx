import { useState, type FormEvent } from "react";
import { Alert, Box, Button, TextField, Typography } from "@mui/material";

import { api, ErroApi } from "../api/cliente";
import type { Usuario } from "../api/tipos";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";

/** Troca de senha (ADR-018). `obrigatoria`: primeiro acesso com senha temporária. */
export default function TrocarSenha({ obrigatoria = false, aoConcluir }: { obrigatoria?: boolean; aoConcluir?: () => void }) {
  const { atualizarUsuario } = useAutenticacao();
  const [f, setF] = useState({ atual: "", nova: "", confirmacao: "" });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [geral, setGeral] = useState("");
  const [ok, setOk] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const diferentes = f.confirmacao.length > 0 && f.nova !== f.confirmacao;
  const curta = f.nova.length > 0 && f.nova.length < 10;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErros({});
    setGeral("");
    setEnviando(true);
    try {
      const u = await api<Usuario>("/auth/trocar-senha/", { method: "POST", json: { senha_atual: f.atual, nova_senha: f.nova } });
      setF({ atual: "", nova: "", confirmacao: "" });
      setOk(true);
      atualizarUsuario(u);
      aoConcluir?.();
    } catch (erro) {
      const dados = erro instanceof ErroApi ? (erro.dados as Record<string, string[] | string> | undefined) : undefined;
      if (dados && (dados.senha_atual || dados.nova_senha)) {
        setErros({
          atual: Array.isArray(dados.senha_atual) ? dados.senha_atual.join(" ") : "",
          nova: Array.isArray(dados.nova_senha) ? dados.nova_senha.join(" ") : "",
        });
      } else {
        setGeral(erro instanceof Error ? erro.message : "Não foi possível alterar a senha.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Box component="form" onSubmit={enviar} noValidate sx={{ display: "grid", gap: 2, maxWidth: 420 }}>
      {obrigatoria && (
        <Alert severity="info">
          Você entrou com uma senha temporária. Crie a sua senha para continuar usando o Nexo.
        </Alert>
      )}
      {ok && !obrigatoria && <Alert severity="success">Senha alterada. Outras sessões abertas foram encerradas.</Alert>}
      {geral && <Alert severity="error">{geral}</Alert>}
      <TextField
        id="senha-atual"
        label={obrigatoria ? "Senha temporária" : "Senha atual"}
        type="password"
        autoComplete="current-password"
        value={f.atual}
        onChange={(e) => setF({ ...f, atual: e.target.value })}
        error={!!erros.atual}
        helperText={erros.atual || (obrigatoria ? "A que você recebeu por e-mail ou do administrador." : " ")}
        required
      />
      <TextField
        id="senha-nova"
        label="Nova senha"
        type="password"
        autoComplete="new-password"
        value={f.nova}
        onChange={(e) => setF({ ...f, nova: e.target.value })}
        error={!!erros.nova || curta}
        helperText={erros.nova || "No mínimo 10 caracteres, sem ser só números nem parecida com seu nome ou usuário."}
        required
      />
      <TextField
        id="senha-confirmacao"
        label="Repita a nova senha"
        type="password"
        autoComplete="new-password"
        value={f.confirmacao}
        onChange={(e) => setF({ ...f, confirmacao: e.target.value })}
        error={diferentes}
        helperText={diferentes ? "As senhas não conferem." : " "}
        required
      />
      <Box>
        <Button type="submit" variant="contained" disabled={enviando || !f.atual || f.nova.length < 10 || f.nova !== f.confirmacao}>
          {enviando ? "Salvando…" : obrigatoria ? "Criar senha e continuar" : "Alterar senha"}
        </Button>
      </Box>
      <Typography variant="caption" sx={{ color: cores.textoSecundario }}>
        Use uma senha só sua, que você não usa em outros sistemas.
      </Typography>
    </Box>
  );
}
