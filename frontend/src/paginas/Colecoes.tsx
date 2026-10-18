import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, Paper, Switch, TextField, Typography } from "@mui/material";
import { Folder, FolderLock, Plus } from "lucide-react";

import { api } from "../api/cliente";
import type { Colecao, Paginado } from "../api/tipos";
import { Cabecalho, EstadoVazio, Erro, Pagina } from "../componentes/comuns";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";

export default function Colecoes() {
  const { tem } = useAutenticacao();
  const navegar = useNavigate();
  const queryClient = useQueryClient();
  const [nova, setNova] = useState<{ nome: string; descricao: string; pessoal: boolean } | null>(null);
  const colecoes = useQuery({ queryKey: ["colecoes"], queryFn: () => api<Paginado<Colecao>>("/colecoes/?tamanho=100") });
  const criar = useMutation({
    mutationFn: () => api("/colecoes/", { method: "POST", json: nova }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["colecoes"] });
      setNova(null);
    },
  });
  return (
    <Pagina>
      <Cabecalho
        titulo="Pastas e coleções"
        descricao="Agrupamentos de documentos. Uma coleção não altera as permissões: cada servidor vê apenas os documentos autorizados para ele."
        acoes={<Button variant="contained" startIcon={<Plus size={16} />} onClick={() => setNova({ nome: "", descricao: "", pessoal: !tem("gerir_colecoes") })}>Nova coleção</Button>}
      />
      {colecoes.isError && <Erro erro={colecoes.error} />}
      {colecoes.data?.results.length === 0 && <Paper variant="outlined"><EstadoVazio icone={<Folder size={28} />} titulo="Nenhuma coleção ainda" texto="Crie uma coleção para reunir documentos de um mesmo tema." /></Paper>}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(3, 1fr)" }, gap: 1.5 }}>
        {colecoes.data?.results.map((c) => (
          <Paper key={c.id} variant="outlined" component="button" onClick={() => navegar(`/repositorio?colecao=${c.id}`)} sx={{ p: 2, textAlign: "left", cursor: "pointer", font: "inherit", display: "flex", gap: 1.5, "&:hover": { borderColor: cores.primariaBorda } }}>
            {c.pessoal ? <FolderLock size={22} color={cores.textoSecundario} /> : <Folder size={22} color={cores.primaria} />}
            <Box>
              <Typography sx={{ fontWeight: 600, fontSize: 15 }}>{c.nome}</Typography>
              {c.descricao && <Typography variant="body2" sx={{ color: cores.textoSecundario }}>{c.descricao}</Typography>}
              <Typography variant="caption">{c.total_documentos ?? 0} documento(s) visíveis para você{c.pessoal ? ", pessoal" : ""}</Typography>
            </Box>
          </Paper>
        ))}
      </Box>
      {nova && (
        <Dialog open onClose={() => setNova(null)} fullWidth maxWidth="xs">
          <DialogTitle>Nova coleção</DialogTitle>
          <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
            {criar.isError && <Alert severity="error">{(criar.error as Error).message}</Alert>}
            <TextField label="Nome" value={nova.nome} onChange={(e) => setNova({ ...nova, nome: e.target.value })} autoFocus />
            <TextField label="Descrição" value={nova.descricao} onChange={(e) => setNova({ ...nova, descricao: e.target.value })} multiline minRows={2} />
            <FormControlLabel control={<Switch checked={nova.pessoal} disabled={!tem("gerir_colecoes")} onChange={(e) => setNova({ ...nova, pessoal: e.target.checked })} />} label="Coleção pessoal (só você vê)" />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setNova(null)}>Cancelar</Button>
            <Button variant="contained" onClick={() => criar.mutate()} disabled={!nova.nome.trim()}>Criar coleção</Button>
          </DialogActions>
        </Dialog>
      )}
    </Pagina>
  );
}
