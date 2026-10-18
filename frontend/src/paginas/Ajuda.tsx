import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Accordion, AccordionDetails, AccordionSummary, Box, Button, Chip, InputAdornment, Paper, TextField, Typography } from "@mui/material";
import { Bot, ChevronDown, LifeBuoy, Search } from "lucide-react";

import { GRUPOS, ROTULO_FUNCAO, topicoDaTela, topicosPermitidos, type Topico } from "../ajuda/conteudo";
import { Cabecalho, EstadoVazio, Pagina } from "../componentes/comuns";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores } from "../tema";

const normalizar = (t: string) =>
  t
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();

function textoDoTopico(t: Topico) {
  return normalizar([t.titulo, t.resumo, ...(t.passos ?? []), ...(t.dicas ?? [])].join(" "));
}

/** Ajuda adaptada ao perfil: cada pessoa vê só os tópicos das funções que tem. */
export default function Ajuda() {
  const { usuario, tem } = useAutenticacao();
  const navegar = useNavigate();
  const [params] = useSearchParams();
  const grupos = useMemo(() => topicosPermitidos(tem), [tem]);
  const inicial = params.get("topico") ?? (params.get("de") ? topicoDaTela(grupos, params.get("de")!) : null);
  const [aberto, setAberto] = useState<string | null>(inicial);
  const [termo, setTermo] = useState("");
  const refs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!inicial) return;
    setAberto(inicial);
    refs.current[inicial]?.scrollIntoView({ block: "start" });
  }, [inicial]);

  const filtrados = useMemo(() => {
    const q = normalizar(termo.trim());
    if (!q) return grupos;
    const partes = q.split(/\s+/);
    return grupos
      .map((g) => ({ ...g, topicos: g.topicos.filter((t) => partes.every((p) => textoDoTopico(t).includes(p))) }))
      .filter((g) => g.topicos.length > 0);
  }, [grupos, termo]);

  const funcoes = (usuario?.funcoes ?? []).map((f) => ROTULO_FUNCAO[f]).filter(Boolean);
  const totalTopicos = GRUPOS.reduce((n, g) => n + g.topicos.length, 0);
  const visiveis = grupos.reduce((n, g) => n + g.topicos.length, 0);

  return (
    <Pagina>
      <Cabecalho titulo="Ajuda" descricao="Como usar o Nexo, de acordo com o seu perfil de acesso." />

      <Paper variant="outlined" sx={{ p: 2.5, mb: 3, display: "grid", gap: 1 }}>
        <Typography sx={{ fontWeight: 600 }}>
          {usuario?.nome}
          {usuario?.setor ? `, ${usuario.setor.nome}` : ", sem setor vinculado"}
        </Typography>
        <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
          {(usuario?.perfis ?? []).map((p) => (
            <Chip key={p.codigo} size="small" label={p.nome} sx={{ bgcolor: cores.primariaFundo, color: cores.primariaHover }} />
          ))}
        </Box>
        <Typography variant="body2" sx={{ color: cores.textoSecundario }}>
          Com o seu perfil você consulta os documentos autorizados e usa o assistente
          {funcoes.length ? `, e também pode ${funcoes.join("; ")}.` : "."}
          {visiveis < totalTopicos && " Esta ajuda mostra só o que vale para você."}
        </Typography>
        {!usuario?.setor && (
          <Typography variant="body2" sx={{ color: cores.cautela.texto }}>
            Você ainda não tem setor no Nexo, por isso vê só os documentos de acesso geral. Peça ao administrador do sistema para definir o seu setor.
          </Typography>
        )}
      </Paper>

      <TextField
        id="ajuda-busca"
        fullWidth
        size="small"
        placeholder="Buscar na ajuda (ex.: coleção, baixar, setor)"
        value={termo}
        onChange={(e) => setTermo(e.target.value)}
        InputProps={{ startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment> }}
        inputProps={{ "aria-label": "Buscar na ajuda" }}
        sx={{ mb: 3 }}
      />

      {filtrados.length === 0 && (
        <Paper variant="outlined">
          <EstadoVazio
            icone={<LifeBuoy size={28} />}
            titulo="Nada encontrado na ajuda"
            texto="Tente outra palavra ou pergunte ao assistente."
            acao={<Button onClick={() => navegar("/assistente")}>Perguntar ao assistente</Button>}
          />
        </Paper>
      )}

      <Box sx={{ display: "grid", gap: 3 }}>
        {filtrados.map((g) => (
          <Box component="section" key={g.titulo} aria-label={g.titulo}>
            <Typography component="h2" sx={{ fontSize: 18, fontWeight: 700, color: cores.titulo }}>
              {g.titulo}
            </Typography>
            <Typography variant="body2" sx={{ color: cores.textoSecundario, mb: 1.25 }}>
              {g.descricao}
            </Typography>
            {g.topicos.map((t) => (
              <Accordion
                key={t.id}
                ref={(el) => {
                  refs.current[t.id] = el;
                }}
                expanded={aberto === t.id || !!termo.trim()}
                onChange={(_, v) => setAberto(v ? t.id : null)}
                disableGutters
                variant="outlined"
                sx={{ "&:not(:last-of-type)": { borderBottom: 0 }, scrollMarginTop: 72 }}
              >
                <AccordionSummary expandIcon={<ChevronDown size={18} />} id={`ajuda-${t.id}`} aria-controls={`ajuda-${t.id}-conteudo`}>
                  <Typography sx={{ fontWeight: 600 }}>{t.titulo}</Typography>
                </AccordionSummary>
                <AccordionDetails id={`ajuda-${t.id}-conteudo`} sx={{ pt: 0, display: "grid", gap: 1.5, maxWidth: 760 }}>
                  <Typography variant="body2">{t.resumo}</Typography>
                  {t.passos && (
                    <Box component="ol" sx={{ m: 0, pl: 2.5, display: "grid", gap: 0.75 }}>
                      {t.passos.map((p) => (
                        <Typography component="li" variant="body2" key={p}>
                          {p}
                        </Typography>
                      ))}
                    </Box>
                  )}
                  {t.dicas && (
                    <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: cores.fundo, border: `1px solid ${cores.bordaSutil}` }}>
                      <Typography sx={{ fontSize: 13, fontWeight: 600, color: cores.textoSecundario, mb: 0.5 }}>Bom saber</Typography>
                      <Box component="ul" sx={{ m: 0, pl: 2.5, display: "grid", gap: 0.5 }}>
                        {t.dicas.map((d) => (
                          <Typography component="li" variant="body2" key={d} sx={{ color: cores.textoSecundario }}>
                            {d}
                          </Typography>
                        ))}
                      </Box>
                    </Box>
                  )}
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        ))}
      </Box>

      <Paper variant="outlined" sx={{ p: 2.5, mt: 4, display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
        <Box sx={{ flex: "1 1 260px" }}>
          <Typography sx={{ fontWeight: 600 }}>Ainda com dúvida?</Typography>
          <Typography variant="body2" sx={{ color: cores.textoSecundario }}>
            Pergunte ao assistente sobre normas e procedimentos. Para acesso, perfis ou problemas no sistema, procure o administrador do Nexo no seu órgão.
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<Bot size={16} />} onClick={() => navegar("/assistente")}>
          Perguntar ao assistente
        </Button>
      </Paper>
    </Pagina>
  );
}
