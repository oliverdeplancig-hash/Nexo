import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  Chip,
  InputAdornment,
  MenuItem,
  Pagination,
  Paper,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import {
  CheckCheck,
  FilePlus2,
  MessageSquareWarning,
  PencilLine,
  RotateCcw,
  Search,
} from "lucide-react";

import { api } from "../api/cliente";
import type { Lacuna, Paginado, Regra, ResumoLacunas } from "../api/tipos";
import { MOTIVOS } from "../componentes/AvaliacaoResposta";
import { EstadoVazio, Erro } from "../componentes/comuns";
import { cores, fonteMono } from "../tema";
import { dataHora } from "../util/formatos";

const ORIGEM: Record<string, string> = {
  sem_fontes: "Sem fontes suficientes",
  extrativo: "Só trechos (IA indisponível)",
  deterministico: "Resposta por regra",
  rag: "Gerada pela IA",
};

const pct = (parte: number, total: number) =>
  total ? `${Math.round((parte / total) * 100)}%` : "—";

interface Props {
  regras: Regra[];
  /** Abre o editor de regra; ao salvar, a lacuna é marcada como tratada com a regra. */
  aoEditarRegra: (regra: Partial<Regra>, lacunaId: number) => void;
}

export default function Lacunas({ regras, aoEditarRegra }: Props) {
  const queryClient = useQueryClient();
  const [situacao, setSituacao] = useState("pendentes");
  const [tipo, setTipo] = useState("todas");
  const [termo, setTermo] = useState("");
  const [pagina, setPagina] = useState(1);

  const resumo = useQuery({
    queryKey: ["lacunas", "resumo"],
    queryFn: () => api<ResumoLacunas>("/lacunas/resumo/?dias=30"),
  });
  const lista = useQuery({
    queryKey: ["lacunas", situacao, tipo, termo, pagina],
    queryFn: () =>
      api<Paginado<Lacuna>>(
        `/lacunas/?situacao=${situacao}&tipo=${tipo}&q=${encodeURIComponent(termo)}&page=${pagina}`,
      ),
  });
  const tratar = useMutation({
    mutationFn: ({ id, reabrir }: { id: number; reabrir?: boolean }) =>
      api(`/lacunas/${id}/tratar/`, {
        method: reabrir ? "DELETE" : "POST",
        json: reabrir ? undefined : {},
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lacunas"] }),
  });

  const porCodigo = (codigo: string | null | undefined) =>
    regras.find((r) => r.codigo === codigo);
  const r = resumo.data;
  const total = lista.data?.count ?? 0;

  return (
    <Box>
      {r && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
            gap: 1.5,
            mb: 3,
          }}
        >
          <Indicador
            rotulo="Respostas nos últimos 30 dias"
            valor={String(r.respostas)}
          />
          <Indicador
            rotulo="Respondidas por regra aprovada"
            valor={pct(r.por_origem.deterministico ?? 0, r.respostas)}
            nota={`${r.por_origem.deterministico ?? 0} de ${r.respostas}`}
          />
          <Indicador
            rotulo="Avaliadas como úteis"
            valor={pct(r.uteis, r.avaliadas)}
            nota={
              r.avaliadas
                ? `${r.uteis} de ${r.avaliadas} avaliações`
                : "sem avaliações ainda"
            }
          />
          <Indicador
            rotulo="Lacunas pendentes"
            valor={String(r.lacunas_pendentes)}
            alerta={r.lacunas_pendentes > 0}
          />
        </Box>
      )}

      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 1.5,
          alignItems: "center",
          mb: 2,
        }}
      >
        <ToggleButtonGroup
          size="small"
          exclusive
          value={situacao}
          onChange={(_, v) => v && (setSituacao(v), setPagina(1))}
          aria-label="Situação"
        >
          <ToggleButton value="pendentes">Pendentes</ToggleButton>
          <ToggleButton value="tratadas">Tratadas</ToggleButton>
          <ToggleButton value="todas">Todas</ToggleButton>
        </ToggleButtonGroup>
        <TextField
          select
          size="small"
          label="Tipo"
          value={tipo}
          onChange={(e) => (setTipo(e.target.value), setPagina(1))}
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="todas">Todas as lacunas</MenuItem>
          <MenuItem value="sem_resposta">Sem resposta nos documentos</MenuItem>
          <MenuItem value="negativas">Avaliadas como não úteis</MenuItem>
        </TextField>
        <TextField
          size="small"
          placeholder="Buscar na pergunta"
          value={termo}
          onChange={(e) => (setTermo(e.target.value), setPagina(1))}
          sx={{ flex: 1, minWidth: 200 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search size={16} />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {lista.isError && <Erro erro={lista.error} />}
      {lista.data && lista.data.results.length === 0 && (
        <EstadoVazio
          icone={<CheckCheck size={28} />}
          titulo={
            situacao === "pendentes"
              ? "Nenhuma lacuna pendente"
              : "Nada encontrado"
          }
          texto="Perguntas sem resposta nos documentos e respostas avaliadas como não úteis aparecem aqui."
        />
      )}

      <Box sx={{ display: "grid", gap: 1.5 }}>
        {lista.data?.results.map((l) => {
          const proxima = porCodigo(l.regra_proxima?.codigo);
          const usada = porCodigo(l.regra_usada);
          return (
            <Paper
              key={l.id}
              variant="outlined"
              component="article"
              sx={{ p: 2 }}
            >
              <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
                <Box
                  sx={{
                    color:
                      l.avaliacao?.util === false
                        ? cores.cautela.forte
                        : cores.textoSecundario,
                    pt: 0.25,
                  }}
                >
                  <MessageSquareWarning size={18} />
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    sx={{
                      fontWeight: 600,
                      color: cores.titulo,
                      overflowWrap: "anywhere",
                    }}
                  >
                    “{l.pergunta}”
                  </Typography>
                  <Box
                    sx={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 0.75,
                      mt: 0.75,
                      alignItems: "center",
                    }}
                  >
                    {l.origem && (
                      <Chip
                        size="small"
                        label={ORIGEM[l.origem] ?? l.origem}
                        sx={{ bgcolor: cores.bordaSutil }}
                      />
                    )}
                    {l.avaliacao?.util === false && (
                      <Chip
                        size="small"
                        label={`Não útil: ${MOTIVOS[l.avaliacao.motivo] ?? "sem motivo"}`}
                        sx={{
                          bgcolor: cores.cautela.fundo,
                          color: cores.cautela.texto,
                        }}
                      />
                    )}
                    {l.regra_usada && (
                      <Chip
                        size="small"
                        variant="outlined"
                        label={`Respondida por ${l.regra_usada}`}
                      />
                    )}
                    <Typography variant="caption">
                      {dataHora(l.criada_em)}
                    </Typography>
                  </Box>
                  {l.avaliacao?.comentario && (
                    <Typography
                      variant="body2"
                      sx={{
                        mt: 1,
                        color: cores.textoSecundario,
                        fontStyle: "italic",
                      }}
                    >
                      Comentário: {l.avaliacao.comentario}
                    </Typography>
                  )}
                  {l.regra_proxima && (
                    <Typography
                      variant="body2"
                      sx={{ mt: 1, color: cores.textoSecundario }}
                    >
                      Quase respondida pela regra{" "}
                      <Box
                        component="span"
                        sx={{ fontFamily: fonteMono, fontSize: 13 }}
                      >
                        {l.regra_proxima.codigo}
                      </Box>{" "}
                      — {l.regra_proxima.titulo} (pontuação{" "}
                      {l.regra_proxima.pontuacao.toFixed(2).replace(".", ",")}).
                    </Typography>
                  )}
                  {l.fontes.length > 0 && (
                    <Typography
                      variant="body2"
                      sx={{ mt: 0.5, color: cores.textoSecundario }}
                    >
                      Documentos usados:{" "}
                      {l.fontes.map((f) => f.titulo).join("; ")}
                    </Typography>
                  )}
                  {l.tratamento && (
                    <Typography
                      variant="caption"
                      component="p"
                      sx={{ mt: 1, color: cores.verificado.texto }}
                    >
                      Tratada por {l.tratamento.tratada_por || "—"} em{" "}
                      {dataHora(l.tratamento.tratada_em)}
                      {l.tratamento.regra
                        ? ` com a regra ${l.tratamento.regra}`
                        : ""}
                      {l.tratamento.observacao
                        ? `. ${l.tratamento.observacao}`
                        : ""}
                    </Typography>
                  )}
                </Box>
              </Box>

              <Box
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 1,
                  mt: 1.5,
                  pl: { sm: 3.25 },
                }}
              >
                {!l.tratamento && (
                  <>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<FilePlus2 size={16} />}
                      onClick={() =>
                        aoEditarRegra(
                          {
                            tipo: "faq",
                            titulo: "",
                            frases_exemplo: [l.pergunta],
                            palavras_chave: [],
                            termos_obrigatorios: [],
                            termos_excludentes: [],
                            padroes_regex: [],
                            etapas: [],
                            fontes: [],
                            prioridade: 0,
                          },
                          l.id,
                        )
                      }
                    >
                      Criar regra
                    </Button>
                    {proxima && (
                      <Button
                        size="small"
                        startIcon={<PencilLine size={16} />}
                        onClick={() =>
                          aoEditarRegra(
                            {
                              ...proxima,
                              frases_exemplo: proxima.frases_exemplo.includes(
                                l.pergunta,
                              )
                                ? proxima.frases_exemplo
                                : [...proxima.frases_exemplo, l.pergunta],
                            },
                            l.id,
                          )
                        }
                      >
                        Incluir como exemplo em {proxima.codigo}
                      </Button>
                    )}
                    {usada && (
                      <Button
                        size="small"
                        startIcon={<PencilLine size={16} />}
                        onClick={() => aoEditarRegra(usada, l.id)}
                      >
                        Revisar {usada.codigo}
                      </Button>
                    )}
                    <Button
                      size="small"
                      startIcon={<CheckCheck size={16} />}
                      disabled={tratar.isPending}
                      onClick={() => tratar.mutate({ id: l.id })}
                    >
                      Marcar como tratada
                    </Button>
                  </>
                )}
                {l.tratamento && (
                  <Button
                    size="small"
                    startIcon={<RotateCcw size={16} />}
                    disabled={tratar.isPending}
                    onClick={() => tratar.mutate({ id: l.id, reabrir: true })}
                  >
                    Reabrir
                  </Button>
                )}
              </Box>
            </Paper>
          );
        })}
      </Box>

      {total > 20 && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
          <Pagination
            count={Math.ceil(total / 20)}
            page={pagina}
            onChange={(_, p) => setPagina(p)}
          />
        </Box>
      )}
      <Typography variant="caption" component="p" sx={{ mt: 2 }}>
        Para proteger quem perguntou, a lista não mostra o autor nem o texto da
        resposta. Documentos usados só aparecem se o seu perfil puder
        consultá-los.
      </Typography>
    </Box>
  );
}

function Indicador({
  rotulo,
  valor,
  nota,
  alerta = false,
}: {
  rotulo: string;
  valor: string;
  nota?: string;
  alerta?: boolean;
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        borderColor: alerta ? cores.cautela.borda : undefined,
        bgcolor: alerta ? cores.cautela.fundo : undefined,
      }}
    >
      <Typography variant="caption" component="p">
        {rotulo}
      </Typography>
      <Typography
        sx={{
          fontSize: 26,
          fontWeight: 700,
          color: alerta ? cores.cautela.texto : cores.titulo,
          lineHeight: 1.2,
          mt: 0.5,
        }}
      >
        {valor}
      </Typography>
      {nota && (
        <Typography variant="caption" component="p">
          {nota}
        </Typography>
      )}
    </Paper>
  );
}
