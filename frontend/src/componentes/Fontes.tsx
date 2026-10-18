import { useNavigate } from "react-router-dom";
import { Box, Button, Typography } from "@mui/material";
import { ExternalLink, Lock } from "lucide-react";

import type { Fonte, SetorSugerido } from "../api/tipos";
import { cores, fonteMono } from "../tema";
import { data } from "../util/formatos";
import { IconeArquivo } from "./comuns";

export function CartaoFonte({ fonte, compacto = false }: { fonte: Fonte; compacto?: boolean }) {
  const navegar = useNavigate();
  const local = [fonte.pagina ? `p. ${fonte.pagina}` : null, fonte.secao || null].filter(Boolean).join(", ");
  return (
    <Box
      component="article"
      sx={{ border: `1px solid ${cores.borda}`, borderRadius: 2, p: 1.75, bgcolor: cores.superficie, display: "flex", flexDirection: "column", gap: 1 }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        {fonte.numero !== undefined && (
          <Box
            component="span"
            sx={{
              fontFamily: fonteMono,
              fontSize: 11,
              px: 0.75,
              py: 0.1,
              borderRadius: 0.5,
              bgcolor: fonte.citada ? cores.primariaFundo : cores.bordaSutil,
              color: fonte.citada ? cores.primariaHover : cores.textoSecundario,
              border: `1px solid ${fonte.citada ? cores.primariaBorda : cores.borda}`,
            }}
            title={fonte.citada ? "Citada na resposta" : "Consultada, não citada"}
          >
            [{fonte.numero}]
          </Box>
        )}
        <IconeArquivo tipo={fonte.tipo_arquivo} tamanho={16} />
        <Typography sx={{ fontSize: 14, fontWeight: 600, flex: 1, minWidth: 0 }} noWrap title={fonte.titulo}>
          {fonte.titulo}
        </Typography>
      </Box>
      {local && <Typography variant="caption">{local}</Typography>}
      {fonte.trecho && !compacto && (
        <Typography
          component="blockquote"
          sx={{
            m: 0,
            pl: 1.5,
            borderLeft: `3px solid ${cores.primariaBorda}`,
            fontSize: 13,
            lineHeight: "20px",
            color: cores.textoSecundario,
            display: "-webkit-box",
            WebkitLineClamp: 4,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {fonte.trecho}
        </Typography>
      )}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
        <Typography variant="caption">
          Versão {fonte.versao}, atualizada em {data(fonte.atualizado_em)}
        </Typography>
        {fonte.pode_abrir ? (
          <Button
            size="small"
            endIcon={<ExternalLink size={14} />}
            onClick={() => navegar(`/documentos/${fonte.documento_id}${fonte.pagina ? `?pagina=${fonte.pagina}` : ""}`)}
          >
            Abrir documento
          </Button>
        ) : (
          <Typography variant="caption" sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}>
            <Lock size={12} /> Abertura não autorizada
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export function CartaoSetor({ setor, destaque = false }: { setor: SetorSugerido; destaque?: boolean }) {
  return (
    <Box
      sx={{
        border: `1px solid ${destaque ? cores.primariaBorda : cores.borda}`,
        bgcolor: destaque ? cores.primariaFundo : cores.superficie,
        borderRadius: 2,
        p: 1.75,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: 14 }}>
        {setor.nome} <Box component="span" sx={{ color: cores.textoSecundario, fontWeight: 500 }}>({setor.sigla})</Box>
      </Typography>
      {setor.descricao && <Typography variant="body2" sx={{ color: cores.textoSecundario }}>{setor.descricao}</Typography>}
      {setor.canal_contato && (
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          Contato: {setor.canal_contato}
        </Typography>
      )}
      {setor.horario_atendimento && <Typography variant="caption">Atendimento: {setor.horario_atendimento}</Typography>}
      {setor.orientacao_acesso && (
        <Typography variant="body2" sx={{ mt: 0.5, color: cores.textoSecundario }}>
          {setor.orientacao_acesso}
        </Typography>
      )}
    </Box>
  );
}
