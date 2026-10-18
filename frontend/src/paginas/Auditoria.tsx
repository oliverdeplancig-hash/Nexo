import { Fragment, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  IconButton,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { ChevronDown, ShieldCheck } from "lucide-react";

import { api, parametros } from "../api/cliente";
import type { EventoAuditoria, Paginado } from "../api/tipos";
import { Cabecalho, Erro, Pagina } from "../componentes/comuns";
import { cores, fonteMono } from "../tema";
import { dataHora } from "../util/formatos";

const COR_RESULTADO: Record<string, { texto: string; fundo: string }> = {
  SUCESSO: { texto: cores.verificado.texto, fundo: cores.verificado.fundo },
  FALHA: { texto: cores.cautela.texto, fundo: cores.cautela.fundo },
  NEGADO: { texto: "#991B1B", fundo: "#FEF2F2" },
};

export default function Auditoria() {
  const [filtros, setFiltros] = useState({ de: "", ate: "", usuario: "", setor: "", tipo: "", resultado: "" });
  const [pagina, setPagina] = useState(1);
  const [aberto, setAberto] = useState<number | null>(null);

  const tipos = useQuery({ queryKey: ["auditoria", "tipos"], queryFn: () => api<{ tipos: { valor: string; rotulo: string }[]; resultados: { valor: string; rotulo: string }[] }>("/auditoria/eventos/tipos/") });
  const eventos = useQuery({
    queryKey: ["auditoria", filtros, pagina],
    queryFn: () => api<Paginado<EventoAuditoria>>(`/auditoria/eventos/${parametros({ ...filtros, page: pagina, tamanho: 25 })}`),
    placeholderData: keepPreviousData,
  });
  const integridade = useQuery({
    queryKey: ["auditoria", "integridade"],
    queryFn: () => api<{ integra: boolean; eventos_verificados: number; primeiro_evento_invalido: number | null }>("/auditoria/eventos/integridade/"),
    enabled: false,
  });

  const mudar = (k: keyof typeof filtros, v: string) => {
    setFiltros({ ...filtros, [k]: v });
    setPagina(1);
  };

  return (
    <Pagina larga>
      <Cabecalho
        titulo="Auditoria e trilha de conformidade"
        descricao="Eventos de acesso, alterações e consultas. O conteúdo de documentos e conversas não é registrado na trilha."
        acoes={<Button variant="outlined" startIcon={<ShieldCheck size={16} />} onClick={() => integridade.refetch()} disabled={integridade.isFetching}>{integridade.isFetching ? "Verificando…" : "Verificar integridade"}</Button>}
      />
      {integridade.data && (
        <Alert severity={integridade.data.integra ? "success" : "error"} sx={{ mb: 2 }}>
          {integridade.data.integra
            ? `Trilha íntegra: ${integridade.data.eventos_verificados} eventos verificados pelo encadeamento de hashes.`
            : `Inconsistência detectada a partir do evento ${integridade.data.primeiro_evento_invalido}. Acione a equipe de segurança.`}
        </Alert>
      )}

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(6, 1fr)" }, gap: 1.25, mb: 2 }}>
        <TextField size="small" type="date" label="De" InputLabelProps={{ shrink: true }} value={filtros.de} onChange={(e) => mudar("de", e.target.value)} />
        <TextField size="small" type="date" label="Até" InputLabelProps={{ shrink: true }} value={filtros.ate} onChange={(e) => mudar("ate", e.target.value)} />
        <TextField size="small" label="Usuário" value={filtros.usuario} onChange={(e) => mudar("usuario", e.target.value)} />
        <TextField size="small" label="Setor (sigla)" value={filtros.setor} onChange={(e) => mudar("setor", e.target.value.toUpperCase())} />
        <TextField select size="small" label="Tipo de evento" value={filtros.tipo} onChange={(e) => mudar("tipo", e.target.value)}>
          <MenuItem value="">Todos</MenuItem>
          {(tipos.data?.tipos ?? []).map((t) => <MenuItem key={t.valor} value={t.valor}>{t.rotulo}</MenuItem>)}
        </TextField>
        <TextField select size="small" label="Resultado" value={filtros.resultado} onChange={(e) => mudar("resultado", e.target.value)}>
          <MenuItem value="">Todos</MenuItem>
          {(tipos.data?.resultados ?? []).map((t) => <MenuItem key={t.valor} value={t.valor}>{t.rotulo}</MenuItem>)}
        </TextField>
      </Box>

      {eventos.isError && <Erro erro={eventos.error} />}
      <TableContainer component={Paper} variant="outlined" sx={{ opacity: eventos.isFetching ? 0.7 : 1 }}>
        <Table size="small" aria-label="Eventos de auditoria">
          <TableHead>
            <TableRow>
              <TableCell>Data e hora</TableCell>
              <TableCell>Evento</TableCell>
              <TableCell>Usuário</TableCell>
              <TableCell>Setor</TableCell>
              <TableCell>Objeto</TableCell>
              <TableCell>Resultado</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {eventos.data?.results.map((e) => (
              <Fragment key={e.id}>
                <TableRow hover>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>{dataHora(e.ocorrido_em)}</TableCell>
                  <TableCell>{e.tipo_rotulo}</TableCell>
                  <TableCell>{e.usuario_login || "—"}</TableCell>
                  <TableCell>{e.setor_sigla || "—"}</TableCell>
                  <TableCell sx={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.objeto_descricao || "—"}</TableCell>
                  <TableCell>
                    <Chip size="small" label={e.resultado.charAt(0) + e.resultado.slice(1).toLowerCase()} sx={{ color: COR_RESULTADO[e.resultado].texto, bgcolor: COR_RESULTADO[e.resultado].fundo }} />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => setAberto(aberto === e.id ? null : e.id)} aria-label="Detalhes" aria-expanded={aberto === e.id}>
                      <ChevronDown size={16} style={{ transform: aberto === e.id ? "rotate(180deg)" : undefined }} />
                    </IconButton>
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell colSpan={7} sx={{ py: 0, borderBottom: aberto === e.id ? undefined : 0 }}>
                    <Collapse in={aberto === e.id} unmountOnExit>
                      <Box sx={{ py: 1.5, display: "grid", gap: 0.5 }}>
                        <Typography variant="caption">IP: {e.ip ?? "—"}; objeto: {e.objeto_tipo} {e.objeto_id}</Typography>
                        <Typography sx={{ fontFamily: fonteMono, fontSize: 12, whiteSpace: "pre-wrap", color: cores.textoSecundario }}>{JSON.stringify(e.detalhes, null, 2)}</Typography>
                        <Typography sx={{ fontFamily: fonteMono, fontSize: 11, color: "#94A3B8" }}>hash {e.hash}</Typography>
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {eventos.data && (
        <TablePagination component="div" count={eventos.data.count} page={pagina - 1} rowsPerPage={25} rowsPerPageOptions={[25]} onPageChange={(_, p) => setPagina(p + 1)} labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`} />
      )}
    </Pagina>
  );
}
