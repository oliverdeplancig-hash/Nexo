import { useState } from "react";
import {
  Box,
  Button,
  Chip,
  IconButton,
  Popover,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { ThumbsDown, ThumbsUp } from "lucide-react";

import { api } from "../api/cliente";
import type { Avaliacao } from "../api/tipos";
import { cores } from "../tema";

export const MOTIVOS: Record<string, string> = {
  incorreta: "Informação incorreta",
  incompleta: "Incompleta",
  nao_respondeu: "Não respondeu à pergunta",
  desatualizada: "Desatualizada",
  setor_errado: "Setor indicado errado",
  outro: "Outro",
};

/** "Esta resposta ajudou?" — o autor marca útil / não útil; no "não", escolhe o motivo. */
export default function AvaliacaoResposta({
  mensagemId,
  inicial,
}: {
  mensagemId: number;
  inicial: Avaliacao | null;
}) {
  const [avaliacao, setAvaliacao] = useState<Avaliacao | null>(inicial);
  const [ancora, setAncora] = useState<HTMLElement | null>(null);
  const [motivo, setMotivo] = useState(inicial?.motivo ?? "");
  const [comentario, setComentario] = useState(inicial?.comentario ?? "");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  async function salvar(dados: Avaliacao | null) {
    setEnviando(true);
    setErro("");
    try {
      if (dados === null) {
        await api(`/mensagens/${mensagemId}/avaliacao/`, { method: "DELETE" });
        setAvaliacao(null);
      } else {
        setAvaliacao(
          await api<Avaliacao>(`/mensagens/${mensagemId}/avaliacao/`, {
            method: "PUT",
            json: dados,
          }),
        );
      }
      setAncora(null);
    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : "Não foi possível registrar a avaliação.",
      );
    } finally {
      setEnviando(false);
    }
  }

  const util = avaliacao?.util === true;
  const naoUtil = avaliacao?.util === false;

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.25 }}>
      <Tooltip
        title={
          util
            ? "Você marcou como útil (clique para desfazer)"
            : "Resposta útil"
        }
      >
        <IconButton
          size="small"
          aria-label="Resposta útil"
          aria-pressed={util}
          disabled={enviando}
          onClick={() =>
            salvar(util ? null : { util: true, motivo: "", comentario: "" })
          }
          sx={
            util
              ? {
                  color: cores.verificado.forte,
                  bgcolor: cores.verificado.fundo,
                }
              : undefined
          }
        >
          <ThumbsUp size={16} />
        </IconButton>
      </Tooltip>
      <Tooltip
        title={
          naoUtil
            ? `Não útil: ${MOTIVOS[avaliacao?.motivo ?? ""] ?? "sem motivo"}`
            : "Resposta não ajudou"
        }
      >
        <IconButton
          size="small"
          aria-label="Resposta não ajudou"
          aria-pressed={naoUtil}
          aria-haspopup="dialog"
          disabled={enviando}
          onClick={(e) => setAncora(e.currentTarget)}
          sx={
            naoUtil
              ? { color: cores.cautela.forte, bgcolor: cores.cautela.fundo }
              : undefined
          }
        >
          <ThumbsDown size={16} />
        </IconButton>
      </Tooltip>
      {erro && (
        <Typography variant="caption" sx={{ color: cores.erro, ml: 0.5 }}>
          {erro}
        </Typography>
      )}

      <Popover
        open={!!ancora}
        anchorEl={ancora}
        onClose={() => setAncora(null)}
        anchorOrigin={{ vertical: "top", horizontal: "left" }}
        transformOrigin={{ vertical: "bottom", horizontal: "left" }}
        slotProps={{
          paper: {
            sx: { p: 2, width: 340, maxWidth: "calc(100vw - 32px)" },
            role: "dialog",
            "aria-label": "O que faltou na resposta?",
          },
        }}
      >
        <Typography sx={{ fontWeight: 600, fontSize: 14, mb: 1 }}>
          O que não ajudou?
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mb: 1.5 }}>
          {Object.entries(MOTIVOS).map(([valor, rotulo]) => (
            <Chip
              key={valor}
              label={rotulo}
              size="small"
              onClick={() => setMotivo(valor)}
              variant={motivo === valor ? "filled" : "outlined"}
              color={motivo === valor ? "primary" : "default"}
              aria-pressed={motivo === valor}
            />
          ))}
        </Box>
        <TextField
          size="small"
          fullWidth
          multiline
          minRows={2}
          label="Comentário (opcional)"
          value={comentario}
          onChange={(e) => setComentario(e.target.value.slice(0, 500))}
          helperText="Ajuda a equipe a corrigir a resposta. Não inclua dados pessoais."
        />
        <Box
          sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mt: 1.5 }}
        >
          {naoUtil && (
            <Button
              size="small"
              onClick={() => salvar(null)}
              disabled={enviando}
            >
              Remover avaliação
            </Button>
          )}
          <Button
            size="small"
            variant="contained"
            disabled={enviando || !motivo}
            onClick={() =>
              salvar({ util: false, motivo, comentario: comentario.trim() })
            }
          >
            Enviar
          </Button>
        </Box>
      </Popover>
    </Box>
  );
}
