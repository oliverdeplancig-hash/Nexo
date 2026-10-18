import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Box,
  MenuItem,
  Paper,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { api } from "../api/cliente";
import { Cabecalho, ChipVigencia, Erro, Pagina, TituloSecao } from "../componentes/comuns";
import { cores } from "../tema";
import { data, dataHora } from "../util/formatos";

interface Painel {
  dias: number;
  resumo: { total: number; vigentes: number; revogados: number; revisao_atrasada: number; revisao_proxima: number; sem_revisao: number };
  por_setor: { sigla: string; nome: string; vigentes: number; revogados: number; revisao_atrasada: number; sem_revisao: number; ultima_atualizacao: string }[];
  revisoes_atrasadas: { id: number; titulo: string; setor: string; revisar_em: string; dias_atraso: number; responsavel: string | null }[];
  mais_consultados: { id: number; titulo: string; setor: string; vigencia: string; aberturas: number }[];
}

const numero = { fontVariantNumeric: "tabular-nums" } as const;

/** Painel do acervo (ADR-016): números só sobre os documentos que a pessoa pode consultar. */
export default function PainelAcervo() {
  const [dias, setDias] = useState(30);
  const painel = useQuery({ queryKey: ["painel-acervo", dias], queryFn: () => api<Painel>(`/painel/acervo/?dias=${dias}`) });
  const p = painel.data;
  const maxAberturas = Math.max(1, ...(p?.mais_consultados.map((m) => m.aberturas) ?? [1]));

  return (
    <Pagina larga>
      <Cabecalho
        titulo="Painel do acervo"
        descricao="Situação dos documentos que você pode consultar: vigência, revisões e uso. Documentos fora do seu acesso não entram nas contas."
      />
      {painel.isError && <Erro erro={painel.error} />}
      {painel.isLoading && <Skeleton variant="rounded" height={320} />}
      {p && (
        <Box sx={{ display: "grid", gap: 3 }}>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(5, 1fr)" }, gap: 1.5 }}>
            <Indicador rotulo="Vigentes" valor={p.resumo.vigentes} />
            <Indicador rotulo="Revogados" valor={p.resumo.revogados} nota="consulta histórica" />
            <Indicador rotulo="Revisões atrasadas" valor={p.resumo.revisao_atrasada} alerta={p.resumo.revisao_atrasada > 0} />
            <Indicador rotulo="Revisões nos próximos 30 dias" valor={p.resumo.revisao_proxima} />
            <Indicador rotulo="Sem revisão programada" valor={p.resumo.sem_revisao} nota="vigentes sem data de revisão" />
          </Box>

          <Box component="section">
            <TituloSecao>Por setor responsável</TituloSecao>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small" aria-label="Documentos por setor">
                <TableHead>
                  <TableRow>
                    <TableCell>Setor</TableCell>
                    <TableCell align="right">Vigentes</TableCell>
                    <TableCell align="right">Revogados</TableCell>
                    <TableCell align="right">Revisão atrasada</TableCell>
                    <TableCell align="right">Sem revisão</TableCell>
                    <TableCell>Última atualização</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {p.por_setor.map((s) => (
                    <TableRow key={s.sigla} hover>
                      <TableCell>
                        <Typography sx={{ fontWeight: 600, fontSize: 14 }}>{s.sigla}</Typography>
                        <Typography variant="caption">{s.nome}</Typography>
                      </TableCell>
                      <TableCell align="right" sx={numero}>{s.vigentes}</TableCell>
                      <TableCell align="right" sx={numero}>{s.revogados}</TableCell>
                      <TableCell align="right" sx={{ ...numero, color: s.revisao_atrasada ? cores.cautela.texto : undefined, fontWeight: s.revisao_atrasada ? 700 : 400 }}>
                        {s.revisao_atrasada}
                      </TableCell>
                      <TableCell align="right" sx={numero}>{s.sem_revisao}</TableCell>
                      <TableCell>{dataHora(s.ultima_atualizacao)}</TableCell>
                    </TableRow>
                  ))}
                  {p.por_setor.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} sx={{ color: cores.textoSecundario }}>Nenhum documento disponível para o seu perfil.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>

          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 3, alignItems: "start" }}>
            <Box component="section" sx={{ minWidth: 0 }}>
              <TituloSecao>Revisões atrasadas</TituloSecao>
              <Paper variant="outlined">
                {p.revisoes_atrasadas.length === 0 ? (
                  <Typography variant="body2" sx={{ p: 2, color: cores.textoSecundario }}>Nenhuma revisão atrasada.</Typography>
                ) : (
                  p.revisoes_atrasadas.map((d, i) => (
                    <Box key={d.id} sx={{ display: "flex", gap: 1.5, alignItems: "baseline", px: 2, py: 1.25, borderTop: i ? `1px solid ${cores.bordaSutil}` : 0 }}>
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Box component={RouterLink} to={`/documentos/${d.id}`} sx={{ color: cores.titulo, fontWeight: 600, fontSize: 14, textDecoration: "none", "&:hover": { color: cores.primariaHover }, overflowWrap: "anywhere" }}>
                          {d.titulo}
                        </Box>
                        <Typography variant="caption" component="p">
                          {d.setor}, prevista para {data(d.revisar_em)}
                          {d.responsavel ? `, responsável: ${d.responsavel}` : ", sem responsável"}
                        </Typography>
                      </Box>
                      <Typography sx={{ ...numero, fontSize: 13, fontWeight: 700, color: cores.cautela.texto, whiteSpace: "nowrap" }}>
                        {d.dias_atraso} dia{d.dias_atraso === 1 ? "" : "s"}
                      </Typography>
                    </Box>
                  ))
                )}
              </Paper>
            </Box>

            <Box component="section" sx={{ minWidth: 0 }}>
              <TituloSecao
                acao={
                  <TextField select size="small" value={dias} onChange={(e) => setDias(Number(e.target.value))} inputProps={{ "aria-label": "Período" }}>
                    <MenuItem value={7}>7 dias</MenuItem>
                    <MenuItem value={30}>30 dias</MenuItem>
                    <MenuItem value={90}>90 dias</MenuItem>
                  </TextField>
                }
              >
                Mais consultados
              </TituloSecao>
              <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 1.25 }}>
                {p.mais_consultados.length === 0 && (
                  <Typography variant="body2" sx={{ color: cores.textoSecundario }}>Nenhuma abertura registrada no período.</Typography>
                )}
                {p.mais_consultados.map((m) => (
                  <Box key={m.id} sx={{ display: "grid", gap: 0.5 }}>
                    <Box sx={{ display: "flex", gap: 1, alignItems: "baseline" }}>
                      <Box component={RouterLink} to={`/documentos/${m.id}`} sx={{ flex: 1, minWidth: 0, color: cores.titulo, fontSize: 14, textDecoration: "none", overflowWrap: "anywhere", "&:hover": { color: cores.primariaHover } }}>
                        {m.titulo}
                      </Box>
                      <ChipVigencia vigencia={m.vigencia} />
                      <Typography sx={{ ...numero, fontSize: 13, fontWeight: 600 }}>{m.aberturas}</Typography>
                    </Box>
                    <Box sx={{ height: 6, borderRadius: 99, bgcolor: cores.bordaSutil, overflow: "hidden" }} aria-hidden>
                      <Box sx={{ height: "100%", width: `${(m.aberturas / maxAberturas) * 100}%`, bgcolor: cores.primaria, borderRadius: 99 }} />
                    </Box>
                  </Box>
                ))}
                <Typography variant="caption">Aberturas registradas na auditoria. O painel não mostra quem abriu.</Typography>
              </Paper>
            </Box>
          </Box>
        </Box>
      )}
    </Pagina>
  );
}

function Indicador({ rotulo, valor, nota, alerta = false }: { rotulo: string; valor: number; nota?: string; alerta?: boolean }) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: alerta ? cores.cautela.borda : undefined, bgcolor: alerta ? cores.cautela.fundo : undefined }}>
      <Typography variant="caption" component="p">{rotulo}</Typography>
      <Typography sx={{ ...numero, fontSize: 26, fontWeight: 700, lineHeight: 1.2, mt: 0.5, color: alerta ? cores.cautela.texto : cores.titulo }}>{valor}</Typography>
      {nota && <Typography variant="caption" component="p">{nota}</Typography>}
    </Paper>
  );
}
