import { useState, type FormEvent } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Box, Button, InputBase, Link, Skeleton, Typography } from "@mui/material";
import { Bot, Clock, Library, MessageSquare, Search, Users } from "lucide-react";

import { api } from "../api/cliente";
import type { Conversa, DocumentoLista, Paginado, Setor } from "../api/tipos";
import { Cartao, ChipClassificacao, EstadoVazio, IconeArquivo, Pagina, TituloSecao } from "../componentes/comuns";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores, sombras } from "../tema";
import { data, relativo } from "../util/formatos";

export default function Dashboard() {
  const { usuario } = useAutenticacao();
  const navegar = useNavigate();
  const [consulta, setConsulta] = useState("");

  const conversas = useQuery({ queryKey: ["conversas", "recentes"], queryFn: () => api<Paginado<Conversa>>("/conversas/?tamanho=3") });
  const documentos = useQuery({
    queryKey: ["documentos", "recentes-dashboard"],
    queryFn: () => api<Paginado<DocumentoLista>>("/documentos/?tamanho=6&ordem=-atualizacao"),
  });
  const setores = useQuery({ queryKey: ["setores", "dashboard"], queryFn: () => api<Paginado<Setor>>("/setores/?tamanho=4") });

  const primeiroNome = (usuario?.nome ?? "").split(" ")[0];

  function pesquisar(e: FormEvent) {
    e.preventDefault();
    if (consulta.trim()) navegar(`/busca?q=${encodeURIComponent(consulta.trim())}`);
  }

  function perguntar() {
    navegar("/assistente", { state: { pergunta: consulta.trim() || undefined, nova: Date.now() } });
  }

  const atalhos = [
    { titulo: "Consultar documentos", texto: "Normas, manuais e modelos autorizados para o seu perfil.", icone: <Library size={22} />, para: "/repositorio" },
    { titulo: "Fazer uma pergunta à IA", texto: "Respostas com as fontes consultadas.", icone: <Bot size={22} />, para: "/assistente" },
    { titulo: "Encontrar um setor", texto: "Quem é responsável por cada assunto.", icone: <Users size={22} />, para: "/setores" },
    { titulo: "Ver documentos recentes", texto: "O que você abriu nos últimos dias.", icone: <Clock size={22} />, para: "/repositorio?aba=recentes" },
  ];

  return (
    <Pagina>
      <Box component="section" aria-labelledby="saudacao" sx={{ mb: 4 }}>
        <Typography id="saudacao" variant="h1" sx={{ fontSize: { xs: 26, md: 32 } }}>
          Olá, {primeiroNome}
        </Typography>
        <Typography sx={{ color: cores.textoSecundario, mt: 0.5, mb: 2.5 }}>O que você precisa encontrar hoje?</Typography>

        <Box
          component="form"
          role="search"
          onSubmit={pesquisar}
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            gap: 1.25,
            p: 1.25,
            bgcolor: cores.superficie,
            border: `1px solid ${cores.bordaForte}`,
            borderRadius: 3,
            boxShadow: sombras.n2,
            "&:focus-within": { borderColor: cores.primaria },
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1, px: 1 }}>
            <Search size={20} color={cores.textoSecundario} aria-hidden />
            <InputBase
              value={consulta}
              onChange={(e) => setConsulta(e.target.value)}
              placeholder="Pesquise documentos, normas, procedimentos ou faça uma pergunta..."
              inputProps={{ "aria-label": "Pesquisar ou perguntar" }}
              sx={{ flex: 1, fontSize: 15, minHeight: 44 }}
            />
          </Box>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button type="submit" variant="outlined" disabled={!consulta.trim()} sx={{ flex: { xs: 1, sm: "none" } }}>
              Pesquisar
            </Button>
            <Button variant="contained" startIcon={<Bot size={18} />} onClick={perguntar} sx={{ flex: { xs: 1, sm: "none" } }}>
              Perguntar à IA
            </Button>
          </Box>
        </Box>
      </Box>

      <Box component="section" aria-label="Acesso rápido" sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" }, gap: 1.5, mb: 5 }}>
        {atalhos.map((a) => (
          <Box
            key={a.titulo}
            component={RouterLink}
            to={a.para}
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 1,
              p: 2,
              borderRadius: 2,
              border: `1px solid ${cores.borda}`,
              bgcolor: cores.superficie,
              textDecoration: "none",
              color: "inherit",
              "&:hover": { borderColor: cores.primariaBorda, bgcolor: cores.primariaFundo },
            }}
          >
            <Box sx={{ color: cores.primaria }}>{a.icone}</Box>
            <Typography sx={{ fontWeight: 600, fontSize: 15, color: cores.titulo }}>{a.titulo}</Typography>
            <Typography variant="body2" sx={{ color: cores.textoSecundario, display: { xs: "none", sm: "block" } }}>
              {a.texto}
            </Typography>
          </Box>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "3fr 2fr" }, gap: 4 }}>
        <Box component="section">
          <TituloSecao acao={<Link component={RouterLink} to="/historico" variant="body2">Ver histórico completo</Link>}>
            Continuar de onde parou
          </TituloSecao>
          {conversas.isLoading ? (
            <Skeleton variant="rounded" height={140} />
          ) : conversas.data?.results.length ? (
            <Box sx={{ display: "grid", gap: 1 }}>
              {conversas.data.results.map((c) => (
                <Box
                  key={c.id}
                  component={RouterLink}
                  to={`/assistente/${c.id}`}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    p: 1.75,
                    borderRadius: 2,
                    border: `1px solid ${cores.borda}`,
                    bgcolor: cores.superficie,
                    textDecoration: "none",
                    color: "inherit",
                    "&:hover": { borderColor: cores.bordaForte },
                  }}
                >
                  <MessageSquare size={18} color={cores.textoSecundario} aria-hidden />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography noWrap sx={{ fontWeight: 600, fontSize: 14 }}>
                      {c.titulo}
                    </Typography>
                    <Typography variant="caption">{relativo(c.ultima_mensagem_em)}</Typography>
                  </Box>
                  <Typography variant="body2" sx={{ color: cores.primariaHover, fontWeight: 500 }}>
                    Continuar
                  </Typography>
                </Box>
              ))}
            </Box>
          ) : (
            <Cartao>
              <EstadoVazio titulo="Nenhuma conversa ainda" texto="Faça uma pergunta ao assistente para começar." />
            </Cartao>
          )}

          <Box sx={{ mt: 4 }}>
            <TituloSecao acao={<Link component={RouterLink} to="/repositorio" variant="body2">Abrir repositório</Link>}>
              Documentos recentes
            </TituloSecao>
            <Cartao sx={{ p: 0 }}>
              {documentos.isLoading ? (
                <Skeleton variant="rectangular" height={200} />
              ) : documentos.data?.results.length ? (
                documentos.data.results.map((d, i) => (
                  <Box
                    key={d.id}
                    component={RouterLink}
                    to={`/documentos/${d.id}`}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1.5,
                      px: 2,
                      py: 1.5,
                      borderTop: i ? `1px solid ${cores.bordaSutil}` : "none",
                      textDecoration: "none",
                      color: "inherit",
                      "&:hover": { bgcolor: cores.fundo },
                    }}
                  >
                    <IconeArquivo tipo={d.tipo_arquivo} />
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography noWrap sx={{ fontSize: 14, fontWeight: 500 }}>
                        {d.titulo}
                      </Typography>
                      <Typography variant="caption">
                        {d.tipo_arquivo.toUpperCase()}, {d.setor_responsavel.sigla}, atualizado em {data(d.atualizado_em)}
                      </Typography>
                    </Box>
                    <ChipClassificacao valor={d.classificacao} />
                  </Box>
                ))
              ) : (
                <EstadoVazio titulo="Nenhum documento disponível" texto="Ainda não há documentos autorizados para o seu perfil." />
              )}
            </Cartao>
          </Box>
        </Box>

        <Box component="section">
          <TituloSecao acao={<Link component={RouterLink} to="/setores" variant="body2">Ver diretório</Link>}>
            Acesso rápido aos setores
          </TituloSecao>
          <Box sx={{ display: "grid", gap: 1 }}>
            {setores.isLoading && <Skeleton variant="rounded" height={160} />}
            {(setores.data?.results ?? []).map((s) => (
              <Cartao key={s.id} sx={{ p: 2 }}>
                <Typography sx={{ fontWeight: 600, fontSize: 14 }}>
                  {s.nome} <Box component="span" sx={{ color: cores.textoSecundario }}>({s.sigla})</Box>
                </Typography>
                <Typography variant="body2" sx={{ color: cores.textoSecundario, mt: 0.25 }}>
                  {s.descricao || s.competencias}
                </Typography>
                {s.canal_contato && (
                  <Typography variant="caption" component="p" sx={{ mt: 0.75 }}>
                    Contato: {s.canal_contato}
                  </Typography>
                )}
              </Cartao>
            ))}
          </Box>
        </Box>
      </Box>
    </Pagina>
  );
}
