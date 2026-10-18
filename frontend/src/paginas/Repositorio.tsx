import { useMemo, useState } from "react";
import { Link as RouterLink, useNavigate, useSearchParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  Checkbox,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Skeleton,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  Tabs,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { Download, Eye, FileUp, FolderPlus, LayoutGrid, Rows3, Search, Star } from "lucide-react";

import { api, parametros } from "../api/cliente";
import type { DocumentoLista, Paginado, Setor } from "../api/tipos";
import { Cabecalho, ChipClassificacao, EstadoVazio, Erro, IconeArquivo, Pagina } from "../componentes/comuns";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";
import { data } from "../util/formatos";

const ABAS = [
  { valor: "todos", rotulo: "Todos os autorizados" },
  { valor: "meus", rotulo: "Meus documentos" },
  { valor: "favoritos", rotulo: "Favoritos" },
  { valor: "recentes", rotulo: "Recentes" },
  { valor: "compartilhados", rotulo: "Compartilhados comigo" },
];

export default function Repositorio() {
  const [params, setParams] = useSearchParams();
  const navegar = useNavigate();
  const queryClient = useQueryClient();
  const { tem } = useAutenticacao();
  const celular = useMediaQuery("(max-width:767.95px)");
  const [visao, setVisao] = useState<"tabela" | "grade">("tabela");
  const [selecionados, setSelecionados] = useState<number[]>([]);
  const [termo, setTermo] = useState(params.get("q") ?? "");

  const aba = params.get("aba") ?? "todos";
  const pagina = Number(params.get("pagina") ?? "1");
  const ordem = params.get("ordem") ?? "-atualizacao";
  const filtros = { aba, q: params.get("q"), tipo: params.get("tipo"), setor: params.get("setor"), de: params.get("de"), ate: params.get("ate"), ordem, page: pagina };

  const setores = useQuery({ queryKey: ["setores", "todos"], queryFn: () => api<Paginado<Setor>>("/setores/?tamanho=100") });
  const consulta = useQuery({
    queryKey: ["documentos", filtros],
    queryFn: () => api<Paginado<DocumentoLista>>(`/documentos/${parametros(filtros)}`),
    placeholderData: keepPreviousData,
  });

  const favoritar = useMutation({
    mutationFn: ({ id, valor }: { id: number; valor: boolean }) => api(`/documentos/${id}/favorito/`, { method: valor ? "POST" : "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documentos"] }),
  });

  function mudar(chave: string, valor: string | null) {
    const novo = new URLSearchParams(params);
    if (valor) novo.set(chave, valor);
    else novo.delete(chave);
    if (chave !== "pagina") novo.delete("pagina");
    setParams(novo);
    setSelecionados([]);
  }

  function ordenar(campo: string) {
    mudar("ordem", ordem === campo ? `-${campo}` : campo);
  }

  const docs = consulta.data?.results ?? [];
  const todosSelecionados = docs.length > 0 && docs.every((d) => selecionados.includes(d.id));
  const exibicao = celular ? "grade" : visao;

  const colunasOrdenaveis = useMemo(
    () => ({ titulo: "Nome", tipo: "Tipo", setor: "Setor responsável", atualizacao: "Atualização" }),
    [],
  );

  return (
    <Pagina larga>
      <Cabecalho
        titulo="Repositório documental"
        descricao="Consulte e organize os documentos institucionais disponíveis para seu perfil."
        acoes={
          <>
            {tem("importar_documentos") && (
              <Button variant="contained" startIcon={<FileUp size={16} />} onClick={() => navegar("/importacao")}>
                Adicionar documento
              </Button>
            )}
            <Button variant="outlined" startIcon={<FolderPlus size={16} />} onClick={() => navegar("/colecoes")}>
              Nova pasta ou coleção
            </Button>
          </>
        }
      />

      <Tabs
        value={aba}
        onChange={(_, v) => mudar("aba", v === "todos" ? null : v)}
        variant="scrollable"
        allowScrollButtonsMobile
        sx={{ borderBottom: `1px solid ${cores.borda}`, mb: 2, minHeight: 40, "& .MuiTab-root": { minHeight: 40, textTransform: "none", fontWeight: 500 } }}
      >
        {ABAS.map((a) => (
          <Tab key={a.valor} value={a.valor} label={a.rotulo} />
        ))}
      </Tabs>

      <Box sx={{ display: "flex", gap: 1.25, flexWrap: "wrap", alignItems: "center", mb: 2 }}>
        <Box component="form" onSubmit={(e) => { e.preventDefault(); mudar("q", termo.trim() || null); }} sx={{ flex: "1 1 280px" }}>
          <TextField
            size="small"
            fullWidth
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="Buscar por nome ou número de referência"
            InputProps={{ startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment> }}
            inputProps={{ "aria-label": "Buscar por nome" }}
          />
        </Box>
        <TextField select size="small" label="Tipo" value={params.get("tipo") ?? ""} onChange={(e) => mudar("tipo", e.target.value || null)} sx={{ minWidth: 120 }}>
          <MenuItem value="">Todos</MenuItem>
          {["pdf", "docx", "md", "txt", "html"].map((t) => (
            <MenuItem key={t} value={t}>{t.toUpperCase()}</MenuItem>
          ))}
        </TextField>
        <TextField select size="small" label="Setor" value={params.get("setor") ?? ""} onChange={(e) => mudar("setor", e.target.value || null)} sx={{ minWidth: 160 }}>
          <MenuItem value="">Todos</MenuItem>
          {(setores.data?.results ?? []).map((s) => (
            <MenuItem key={s.id} value={String(s.id)}>{s.sigla}</MenuItem>
          ))}
        </TextField>
        <TextField size="small" type="date" label="Atualizado desde" InputLabelProps={{ shrink: true }} value={params.get("de") ?? ""} onChange={(e) => mudar("de", e.target.value || null)} />
        <Button variant="text" onClick={() => navegar(`/busca${termo ? `?q=${encodeURIComponent(termo)}` : ""}`)}>
          Pesquisar no conteúdo
        </Button>
        {!celular && (
          <ToggleButtonGroup size="small" exclusive value={visao} onChange={(_, v) => v && setVisao(v)} aria-label="Modo de exibição" sx={{ ml: "auto" }}>
            <ToggleButton value="tabela" aria-label="Tabela"><Rows3 size={16} /></ToggleButton>
            <ToggleButton value="grade" aria-label="Grade"><LayoutGrid size={16} /></ToggleButton>
          </ToggleButtonGroup>
        )}
      </Box>

      {selecionados.length > 0 && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, p: 1, mb: 1.5, borderRadius: 2, bgcolor: cores.primariaFundo, border: `1px solid ${cores.primariaBorda}` }}>
          <Typography variant="body2" sx={{ fontWeight: 600, px: 1 }}>
            {selecionados.length} selecionado{selecionados.length > 1 ? "s" : ""}
          </Typography>
          <Button size="small" startIcon={<Star size={14} />} onClick={() => { selecionados.forEach((id) => favoritar.mutate({ id, valor: true })); setSelecionados([]); }}>
            Adicionar aos favoritos
          </Button>
          <Button size="small" onClick={() => setSelecionados([])}>Limpar seleção</Button>
        </Box>
      )}

      {consulta.isError && <Erro erro={consulta.error} />}

      {consulta.isLoading ? (
        <Skeleton variant="rounded" height={320} />
      ) : !docs.length ? (
        <Paper variant="outlined">
          <EstadoVazio
            icone={<Search size={32} />}
            titulo={params.get("q") ? "Nenhum documento com esse nome" : "Nenhum documento nesta lista"}
            texto={params.get("q") ? "Tente outro termo ou pesquise no conteúdo dos documentos." : "Os documentos autorizados para o seu perfil aparecerão aqui."}
            acao={params.get("q") ? <Button onClick={() => navegar(`/busca?q=${encodeURIComponent(params.get("q") ?? "")}`)}>Pesquisar no conteúdo</Button> : undefined}
          />
        </Paper>
      ) : exibicao === "tabela" ? (
        <TableContainer component={Paper} variant="outlined" sx={{ opacity: consulta.isFetching ? 0.7 : 1 }}>
          <Table size="small" aria-label="Documentos">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    size="small"
                    checked={todosSelecionados}
                    indeterminate={!todosSelecionados && selecionados.length > 0}
                    onChange={() => setSelecionados(todosSelecionados ? [] : docs.map((d) => d.id))}
                    inputProps={{ "aria-label": "Selecionar todos" }}
                  />
                </TableCell>
                {Object.entries(colunasOrdenaveis).map(([campo, rotulo]) => (
                  <TableCell key={campo} sortDirection={ordem.replace("-", "") === campo ? (ordem.startsWith("-") ? "desc" : "asc") : false}>
                    <TableSortLabel active={ordem.replace("-", "") === campo} direction={ordem.startsWith("-") ? "desc" : "asc"} onClick={() => ordenar(campo)}>
                      {rotulo}
                    </TableSortLabel>
                  </TableCell>
                ))}
                <TableCell>Categoria</TableCell>
                <TableCell>Responsável</TableCell>
                <TableCell align="right">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {docs.map((d) => (
                <TableRow key={d.id} hover selected={selecionados.includes(d.id)}>
                  <TableCell padding="checkbox">
                    <Checkbox
                      size="small"
                      checked={selecionados.includes(d.id)}
                      onChange={() => setSelecionados((s) => (s.includes(d.id) ? s.filter((x) => x !== d.id) : [...s, d.id]))}
                      inputProps={{ "aria-label": `Selecionar ${d.titulo}` }}
                    />
                  </TableCell>
                  <TableCell sx={{ maxWidth: 360 }}>
                    <Box component={RouterLink} to={`/documentos/${d.id}`} sx={{ display: "flex", alignItems: "center", gap: 1, color: cores.titulo, textDecoration: "none", fontWeight: 500, "&:hover": { color: cores.primariaHover } }}>
                      <IconeArquivo tipo={d.tipo_arquivo} />
                      <Box component="span" sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.titulo}</Box>
                    </Box>
                    {d.classificacao && d.classificacao !== "geral" && <Box sx={{ mt: 0.5 }}><ChipClassificacao valor={d.classificacao} /></Box>}
                  </TableCell>
                  <TableCell>{d.tipo_arquivo.toUpperCase()}</TableCell>
                  <TableCell>{d.setor_responsavel.sigla}</TableCell>
                  <TableCell>{data(d.atualizado_em)}</TableCell>
                  <TableCell>{d.categoria ?? "—"}</TableCell>
                  <TableCell>{d.responsavel ?? "—"}</TableCell>
                  <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                    <AcoesDocumento d={d} aoFavoritar={(valor) => favoritar.mutate({ id: d.id, valor })} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(3, 1fr)" }, gap: 1.5 }}>
          {docs.map((d) => (
            <Paper key={d.id} variant="outlined" sx={{ p: 2, display: "flex", flexDirection: "column", gap: 1 }}>
              <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
                <IconeArquivo tipo={d.tipo_arquivo} tamanho={22} />
                <Typography component={RouterLink} to={`/documentos/${d.id}`} sx={{ flex: 1, fontWeight: 600, fontSize: 15, color: cores.titulo, textDecoration: "none" }}>
                  {d.titulo}
                </Typography>
              </Box>
              <Typography variant="caption">
                {d.setor_responsavel.sigla}, {d.categoria ?? "sem categoria"}, atualizado em {data(d.atualizado_em)}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <ChipClassificacao valor={d.classificacao} />
                <AcoesDocumento d={d} aoFavoritar={(valor) => favoritar.mutate({ id: d.id, valor })} />
              </Box>
            </Paper>
          ))}
        </Box>
      )}

      {consulta.data && consulta.data.count > 20 && (
        <TablePagination
          component="div"
          count={consulta.data.count}
          page={pagina - 1}
          rowsPerPage={20}
          rowsPerPageOptions={[20]}
          onPageChange={(_, p) => mudar("pagina", String(p + 1))}
          labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`}
        />
      )}
    </Pagina>
  );
}

function AcoesDocumento({ d, aoFavoritar }: { d: DocumentoLista; aoFavoritar: (v: boolean) => void }) {
  const navegar = useNavigate();
  return (
    <Box sx={{ display: "inline-flex" }}>
      {d.acoes_permitidas.includes("visualizar") && (
        <Tooltip title="Visualizar">
          <IconButton size="small" onClick={() => navegar(`/documentos/${d.id}`)} aria-label={`Visualizar ${d.titulo}`}>
            <Eye size={16} />
          </IconButton>
        </Tooltip>
      )}
      {d.acoes_permitidas.includes("baixar") && (
        <Tooltip title="Baixar">
          <IconButton size="small" component="a" href={`/api/v1/documentos/${d.id}/arquivo/?download=1`} aria-label={`Baixar ${d.titulo}`}>
            <Download size={16} />
          </IconButton>
        </Tooltip>
      )}
      <Tooltip title={d.favorito ? "Remover dos favoritos" : "Adicionar aos favoritos"}>
        <IconButton size="small" onClick={() => aoFavoritar(!d.favorito)} aria-pressed={d.favorito} aria-label="Favorito">
          <Star size={16} fill={d.favorito ? "#F59E0B" : "none"} color={d.favorito ? "#F59E0B" : "currentColor"} />
        </IconButton>
      </Tooltip>
    </Box>
  );
}
