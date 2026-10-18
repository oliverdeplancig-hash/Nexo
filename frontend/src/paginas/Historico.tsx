import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Box, IconButton, InputAdornment, Paper, TextField, Tooltip, Typography } from "@mui/material";
import { Archive, FileSearch, MessageSquare, Search } from "lucide-react";

import { api } from "../api/cliente";
import type { Conversa, Paginado } from "../api/tipos";
import { Cabecalho, EstadoVazio, Erro, Pagina } from "../componentes/comuns";
import { cores } from "../tema";
import { relativo } from "../util/formatos";

export default function Historico() {
  const [termo, setTermo] = useState("");
  const queryClient = useQueryClient();
  const conversas = useQuery({ queryKey: ["conversas", "historico", termo], queryFn: () => api<Paginado<Conversa>>(`/conversas/?q=${encodeURIComponent(termo)}&tamanho=50`) });
  const arquivar = useMutation({
    mutationFn: (id: number) => api(`/conversas/${id}/`, { method: "PATCH", json: { arquivada: true } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversas"] }),
  });
  return (
    <Pagina>
      <Cabecalho titulo="Histórico de conversas" descricao="Somente você vê as suas conversas." />
      <TextField size="small" fullWidth placeholder="Buscar pelo título" value={termo} onChange={(e) => setTermo(e.target.value)} InputProps={{ startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment> }} sx={{ mb: 2, maxWidth: 480 }} />
      {conversas.isError && <Erro erro={conversas.error} />}
      <Paper variant="outlined">
        {conversas.data?.results.length === 0 && <EstadoVazio icone={<MessageSquare size={28} />} titulo="Nenhuma conversa encontrada" />}
        {conversas.data?.results.map((c, i) => (
          <Box key={c.id} sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2.5, py: 1.5, borderTop: i ? `1px solid ${cores.bordaSutil}` : 0 }}>
            {c.documento_contexto ? <FileSearch size={18} color={cores.textoSecundario} /> : <MessageSquare size={18} color={cores.textoSecundario} />}
            <Box component={RouterLink} to={`/assistente/${c.id}`} sx={{ flex: 1, minWidth: 0, textDecoration: "none", color: "inherit" }}>
              <Typography noWrap sx={{ fontWeight: 500, fontSize: 14, color: cores.titulo }}>{c.titulo}</Typography>
              <Typography variant="caption">{relativo(c.ultima_mensagem_em)}{c.documento_contexto_titulo ? `, sobre ${c.documento_contexto_titulo}` : ""}</Typography>
            </Box>
            <Tooltip title="Arquivar conversa"><IconButton size="small" onClick={() => arquivar.mutate(c.id)} aria-label={`Arquivar ${c.titulo}`}><Archive size={16} /></IconButton></Tooltip>
          </Box>
        ))}
      </Paper>
    </Pagina>
  );
}
