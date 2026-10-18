import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Autocomplete, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField, Typography } from "@mui/material";

import { api } from "../api/cliente";
import type { DocumentoDetalhe, DocumentoLista, Paginado } from "../api/tipos";

const isoHoje = () => new Date().toLocaleDateString("sv-SE");
const isoDaquiAUmAno = () => {
  const d = new Date();
  d.setFullYear(d.getFullYear() + 1);
  return d.toLocaleDateString("sv-SE");
};

function useAtualizar(id: number) {
  const queryClient = useQueryClient();
  return (d: DocumentoDetalhe) => {
    queryClient.setQueryData(["documento", String(id)], d);
    queryClient.invalidateQueries({ queryKey: ["documento"] });
    queryClient.invalidateQueries({ queryKey: ["documentos"] });
  };
}

/** Revogar: o documento continua consultável, mas sai do assistente e da busca padrão (ADR-015). */
export function DialogoRevogar({ documento, aoFechar }: { documento: DocumentoDetalhe; aoFechar: () => void }) {
  const atualizar = useAtualizar(documento.id);
  const [motivo, setMotivo] = useState("");
  const [data, setData] = useState(isoHoje());
  const [termo, setTermo] = useState("");
  const [substituto, setSubstituto] = useState<DocumentoLista | null>(null);
  const opcoes = useQuery({
    queryKey: ["documentos", "substituto", termo],
    queryFn: () => api<Paginado<DocumentoLista>>(`/documentos/?q=${encodeURIComponent(termo)}&vigencia=vigente&tamanho=10`),
  });
  const revogar = useMutation({
    mutationFn: () =>
      api<DocumentoDetalhe>(`/documentos/${documento.id}/revogar/`, {
        method: "POST",
        json: { motivo, revogado_em: data, substituido_por: substituto?.id ?? null },
      }),
    onSuccess: (d) => {
      atualizar(d);
      aoFechar();
    },
  });
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="sm">
      <DialogTitle>Revogar documento</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
        {revogar.isError && <Alert severity="error">{(revogar.error as Error).message}</Alert>}
        <Typography variant="body2" color="text.secondary">
          O documento continua no repositório para consulta histórica, marcado como revogado. O assistente deixa de usá-lo e ele sai da
          busca padrão.
        </Typography>
        <TextField
          id="revogar-motivo"
          label="Motivo"
          required
          value={motivo}
          onChange={(e) => setMotivo(e.target.value.slice(0, 500))}
          placeholder="Ex.: revogado pela norma de 2026"
          multiline
          minRows={2}
          autoFocus
        />
        <TextField id="revogar-data" label="Revogado em" type="date" value={data} onChange={(e) => setData(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ maxWidth: 220 }} />
        <Autocomplete
          options={(opcoes.data?.results ?? []).filter((d) => d.id !== documento.id)}
          getOptionLabel={(o) => o.titulo}
          filterOptions={(x) => x}
          onInputChange={(_, v) => setTermo(v)}
          value={substituto}
          onChange={(_, v) => setSubstituto(v)}
          renderInput={(p) => <TextField {...p} id="revogar-substituto" label="Substituído por (opcional)" helperText="Documento vigente que passa a valer no lugar deste." />}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button color="error" variant="contained" disabled={!motivo.trim() || revogar.isPending} onClick={() => revogar.mutate()}>
          Revogar
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** Registra a revisão de hoje e agenda a próxima. */
export function DialogoRevisao({ documento, aoFechar }: { documento: DocumentoDetalhe; aoFechar: () => void }) {
  const atualizar = useAtualizar(documento.id);
  const [proxima, setProxima] = useState(isoDaquiAUmAno());
  const revisar = useMutation({
    mutationFn: () => api<DocumentoDetalhe>(`/documentos/${documento.id}/revisao/`, { method: "POST", json: { proxima: proxima || null } }),
    onSuccess: (d) => {
      atualizar(d);
      aoFechar();
    },
  });
  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>Registrar revisão</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: "8px !important" }}>
        {revisar.isError && <Alert severity="error">{(revisar.error as Error).message}</Alert>}
        <Typography variant="body2" color="text.secondary">
          Confirme que você conferiu o documento hoje e que ele continua válido. Se ele mudou, use “Enviar nova versão”; se deixou de
          valer, use “Revogar”.
        </Typography>
        <TextField
          id="revisao-proxima"
          label="Próxima revisão"
          type="date"
          value={proxima}
          onChange={(e) => setProxima(e.target.value)}
          InputLabelProps={{ shrink: true }}
          helperText="Deixe em branco se o documento não precisa de revisão periódica."
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button variant="contained" disabled={revisar.isPending} onClick={() => revisar.mutate()}>
          Registrar revisão
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** Desfaz uma revogação feita por engano. */
export function useRestabelecer(documento: DocumentoDetalhe) {
  const atualizar = useAtualizar(documento.id);
  return useMutation({
    mutationFn: () => api<DocumentoDetalhe>(`/documentos/${documento.id}/restabelecer/`, { method: "POST" }),
    onSuccess: atualizar,
  });
}
