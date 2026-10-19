import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  IconButton,
  InputBase,
  LinearProgress,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  ArrowUp,
  BookOpenCheck,
  Bot,
  Check,
  ChevronDown,
  Copy,
  FileSearch,
  ListChecks,
  PanelRight,
  Plus,
  Square,
  WifiOff,
  X,
} from "lucide-react";

import { api } from "../api/cliente";
import { SocketNexo, type EstadoConexao } from "../api/socket";
import type { Conversa, Fonte, Mensagem } from "../api/tipos";
import AvaliacaoResposta from "../componentes/AvaliacaoResposta";
import { Markdown, PainelContextual, SeloConfianca } from "../componentes/comuns";
import { CartaoFonte, CartaoSetor } from "../componentes/Fontes";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores, fonteMono, medidas, sombras } from "../tema";
import { dataHora } from "../util/formatos";

const SUGESTOES = [
  "Como funciona determinado procedimento?",
  "Quais documentos preciso apresentar?",
  "Onde encontro a norma sobre este assunto?",
  "Qual setor é responsável por essa demanda?",
  "Resuma um documento autorizado.",
  "Encontre documentos relacionados a um tema.",
];

const ROTULO_ORIGEM: Record<string, string> = {
  deterministico: "Resposta institucional aprovada",
  rag: "Gerada a partir dos documentos",
  extrativo: "Trechos dos documentos",
  sem_fontes: "Sem fontes suficientes",
  desambiguacao: "Esclarecimento",
};

interface Rascunho {
  texto: string;
  etapa: string;
  aviso?: string;
}

