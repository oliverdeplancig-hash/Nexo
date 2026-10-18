import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Box, Button, Paper, Typography } from "@mui/material";
import { Bell } from "lucide-react";

import { api } from "../api/cliente";
import type { Notificacao, Paginado } from "../api/tipos";
import { Cabecalho, EstadoVazio, Erro, Pagina } from "../componentes/comuns";
import { cores } from "../tema";
import { relativo } from "../util/formatos";

export default function Notificacoes() {
  const navegar = useNavigate();
  const queryClient = useQueryClient();
  const lista = useQuery({ queryKey: ["notificacoes", "lista"], queryFn: () => api<Paginado<Notificacao>>("/notificacoes/?tamanho=50") });
  const lerTodas = useMutation({
    mutationFn: () => api("/notificacoes/ler-todas/", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notificacoes"] }),
  });
  async function abrir(n: Notificacao) {
    if (!n.lida) await api(`/notificacoes/${n.id}/ler/`, { method: "POST" });
    queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
    if (n.link) navegar(n.link);
  }
  return (
    <Pagina>
      <Cabecalho titulo="Notificações" acoes={<Button variant="outlined" onClick={() => lerTodas.mutate()}>Marcar todas como lidas</Button>} />
      {lista.isError && <Erro erro={lista.error} />}
      <Paper variant="outlined">
        {lista.data?.results.length === 0 && <EstadoVazio icone={<Bell size={28} />} titulo="Nenhuma notificação" texto="Avisos de processamento de documentos e compartilhamentos aparecerão aqui." />}
        {lista.data?.results.map((n, i) => (
          <Box key={n.id} component="button" onClick={() => abrir(n)} sx={{ all: "unset", boxSizing: "border-box", display: "flex", gap: 1.5, width: "100%", cursor: "pointer", px: 2.5, py: 1.75, borderTop: i ? `1px solid ${cores.bordaSutil}` : 0, bgcolor: n.lida ? "transparent" : cores.primariaFundo, "&:hover": { bgcolor: cores.fundo }, "&:focus-visible": { outline: `2px solid ${cores.primaria}` } }}>
            <Box sx={{ width: 8, height: 8, mt: 1, borderRadius: 99, bgcolor: n.lida ? "transparent" : cores.primaria, flexShrink: 0 }} />
            <Box sx={{ flex: 1 }}>
              <Typography sx={{ fontWeight: n.lida ? 500 : 600, fontSize: 14 }}>{n.titulo}</Typography>
              {n.texto && <Typography variant="body2" sx={{ color: cores.textoSecundario }}>{n.texto}</Typography>}
            </Box>
            <Typography variant="caption" sx={{ whiteSpace: "nowrap" }}>{relativo(n.criada_em)}</Typography>
          </Box>
        ))}
      </Paper>
    </Pagina>
  );
}
