import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Box, Button, IconButton, Paper, Skeleton, Tooltip, Typography } from "@mui/material";
import { Folder, FolderLock, Pencil, Plus, Trash2 } from "lucide-react";

import { api } from "../api/cliente";
import type { Colecao, Paginado } from "../api/tipos";
import { Cabecalho, EstadoVazio, Erro, Pagina, TituloSecao } from "../componentes/comuns";
import { EditorColecao, ExcluirColecao } from "../componentes/DialogosColecao";
import { cores } from "../tema";
import { dataHora } from "../util/formatos";

export default function Colecoes() {
  const [editando, setEditando] = useState<Colecao | "nova" | null>(null);
  const [excluindo, setExcluindo] = useState<Colecao | null>(null);
  const colecoes = useQuery({ queryKey: ["colecoes"], queryFn: () => api<Paginado<Colecao>>("/colecoes/?tamanho=100") });
  const todas = colecoes.data?.results ?? [];
  const pessoais = todas.filter((c) => c.pessoal);
  const institucionais = todas.filter((c) => !c.pessoal);

  const grade = (lista: Colecao[]) => (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(3, 1fr)" }, gap: 1.5 }}>
      {lista.map((c) => (
        <Paper key={c.id} variant="outlined" sx={{ display: "flex", alignItems: "flex-start", "&:hover": { borderColor: cores.primariaBorda } }}>
          <Box
            component={RouterLink}
            to={`/repositorio?colecao=${c.id}`}
            sx={{ flex: 1, minWidth: 0, p: 2, display: "flex", gap: 1.5, color: "inherit", textDecoration: "none", borderRadius: 1 }}
          >
            {c.pessoal ? <FolderLock size={22} color={cores.textoSecundario} /> : <Folder size={22} color={cores.primaria} />}
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ fontWeight: 600, fontSize: 15, overflowWrap: "anywhere" }}>{c.nome}</Typography>
              {c.descricao && <Typography variant="body2" sx={{ color: cores.textoSecundario, overflowWrap: "anywhere" }}>{c.descricao}</Typography>}
              <Typography variant="caption" component="p">
                {c.total_documentos ?? 0} documento(s) visíveis para você
              </Typography>
              <Typography variant="caption" component="p">
                Atualizada em {dataHora(c.atualizado_em)}
                {!c.pessoal && c.criada_por_nome ? `, criada por ${c.criada_por_nome}` : ""}
              </Typography>
            </Box>
          </Box>
          {c.pode_editar && (
            <Box sx={{ display: "flex", flexDirection: "column", p: 0.5 }}>
              <Tooltip title="Editar">
                <IconButton size="small" onClick={() => setEditando(c)} aria-label={`Editar ${c.nome}`}>
                  <Pencil size={16} />
                </IconButton>
              </Tooltip>
              <Tooltip title="Excluir">
                <IconButton size="small" onClick={() => setExcluindo(c)} aria-label={`Excluir ${c.nome}`}>
                  <Trash2 size={16} />
                </IconButton>
              </Tooltip>
            </Box>
          )}
        </Paper>
      ))}
    </Box>
  );

  return (
    <Pagina>
      <Cabecalho
        titulo="Pastas e coleções"
        descricao="Agrupamentos de documentos. Uma coleção não altera as permissões: cada servidor vê apenas os documentos autorizados para ele."
        acoes={<Button variant="contained" startIcon={<Plus size={16} />} onClick={() => setEditando("nova")}>Nova coleção</Button>}
      />
      {colecoes.isError && <Erro erro={colecoes.error} />}
      {colecoes.isLoading && <Skeleton variant="rounded" height={160} />}
      {colecoes.isSuccess && todas.length === 0 && (
        <Paper variant="outlined">
          <EstadoVazio
            icone={<Folder size={28} />}
            titulo="Nenhuma coleção ainda"
            texto="Crie uma coleção e, no repositório, selecione documentos e use “Adicionar à coleção”."
          />
        </Paper>
      )}
      {pessoais.length > 0 && (
        <Box component="section" sx={{ mb: 3 }}>
          <TituloSecao>Minhas coleções pessoais</TituloSecao>
          {grade(pessoais)}
        </Box>
      )}
      {institucionais.length > 0 && (
        <Box component="section">
          <TituloSecao>Coleções institucionais</TituloSecao>
          {grade(institucionais)}
        </Box>
      )}
      <Typography variant="caption" component="p" sx={{ mt: 2 }}>
        Para colocar documentos numa coleção, selecione-os no repositório (ou abra um documento) e use “Adicionar à coleção”.
      </Typography>

      {editando && <EditorColecao colecao={editando === "nova" ? undefined : editando} aoFechar={() => setEditando(null)} />}
      {excluindo && <ExcluirColecao colecao={excluindo} aoFechar={() => setExcluindo(null)} />}
    </Pagina>
  );
}