export default function Chat() {
  const { conversaId } = useParams();
  const local = useLocation();
  const navegar = useNavigate();
  const queryClient = useQueryClient();
  const { usuario } = useAutenticacao();

  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [texto, setTexto] = useState("");
  const [rascunho, setRascunho] = useState<Rascunho | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [conexao, setConexao] = useState<EstadoConexao>("conectando");
  const [painelAberto, setPainelAberto] = useState(false);
  const [fontesPainel, setFontesPainel] = useState<Fonte[]>([]);
  const [carregando, setCarregando] = useState(false);

  const socket = useRef<SocketNexo | null>(null);
  const idAtual = useRef<number | null>(conversaId ? Number(conversaId) : null);
  const criadaAgora = useRef<number | null>(null);
  const fimRef = useRef<HTMLDivElement>(null);
  const estado = local.state as { pergunta?: string; documentoId?: number; documentoTitulo?: string; nova?: number } | null;
  const [compactadas, setCompactadas] = useState(0);
  const [documentoContexto, setDocumentoContexto] = useState<{ id: number; titulo: string } | null>(
    estado?.documentoId ? { id: estado.documentoId, titulo: estado.documentoTitulo ?? "Documento" } : null,
  );

  const status = useQuery({
    queryKey: ["status-servicos"],
    queryFn: () => api<{ ia_disponivel: boolean }>("/status/"),
    refetchInterval: 60_000,
  });

  // useNavigate muda de identidade a cada navegação; a conexão não pode depender dela.
  const navegarRef = useRef(navegar);
  navegarRef.current = navegar;

  // Conexão WebSocket da página (uma por montagem da tela)
  useEffect(() => {
    const s = new SocketNexo("/ws/chat/");
    socket.current = s;
    const pararEstado = s.ouvirEstado(setConexao);
    const parar = s.ouvir((ev) => {
      switch (ev.tipo) {
        case "conversa":
          if (idAtual.current !== ev.id) {
            idAtual.current = ev.id;
            criadaAgora.current = ev.id;
            navegarRef.current(`/assistente/${ev.id}`, { replace: true, state: null });
          }
          break;
        case "status":
          setRascunho((r) => ({ texto: r?.texto ?? "", etapa: ev.texto, aviso: r?.aviso }));
          break;
        case "token":
          setRascunho((r) => ({ texto: (r?.texto ?? "") + ev.texto, etapa: r?.etapa ?? "Gerando resposta", aviso: r?.aviso }));
          break;
        case "aviso":
          setRascunho((r) => ({ texto: r?.texto ?? "", etapa: r?.etapa ?? "", aviso: ev.texto }));
          break;
        case "resposta":
          setRascunho(null);
          setMensagens((m) => [...m, ev.mensagem]);
          queryClient.invalidateQueries({ queryKey: ["conversas"] });
          break;
        case "erro":
          setRascunho(null);
          setErro(ev.texto);
          break;
      }
    });
    s.conectar();
    return () => {
      parar();
      pararEstado();
      s.encerrar();
    };
  }, [queryClient]);

  // Carrega o histórico ao abrir uma conversa existente
  useEffect(() => {
    const id = conversaId ? Number(conversaId) : null;
    if (id && id === criadaAgora.current) return; // acabou de ser criada nesta tela
    idAtual.current = id;
    setErro(null);
    setRascunho(null);
    setCompactadas(0);
    if (!id) {
      setMensagens([]);
      if (!estado?.documentoId) setDocumentoContexto(null);
      return;
    }
    setCarregando(true);
    Promise.all([api<Conversa>(`/conversas/${id}/`), api<Mensagem[]>(`/conversas/${id}/mensagens/`)])
      .then(([conversa, lista]) => {
        setMensagens(lista);
        setCompactadas(conversa.memoria?.mensagens_compactadas ?? 0);
        setDocumentoContexto(
          conversa.documento_contexto ? { id: conversa.documento_contexto, titulo: conversa.documento_contexto_titulo ?? "Documento" } : null,
        );
      })
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversaId, estado?.nova]);

  // Pergunta vinda do dashboard
  const perguntaInicial = useRef(false);
  useEffect(() => {
    if (estado?.pergunta && !perguntaInicial.current) {
      perguntaInicial.current = true;
      enviar(estado.pergunta);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensagens.length, rascunho?.texto]);

  const gerando = rascunho !== null;

  const enviar = useCallback(
    (conteudo?: string) => {
      const pergunta = (conteudo ?? texto).trim();
      if (!pergunta || gerando) return;
      setErro(null);
      setMensagens((m) => [
        ...m,
        {
          id: -Date.now(),
          papel: "usuario",
          conteudo: pergunta,
          origem: "",
          confianca: "",
          etapas: [],
          setor: null,
          setores_sugeridos: [],
          sugestoes: [],
          fontes: [],
          rastro: {},
          interrompida: false,
          duracao_ms: null,
          avaliacao: null,
          criada_em: new Date().toISOString(),
        },
      ]);
      setRascunho({ texto: "", etapa: "Enviando" });
      socket.current?.enviar({
        tipo: "mensagem",
        texto: pergunta,
        conversa_id: idAtual.current,
        documento_id: idAtual.current ? undefined : documentoContexto?.id,
      });
      setTexto("");
    },
    [texto, gerando, documentoContexto],
  );

  function novaConversa() {
    criadaAgora.current = null;
    idAtual.current = null;
    setDocumentoContexto(null);
    navegar("/assistente", { state: { nova: Date.now() } });
  }

  function aoTeclar(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      enviar();
    }
  }

  function abrirFontes(fontes: Fonte[]) {
    setFontesPainel(fontes);
    setPainelAberto(true);
  }

  const vazio = !mensagens.length && !gerando && !carregando;
  const iaDisponivel = status.data?.ia_disponivel;

  return (
    <Box sx={{ display: "flex", minHeight: { xs: "calc(100dvh - 57px - 72px)", lg: "100dvh" } }}>
      <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        {/* Cabeçalho do chat */}
        <Box
          component="header"
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            px: { xs: 2, md: 4 },
            py: 1.75,
            borderBottom: `1px solid ${cores.borda}`,
            bgcolor: cores.superficie,
            position: { lg: "sticky" },
            top: 0,
            zIndex: 5,
          }}
        >
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="h3" component="h1" sx={{ fontSize: { xs: 17, md: 20 } }}>
              Assistente Institucional
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
              <IndicadorServico conexao={conexao} ia={iaDisponivel} />
              <Typography variant="caption" sx={{ display: { xs: "none", sm: "inline" } }}>
                Encontre informações e procedimentos da instituição
              </Typography>
            </Box>
          </Box>
          <Tooltip title="Fontes da resposta">
            <IconButton
              onClick={() => {
                const ultima = [...mensagens].reverse().find((m) => m.fontes.length);
                abrirFontes(ultima?.fontes ?? []);
              }}
              aria-label="Abrir painel de fontes"
            >
              <PanelRight size={20} />
            </IconButton>
          </Tooltip>
          <Button variant="outlined" startIcon={<Plus size={16} />} onClick={novaConversa} sx={{ display: { xs: "none", sm: "inline-flex" } }}>
            Nova conversa
          </Button>
          <IconButton onClick={novaConversa} aria-label="Nova conversa" sx={{ display: { sm: "none" } }}>
            <Plus size={20} />
          </IconButton>
        </Box>

        {conexao === "reconectando" && (
          <Alert severity="warning" icon={<WifiOff size={18} />} sx={{ borderRadius: 0 }}>
            Conexão interrompida. Reconectando ao assistente…
          </Alert>
        )}
        {documentoContexto && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, px: { xs: 2, md: 4 }, py: 1, bgcolor: cores.primariaFundo, borderBottom: `1px solid ${cores.primariaBorda}` }}>
            <FileSearch size={16} color={cores.primariaHover} />
            <Typography variant="body2" sx={{ flex: 1, color: cores.primariaAtiva }}>
              Perguntas limitadas ao documento <strong>{documentoContexto.titulo}</strong>
            </Typography>
            {!idAtual.current && (
              <IconButton size="small" onClick={() => setDocumentoContexto(null)} aria-label="Remover limite de documento">
                <X size={16} />
              </IconButton>
            )}
          </Box>
        )}
        {carregando && <LinearProgress />}

        {/* Mensagens */}
        <Box sx={{ flex: 1, px: { xs: 2, md: 4 }, py: 3 }} aria-live="polite">
          <Box sx={{ maxWidth: medidas.conteudoMax, mx: "auto", display: "flex", flexDirection: "column", gap: 3 }}>
            {vazio && <EstadoInicial aoEscolher={(s) => setTexto(s)} />}
            {compactadas > 0 && (
              <Typography variant="caption" component="p" sx={{ textAlign: "center", fontSize: 12 }}>
                Conversa longa: as mensagens mais antigas foram resumidas para o assistente entender as próximas perguntas. Elas
                continuam aqui para você.
              </Typography>
            )}
            {mensagens.map((m) =>
              m.papel === "usuario" ? (
                <MensagemUsuario key={m.id} m={m} nome={usuario?.nome ?? ""} />
              ) : (
                <MensagemAssistente key={m.id} m={m} aoAbrirFontes={abrirFontes} aoEscolher={(s) => enviar(s)} />
              ),
            )}
            {rascunho && <RespostaEmGeracao rascunho={rascunho} />}
            {erro && (
              <Alert severity="error" variant="outlined" action={<Button color="inherit" size="small" onClick={() => setErro(null)}>Fechar</Button>}>
                {erro}
              </Alert>
            )}
            <div ref={fimRef} />
          </Box>
        </Box>

        {/* Compositor */}
        <Box sx={{ position: "sticky", bottom: { xs: 72, md: 0 }, px: { xs: 1.5, md: 4 }, pb: { xs: 1.5, md: 2.5 }, pt: 1, background: `linear-gradient(transparent, ${cores.fundo} 24%)` }}>
          <Box sx={{ maxWidth: medidas.conteudoMax, mx: "auto" }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "flex-end",
                gap: 1,
                p: 1,
                pl: 2,
                bgcolor: cores.superficie,
                border: `1px solid ${cores.bordaForte}`,
                borderRadius: 3,
                boxShadow: sombras.n2,
                "&:focus-within": { borderColor: cores.primaria, boxShadow: `${sombras.n2}, 0 0 0 3px rgba(37,99,235,.15)` },
              }}
            >
              <InputBase
                multiline
                maxRows={8}
                value={texto}
                onChange={(e) => setTexto(e.target.value.slice(0, 4000))}
                onKeyDown={aoTeclar}
                placeholder="Digite sua pergunta sobre documentos ou procedimentos institucionais..."
                inputProps={{ "aria-label": "Mensagem para o assistente" }}
                sx={{ flex: 1, py: 1, fontSize: 15, lineHeight: "24px" }}
              />
              {gerando ? (
                <Tooltip title="Interromper resposta">
                  <IconButton
                    onClick={() => socket.current?.enviar({ tipo: "interromper" })}
                    aria-label="Interromper resposta"
                    sx={{ bgcolor: cores.titulo, color: "#fff", "&:hover": { bgcolor: cores.texto } }}
                  >
                    <Square size={16} fill="currentColor" />
                  </IconButton>
                </Tooltip>
              ) : (
                <Tooltip title="Enviar (Enter)">
                  <span>
                    <IconButton
                      onClick={() => enviar()}
                      disabled={!texto.trim() || conexao !== "conectado"}
                      aria-label="Enviar pergunta"
                      sx={{ bgcolor: cores.primaria, color: "#fff", "&:hover": { bgcolor: cores.primariaHover }, "&.Mui-disabled": { bgcolor: cores.borda, color: "#94A3B8" } }}
                    >
                      <ArrowUp size={20} />
                    </IconButton>
                  </span>
                </Tooltip>
              )}
            </Box>
            <Typography variant="caption" component="p" sx={{ textAlign: "center", mt: 1, fontSize: 12 }}>
              Confira as fontes e os procedimentos oficiais antes de tomar decisões administrativas.
            </Typography>
          </Box>
        </Box>
      </Box>

      <PainelContextual
        aberto={painelAberto}
        aoFechar={() => setPainelAberto(false)}
        titulo="Fontes da resposta"
        subtitulo="Documentos consultados para gerar a resposta"
      >
        {fontesPainel.length ? (
          <Box sx={{ display: "grid", gap: 1.5 }}>
            {fontesPainel.map((f, i) => (
              <CartaoFonte key={`${f.documento_id}-${f.trecho_id ?? i}`} fonte={f} />
            ))}
          </Box>
        ) : (
          <Typography variant="body2" sx={{ color: cores.textoSecundario }}>
            A resposta selecionada não utilizou documentos. Respostas sem fontes devem ser conferidas com o setor responsável.
          </Typography>
        )}
      </PainelContextual>
    </Box>
  );
}

