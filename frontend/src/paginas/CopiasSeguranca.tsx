import { useQuery } from "@tanstack/react-query";
import { Alert, Box, Chip, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { ShieldCheck, ShieldAlert } from "lucide-react";

import { api } from "../api/cliente";
import { Erro } from "../componentes/comuns";
import { cores, fonteMono } from "../tema";
import { dataHora } from "../util/formatos";

interface Copia {
  arquivo: string;
  criada_em?: string;
  bytes: number;
  cifrada: boolean;
  rotulo?: string;
  arquivos?: number;
  contagens?: { documentos: number; usuarios: number; eventos_auditoria: number };
}

interface Situacao {
  pasta: string;
  senha_configurada: boolean;
  retencao: number;
  alerta_horas: number;
  horas_desde_ultima: number | null;
  em_dia: boolean;
  copias: Copia[];
}

function tamanho(n: number) {
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) {
    n /= 1024;
    i++;
  }
  return `${i ? n.toFixed(1).replace(".", ",") : n} ${u[i]}`;
}

/** Situação das cópias de segurança. Criar e restaurar são feitos no servidor (docs/architecture/copia-de-seguranca.md). */
export default function CopiasSeguranca() {
  const s = useQuery({ queryKey: ["copias"], queryFn: () => api<Situacao>("/manutencao/copias/") });
  if (s.isError) return <Erro erro={s.error} />;
  if (!s.data) return null;
  const d = s.data;
  const ultima = d.copias.find((c) => (c.rotulo ?? "nexo") === "nexo");

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Alert
        severity={d.em_dia ? "success" : "warning"}
        icon={d.em_dia ? <ShieldCheck size={20} /> : <ShieldAlert size={20} />}
      >
        {d.em_dia && ultima
          ? `Última cópia em ${dataHora(ultima.criada_em ?? null)} (há ${String(d.horas_desde_ultima).replace(".", ",")} h).`
          : d.horas_desde_ultima === null
            ? "Nenhuma cópia de segurança foi feita ainda. Agende a cópia diária no servidor."
            : `A última cópia tem ${String(d.horas_desde_ultima).replace(".", ",")} h — mais do que o limite de ${d.alerta_horas} h. Verifique o agendamento.`}
      </Alert>
      {!d.senha_configurada && (
        <Alert severity="warning">
          As cópias estão sendo feitas <strong>sem cifra</strong>. Defina NEXO_BACKUP_SENHA no servidor e guarde a senha fora dele.
        </Alert>
      )}

      <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
        <Typography variant="body2" sx={{ color: cores.textoSecundario }}>
          Pasta: <Box component="span" sx={{ fontFamily: fonteMono, fontSize: 13, color: cores.texto, overflowWrap: "anywhere" }}>{d.pasta}</Box>
        </Typography>
        <Typography variant="body2" sx={{ color: cores.textoSecundario }}>
          Mantém as {d.retencao} cópias diárias mais recentes
        </Typography>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" aria-label="Cópias de segurança">
          <TableHead>
            <TableRow>
              <TableCell>Criada em</TableCell>
              <TableCell>Tipo</TableCell>
              <TableCell>Conteúdo</TableCell>
              <TableCell align="right">Tamanho</TableCell>
              <TableCell>Proteção</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {d.copias.map((c) => (
              <TableRow key={c.arquivo} hover>
                <TableCell>
                  <Typography sx={{ fontSize: 14 }}>{c.criada_em ? dataHora(c.criada_em) : "—"}</Typography>
                  <Typography sx={{ fontFamily: fonteMono, fontSize: 12, color: cores.textoSecundario }}>{c.arquivo}</Typography>
                </TableCell>
                <TableCell>{c.rotulo === "nexo-antes-restauracao" ? "Antes de restaurar" : "Diária"}</TableCell>
                <TableCell>
                  {c.contagens ? `${c.contagens.documentos} documentos, ${c.arquivos ?? 0} arquivos, ${c.contagens.usuarios} usuários` : "—"}
                </TableCell>
                <TableCell align="right">{tamanho(c.bytes)}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={c.cifrada ? "Cifrada" : "Sem cifra"}
                    sx={c.cifrada ? { bgcolor: cores.verificado.fundo, color: cores.verificado.texto } : { bgcolor: cores.cautela.fundo, color: cores.cautela.texto }}
                  />
                </TableCell>
              </TableRow>
            ))}
            {d.copias.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} sx={{ color: cores.textoSecundario }}>
                  Nenhuma cópia nesta pasta.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <Typography variant="caption" component="p">
        A restauração substitui todo o banco e os arquivos e é feita no servidor, com o Nexo parado, pelo comando
        copia_seguranca restaurar (no Windows: scripts\restaurar-windows.cmd). Antes de restaurar, o estado atual é copiado automaticamente.
      </Typography>
    </Box>
  );
}
