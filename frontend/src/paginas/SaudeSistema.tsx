import { useQuery } from "@tanstack/react-query";
import { Alert, Box, Button, Paper, Skeleton, Typography } from "@mui/material";
import { CircleAlert, CircleCheck, RefreshCw, TriangleAlert } from "lucide-react";

import { api } from "../api/cliente";
import { Erro } from "../componentes/comuns";
import { cores } from "../tema";
import { dataHora } from "../util/formatos";

type Situacao = "ok" | "atencao" | "problema";

interface Verificacao {
  codigo: string;
  titulo: string;
  situacao: Situacao;
  resumo: string;
  acao: string;
}

interface Saude {
  situacao: Situacao;
  versao: string;
  verificado_em: string;
  itens: Verificacao[];
}

const ESTILO: Record<Situacao, { rotulo: string; icone: JSX.Element; cor: string; fundo: string; borda: string }> = {
  ok: { rotulo: "Em ordem", icone: <CircleCheck size={20} />, cor: cores.verificado.texto, fundo: cores.verificado.fundo, borda: cores.verificado.borda },
  atencao: { rotulo: "Atenção", icone: <TriangleAlert size={20} />, cor: cores.cautela.texto, fundo: cores.cautela.fundo, borda: cores.cautela.borda },
  problema: { rotulo: "Problema", icone: <CircleAlert size={20} />, cor: cores.erro, fundo: "#FEF2F2", borda: "#FECACA" },
};

/** Saúde do sistema (ADR-023): só estados e números, nunca conteúdo de documentos. */
export default function SaudeSistema() {
  const s = useQuery({ queryKey: ["saude-sistema"], queryFn: () => api<Saude>("/manutencao/saude/"), refetchInterval: 60_000 });
  if (s.isError) return <Erro erro={s.error} />;
  if (!s.data) return <Skeleton variant="rounded" height={320} />;
  const d = s.data;
  const problemas = d.itens.filter((i) => i.situacao === "problema").length;

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Alert
        severity={d.situacao === "ok" ? "success" : d.situacao === "atencao" ? "warning" : "error"}
        action={
          <Button color="inherit" size="small" startIcon={<RefreshCw size={16} />} onClick={() => s.refetch()} disabled={s.isFetching}>
            Verificar agora
          </Button>
        }
      >
        {d.situacao === "ok"
          ? "Tudo em ordem."
          : problemas
            ? `${problemas} ${problemas === 1 ? "item precisa" : "itens precisam"} de ação. Os administradores também recebem aviso por notificação.`
            : "Há pontos de atenção, mas o Nexo está funcionando."}{" "}
        Verificado em {dataHora(d.verificado_em)} · versão {d.versao}.
      </Alert>

      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, display: "grid", gap: 1.5 }} aria-label="Verificações">
        {d.itens.map((i) => {
          const e = ESTILO[i.situacao];
          return (
            <Paper component="li" key={i.codigo} variant="outlined" sx={{ p: 2, display: "flex", gap: 1.5, alignItems: "flex-start", borderColor: i.situacao === "ok" ? undefined : e.borda }}>
              <Box sx={{ color: e.cor, mt: 0.25, flexShrink: 0 }} aria-hidden>
                {e.icone}
              </Box>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Box sx={{ display: "flex", gap: 1, alignItems: "baseline", flexWrap: "wrap" }}>
                  <Typography component="h3" sx={{ fontWeight: 600, fontSize: 15, color: cores.titulo }}>
                    {i.titulo}
                  </Typography>
                  <Typography component="span" sx={{ fontSize: 12, fontWeight: 600, color: e.cor, bgcolor: e.fundo, px: 1, borderRadius: 1 }}>
                    {e.rotulo}
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ mt: 0.5, overflowWrap: "anywhere" }}>
                  {i.resumo}
                </Typography>
                {i.acao && (
                  <Typography variant="body2" sx={{ mt: 0.5, color: cores.textoSecundario, overflowWrap: "anywhere" }}>
                    O que fazer: {i.acao}
                  </Typography>
                )}
              </Box>
            </Paper>
          );
        })}
      </Box>
      <Typography variant="caption" component="p">
        No servidor, o mesmo resultado sai no terminal com manage.py verificar_saude. A tela se atualiza a cada minuto.
      </Typography>
    </Box>
  );
}