function IndicadorServico({ conexao, ia }: { conexao: EstadoConexao; ia?: boolean }) {
  const online = conexao === "conectado";
  const cor = !online ? cores.cautela.forte : ia === false ? cores.cautela.forte : cores.verificado.forte;
  const texto = !online
    ? conexao === "reconectando"
      ? "Reconectando"
      : "Conectando"
    : ia === false
      ? "Disponível com recursos limitados"
      : "Disponível";
  return (
    <Box component="span" role="status" sx={{ display: "inline-flex", alignItems: "center", gap: 0.75, fontSize: 12, fontWeight: 500, color: cores.textoSecundario }}>
      <Box component="span" sx={{ width: 8, height: 8, borderRadius: 99, bgcolor: cor }} />
      {texto}
    </Box>
  );
}

function EstadoInicial({ aoEscolher }: { aoEscolher: (s: string) => void }) {
  return (
    <Box sx={{ textAlign: "center", pt: { xs: 4, md: 8 }, pb: 2 }}>
      <Box sx={{ display: "inline-grid", placeItems: "center", width: 56, height: 56, borderRadius: 3, bgcolor: cores.barraLateral, color: "#fff", mb: 2 }}>
        <Bot size={28} />
      </Box>
      <Typography variant="h2" component="h2" sx={{ fontSize: { xs: 22, md: 26 } }}>
        Como posso ajudar você hoje?
      </Typography>
      <Typography sx={{ color: cores.textoSecundario, mt: 1, mb: 3, maxWidth: 520, mx: "auto" }}>
        Consulte documentos autorizados, entenda procedimentos e descubra qual setor pode ajudar.
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1, textAlign: "left" }}>
        {SUGESTOES.map((s) => (
          <Box
            key={s}
            component="button"
            type="button"
            onClick={() => aoEscolher(s)}
            sx={{
              font: "inherit",
              fontSize: 14,
              textAlign: "left",
              cursor: "pointer",
              p: 1.75,
              borderRadius: 2,
              border: `1px solid ${cores.borda}`,
              bgcolor: cores.superficie,
              color: cores.texto,
              "&:hover": { borderColor: cores.primariaBorda, bgcolor: cores.primariaFundo },
            }}
          >
            {s}
          </Box>
        ))}
      </Box>
    </Box>
  );
}

