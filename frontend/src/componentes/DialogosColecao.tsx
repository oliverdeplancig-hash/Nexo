import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import { api } from "../api/cliente";
import type { Colecao, Paginado } from "../api/tipos";
import { useAutenticacao } from "../contexto/Autenticacao";

function invalidar(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["colecoes"] });
  queryClient.invalidateQueries({ queryKey: ["documentos"] });
  queryClient.invalidateQueries({ queryKey: ["documento"] });
}

/** Criar (sem `colecao`) ou editar uma coleção. */
export function EditorColecao({ colecao, aoFechar, aoSalvar }: { colecao?: Colecao; aoFechar: () => void; aoSalvar?: (c: Colecao) => void }) {
  const { tem } = useAutenticacao();
  const queryClient = useQueryClient();
  const institucionalPermitida = tem("gerir_colecoes");
  const [f, setF] = useState({
    nome: colecao?.nome ?? "",
    descricao: colecao?.descricao ?? "",
    pessoal: colecao?.pessoal ?? !institucionalPermitida,
  });
  const salvar = useMutation({
    mutationFn: () =>
      api<Colecao>(colecao ? `/colecoes/${colecao.id}/` : "/colecoes/", {
        method: colecao ? "PATCH" : "POST",
        json: colecao ? { nome: f.nome, descricao: f.descricao } : f,
      }),
    onSuccess: (c) => {
      invalidar(queryClient);
      aoSalvar?.(c);
      aoFechar();
    },
  });
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>{colecao ? "Editar coleção" : "Nova coleção"}</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
        {salvar.isError && <Alert severity="error">{(salvar.error as Error).message}</Alert>}
        <TextField id="colecao-nome" label="Nome" value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} autoFocus inputProps={{ maxLength: 150 }} />
        <TextField id="colecao-descricao" label="Descrição" value={f.descricao} onChange={(e) => setF({ ...f, descricao: e.target.value })} multiline minRows={2} />
        {colecao ? (
          <Typography variant="body2" color="text.secondary">
            {colecao.pessoal ? "Coleção pessoal: só você vê." : "Coleção institucional: todos veem (cada um, só os documentos autorizados para si)."}
          </Typography>
        ) : (
          <FormControlLabel
            control={<Switch checked={f.pessoal} disabled={!institucionalPermitida} onChange={(e) => setF({ ...f, pessoal: e.target.checked })} />}
            label={institucionalPermitida ? "Coleção pessoal (só você vê)" : "Coleção pessoal (só você vê). Coleções institucionais são criadas pela gestão documental."}
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button variant="contained" onClick={() => salvar.mutate()} disabled={!f.nome.trim() || salvar.isPending}>
          {colecao ? "Salvar" : "Criar coleção"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** Confirmação de exclusão. Os documentos continuam no repositório. */
export function ExcluirColecao({ colecao, aoFechar, aoExcluir }: { colecao: Colecao; aoFechar: () => void; aoExcluir?: () => void }) {
  const queryClient = useQueryClient();
  const excluir = useMutation({
    mutationFn: () => api(`/colecoes/${colecao.id}/`, { method: "DELETE" }),
    onSuccess: () => {
      invalidar(queryClient);
      aoExcluir?.();
      aoFechar();
    },
  });
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>Excluir a coleção “{colecao.nome}”?</DialogTitle>
      <DialogContent>
        {excluir.isError && <Alert severity="error" sx={{ mb: 2 }}>{(excluir.error as Error).message}</Alert>}
        <DialogContentText>
          Os {colecao.total_documentos ?? 0} documento(s) que você vê nela <strong>não serão apagados</strong>: eles continuam no repositório,
          só deixam de fazer parte desta coleção. Subcoleções dentro dela também são excluídas.
          {!colecao.pessoal && " Esta coleção é institucional: ela some para todos os servidores."}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button color="error" variant="contained" onClick={() => excluir.mutate()} disabled={excluir.isPending}>
          Excluir coleção
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** Coloca um ou mais documentos numa coleção que a pessoa organiza (ou numa nova coleção pessoal). */
export function AdicionarAColecao({ documentos, aoFechar, aoConcluir }: { documentos: number[]; aoFechar: () => void; aoConcluir?: (texto: string) => void }) {
  const queryClient = useQueryClient();
  const colecoes = useQuery({ queryKey: ["colecoes"], queryFn: () => api<Paginado<Colecao>>("/colecoes/?tamanho=100") });
  const editaveis = (colecoes.data?.results ?? []).filter((c) => c.pode_editar);
  const [escolhida, setEscolhida] = useState<string>("");
  const [nova, setNova] = useState(false);

  const adicionar = useMutation({
    mutationFn: (id: number) =>
      api<{ adicionados: number; ignorados: number }>(`/colecoes/${id}/documentos/`, { method: "POST", json: { documentos } }),
    onSuccess: (r, id) => {
      invalidar(queryClient);
      const nome = editaveis.find((c) => c.id === id)?.nome ?? "a coleção";
      aoConcluir?.(`${r.adicionados} documento(s) adicionado(s) a “${nome}”.`);
      aoFechar();
    },
  });

  if (nova) {
    return <EditorColecao aoFechar={() => setNova(false)} aoSalvar={(c) => adicionar.mutate(c.id)} />;
  }
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>Adicionar à coleção</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
        {adicionar.isError && <Alert severity="error">{(adicionar.error as Error).message}</Alert>}
        <Typography variant="body2" color="text.secondary">
          {documentos.length} documento(s) selecionado(s). A coleção não muda quem pode abrir cada documento.
        </Typography>
        {editaveis.length > 0 ? (
          <TextField id="colecao-destino" select label="Coleção" value={escolhida} onChange={(e) => setEscolhida(e.target.value)}>
            {editaveis.map((c) => (
              <MenuItem key={c.id} value={String(c.id)}>
                {c.nome} {c.pessoal ? "(pessoal)" : "(institucional)"}
              </MenuItem>
            ))}
          </TextField>
        ) : (
          colecoes.isSuccess && <Alert severity="info">Você ainda não tem coleções que possa organizar. Crie uma nova.</Alert>
        )}
      </DialogContent>
      <DialogActions sx={{ justifyContent: "space-between" }}>
        <Button onClick={() => setNova(true)}>Nova coleção</Button>
        <span>
          <Button onClick={aoFechar}>Cancelar</Button>
          <Button variant="contained" disabled={!escolhida || adicionar.isPending} onClick={() => adicionar.mutate(Number(escolhida))}>
            Adicionar
          </Button>
        </span>
      </DialogActions>
    </Dialog>
  );
}