function MensagemUsuario({ m, nome }: { m: Mensagem; nome: string }) {
  return (
    <Box sx={{ alignSelf: "flex-end", maxWidth: { xs: "92%", md: "75%" } }}>
      <Box sx={{ bgcolor: cores.bordaSutil, border: `1px solid ${cores.borda}`, borderRadius: 2, px: 2, py: 1.5 }}>
        <Typography sx={{ whiteSpace: "pre-wrap", fontSize: 15 }}>{m.conteudo}</Typography>
      </Box>
      <Typography variant="caption" component="p" sx={{ textAlign: "right", mt: 0.5, fontSize: 12 }}>
        {nome}, {dataHora(m.criada_em)}
      </Typography>
    </Box>
  );
}

function MensagemAssistente({
  m,
  aoAbrirFontes,
  aoEscolher,
}: {
  m: Mensagem;
  aoAbrirFontes: (f: Fonte[]) => void;
  aoEscolher: (s: string) => void;
}) {
  const [copiado, setCopiado] = useState(false);
  const [detalhes, setDetalhes] = useState(false);
  const citadas = m.fontes.filter((f) => f.citada);
  const consultadas = m.fontes.filter((f) => !f.citada);

  return (
    <Box component="article" aria-label="Resposta do assistente" sx={{ bgcolor: cores.superficie, border: `1px solid ${cores.borda}`, borderRadius: 2, boxShadow: sombras.n1 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, flexWrap: "wrap", px: 2.5, pt: 2 }}>
        <Box sx={{ display: "grid", placeItems: "center", width: 28, height: 28, borderRadius: 1.5, bgcolor: cores.barraLateral, color: "#fff" }}>
          <Bot size={16} />
        </Box>
        <Typography sx={{ fontWeight: 600, fontSize: 14 }}>Assistente</Typography>
        <Typography variant="caption">{ROTULO_ORIGEM[m.origem] ?? ""}</Typography>
        <Box sx={{ flex: 1 }} />
        <SeloConfianca confianca={m.confianca} />
      </Box>

      <Box sx={{ px: 2.5, pb: 1 }}>
        <Markdown texto={m.conteudo} />
        {m.interrompida && <Typography variant="caption">Resposta interrompida.</Typography>}

        {m.etapas.length > 0 && (
          <Box component="ol" sx={{ listStyle: "none", p: 0, m: 0, mt: 1.5, display: "grid", gap: 1 }}>
            {m.etapas.map((e, i) => (
              <Box component="li" key={i} sx={{ display: "flex", gap: 1.5, p: 1.5, borderRadius: 2, bgcolor: cores.fundo, border: `1px solid ${cores.bordaSutil}` }}>
                <Box sx={{ flexShrink: 0, width: 24, height: 24, borderRadius: 99, bgcolor: cores.primaria, color: "#fff", fontSize: 13, fontWeight: 600, display: "grid", placeItems: "center" }}>
                  {i + 1}
                </Box>
                <Box>
                  <Typography sx={{ fontWeight: 600, fontSize: 14, color: cores.titulo }}>{e.titulo}</Typography>
                  {e.descricao && <Typography variant="body2" sx={{ color: cores.textoSecundario }}>{e.descricao}</Typography>}
                </Box>
              </Box>
            ))}
          </Box>
        )}

        {m.sugestoes.length > 0 && (
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1.5 }}>
            {m.sugestoes.map((s) => (
              <Chip key={s} label={s} onClick={() => aoEscolher(s)} variant="outlined" sx={{ borderColor: cores.primariaBorda, color: cores.primariaHover }} />
            ))}
          </Box>
        )}

        {m.setor && (
          <Box sx={{ mt: 2 }}>
            <Typography sx={{ fontSize: 13, fontWeight: 600, color: cores.textoSecundario, mb: 0.75 }}>Setor responsável</Typography>
            <CartaoSetor setor={m.setor} destaque />
          </Box>
        )}
        {m.setores_sugeridos.length > 0 && (
          <Box sx={{ mt: 2, display: "grid", gap: 1 }}>
            <Typography sx={{ fontSize: 13, fontWeight: 600, color: cores.textoSecundario }}>Setores que podem ajudar</Typography>
            {m.setores_sugeridos.map((s) => (
              <CartaoSetor key={s.id} setor={s} />
            ))}
          </Box>
        )}
      </Box>

      {m.fontes.length > 0 && (
        <Box component="section" aria-label="Fontes consultadas" sx={{ mx: 2.5, mt: 1, pt: 2, borderTop: `1px solid ${cores.borda}` }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.25 }}>
            <BookOpenCheck size={16} color={cores.textoSecundario} />
            <Typography sx={{ fontWeight: 600, fontSize: 14 }}>Fontes consultadas</Typography>
            <Typography variant="caption">
              {citadas.length} citada{citadas.length === 1 ? "" : "s"}
              {consultadas.length ? `, ${consultadas.length} consultada${consultadas.length === 1 ? "" : "s"} sem citação` : ""}
            </Typography>
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 1.25 }}>
            {(citadas.length ? citadas : m.fontes).slice(0, 4).map((f, i) => (
              <CartaoFonte key={`${f.documento_id}-${f.trecho_id ?? i}`} fonte={f} />
            ))}
          </Box>
        </Box>
      )}

      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, px: 1.5, py: 1, mt: 1 }}>
        <Tooltip title={copiado ? "Copiado" : "Copiar resposta"}>
          <IconButton
            size="small"
            aria-label="Copiar resposta"
            onClick={async () => {
              await navigator.clipboard?.writeText(m.conteudo);
              setCopiado(true);
              setTimeout(() => setCopiado(false), 1500);
            }}
          >
            {copiado ? <Check size={16} /> : <Copy size={16} />}
          </IconButton>
        </Tooltip>
        {m.id > 0 && m.origem !== "erro" && m.origem !== "desambiguacao" && (
          <AvaliacaoResposta key={m.id} mensagemId={m.id} inicial={m.avaliacao ?? null} />
        )}
        {m.fontes.length > 0 && (
          <Button size="small" startIcon={<PanelRight size={16} />} onClick={() => aoAbrirFontes(m.fontes)}>
            Ver todas as fontes
          </Button>
        )}
        <Button size="small" startIcon={<ListChecks size={16} />} endIcon={<ChevronDown size={14} style={{ transform: detalhes ? "rotate(180deg)" : undefined }} />} onClick={() => setDetalhes(!detalhes)} aria-expanded={detalhes}>
          Como esta resposta foi obtida
        </Button>
        <Box sx={{ flex: 1 }} />
        <Typography variant="caption" sx={{ display: { xs: "none", sm: "block" }, fontSize: 12 }}>
          {dataHora(m.criada_em)}
          {m.duracao_ms ? `, ${(m.duracao_ms / 1000).toFixed(1).replace(".", ",")} s` : ""}
        </Typography>
      </Box>
      <Collapse in={detalhes} unmountOnExit>
        <Rastro rastro={m.rastro} origem={m.origem} />
      </Collapse>
    </Box>
  );
}

function Rastro({ rastro, origem }: { rastro: Record<string, any>; origem: string }) {
  const motor = rastro.motor as Record<string, any> | undefined;
  const linhas: string[] = [];
  if (motor) {
    const melhor = motor.candidatos?.[0];
    linhas.push(
      melhor
        ? `Motor determinístico: melhor regra ${melhor.codigo} com pontuação ${melhor.pontuacao} (limiar ${motor.limiar}).`
        : "Motor determinístico: nenhuma regra relacionada.",
    );
  }
  if (rastro.regra) linhas.push(`Resposta da regra ${rastro.regra.codigo}, versão ${rastro.regra.versao}. Nenhum modelo de IA foi usado.`);
  if (rastro.busca) {
    const b = rastro.busca;
    linhas.push(`Busca nos documentos autorizados: ${b.texto} trechos por texto, ${b.semantica} por significado, ${b.nome} por nome.`);
    if (b.semantica_disponivel === false) linhas.push("Busca por significado indisponível no momento.");
  }
  if (origem === "rag") linhas.push(`Resposta gerada pela IA local; trechos citados: ${(rastro.citacoes ?? []).join(", ") || "nenhum"}.`);
  if (rastro.aviso) linhas.push(`Atenção: ${rastro.aviso}.`);
  return (
    <Box sx={{ mx: 2.5, mb: 2, p: 1.5, borderRadius: 1.5, bgcolor: cores.fundo, border: `1px solid ${cores.bordaSutil}` }}>
      {linhas.map((l) => (
        <Typography key={l} sx={{ fontSize: 13, lineHeight: "20px", color: cores.textoSecundario, fontFamily: l.startsWith("Motor") ? undefined : undefined }}>
          {l}
        </Typography>
      ))}
      {motor?.pergunta_normalizada && (
        <Typography sx={{ fontFamily: fonteMono, fontSize: 12, color: "#64748B", mt: 0.5 }}>termos: {(motor.tokens ?? []).join(" ")}</Typography>
      )}
    </Box>
  );
}

function RespostaEmGeracao({ rascunho }: { rascunho: Rascunho }) {
  return (
    <Box aria-busy="true" sx={{ bgcolor: cores.superficie, border: `1px solid ${cores.borda}`, borderRadius: 2, p: 2.5 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, mb: rascunho.texto ? 1 : 0 }}>
        <Box sx={{ display: "grid", placeItems: "center", width: 28, height: 28, borderRadius: 1.5, bgcolor: cores.barraLateral, color: "#fff" }}>
          <Bot size={16} />
        </Box>
        <Typography variant="body2" sx={{ color: cores.textoSecundario, fontWeight: 500 }}>
          {rascunho.etapa || "Processando"}…
        </Typography>
      </Box>
      {!rascunho.texto && <LinearProgress sx={{ mt: 1.5, borderRadius: 99, height: 3 }} />}
      {rascunho.aviso && (
        <Alert severity="warning" sx={{ my: 1 }}>
          {rascunho.aviso}
        </Alert>
      )}
      {rascunho.texto && <Markdown texto={rascunho.texto + " ▍"} />}
    </Box>
  );
}
