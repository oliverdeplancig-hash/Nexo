import { useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  BottomNavigation,
  BottomNavigationAction,
  Box,
  Button,
  Drawer,
  IconButton,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import {
  Bell,
  Bot,
  ChevronsLeft,
  ChevronsRight,
  Clock,
  FileUp,
  FolderTree,
  HelpCircle,
  History,
  Library,
  LogOut,
  Menu,
  MessagesSquare,
  Plus,
  Search,
  Settings2,
  Share2,
  ShieldCheck,
  Star,
  UserRound,
  Users,
  Workflow,
} from "lucide-react";

import { api } from "../api/cliente";
import { useAutenticacao } from "../contexto/Autenticacao";
import { cores, medidas } from "../tema";
import MarcaInstitucional from "./MarcaInstitucional";

interface ItemMenu {
  rotulo: string;
  para: string;
  icone: ReactNode;
  funcao?: string | string[];
  atalho?: string;
  contador?: number;
}

function iniciais(nome: string) {
  return nome
    .replace(/[^\p{L}\s]/gu, "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export default function Layout({ children }: { children: ReactNode }) {
  const { usuario, sair, tem } = useAutenticacao();
  const navegar = useNavigate();
  const local = useLocation();
  const telaLarga = useMediaQuery("(min-width:1024px)");
  const celular = useMediaQuery("(max-width:767.95px)");
  const [recolhida, setRecolhida] = useState(false);
  const [aberta, setAberta] = useState(false);

  const { data: contagem } = useQuery({
    queryKey: ["notificacoes", "contagem"],
    queryFn: () => api<{ nao_lidas: number }>("/notificacoes/contagem/"),
    refetchInterval: 60_000,
  });

  const grupos: { titulo: string; itens: ItemMenu[] }[] = [
    {
      titulo: "Navegação principal",
      itens: [
        { rotulo: "Assistente IA", para: "/assistente", icone: <Bot size={18} /> },
        { rotulo: "Repositório documental", para: "/repositorio", icone: <Library size={18} /> },
        { rotulo: "Buscar documentos", para: "/busca", icone: <Search size={18} />, atalho: "Ctrl+K" },
        { rotulo: "Pastas e coleções", para: "/colecoes", icone: <FolderTree size={18} /> },
      ],
    },
    {
      titulo: "Acervo pessoal",
      itens: [
        { rotulo: "Documentos recentes", para: "/repositorio?aba=recentes", icone: <Clock size={18} /> },
        { rotulo: "Favoritos", para: "/repositorio?aba=favoritos", icone: <Star size={18} /> },
        { rotulo: "Compartilhados comigo", para: "/repositorio?aba=compartilhados", icone: <Share2 size={18} /> },
        { rotulo: "Histórico de conversas", para: "/historico", icone: <History size={18} /> },
      ],
    },
    {
      titulo: "Institucional",
      itens: [
        { rotulo: "Setores e contatos", para: "/setores", icone: <Users size={18} /> },
        { rotulo: "Notificações", para: "/notificacoes", icone: <Bell size={18} />, contador: contagem?.nao_lidas },
        { rotulo: "Ajuda", para: "/ajuda", icone: <HelpCircle size={18} /> },
      ],
    },
    {
      titulo: "Governança",
      itens: [
        { rotulo: "Importar documentos", para: "/importacao", icone: <FileUp size={18} />, funcao: "importar_documentos" },
        { rotulo: "Motor de respostas", para: "/motor", icone: <Workflow size={18} />, funcao: "gerir_regras" },
        { rotulo: "Administração", para: "/administracao", icone: <Settings2 size={18} />, funcao: ["admin_usuarios", "admin_permissoes"] },
        { rotulo: "Auditoria", para: "/auditoria", icone: <ShieldCheck size={18} />, funcao: "ver_auditoria" },
      ],
    },
  ];

  const permitido = (i: ItemMenu) => !i.funcao || (Array.isArray(i.funcao) ? i.funcao.some(tem) : tem(i.funcao));
  const compacta = telaLarga && recolhida;
  const largura = compacta ? medidas.barraLateralRecolhida : medidas.barraLateral;

  const ativo = (para: string) => {
    const [caminho, consulta] = para.split("?");
    if (consulta) return local.pathname === caminho && local.search.includes(consulta);
    if (caminho === "/repositorio") return local.pathname === caminho && !local.search.includes("aba=");
    return local.pathname === caminho || local.pathname.startsWith(`${caminho}/`);
  };

  const conteudoMenu = (
    <Box
      component="nav"
      aria-label="Menu principal"
      sx={{ width: largura, height: "100%", bgcolor: cores.barraLateral, color: cores.barraLateralTexto, display: "flex", flexDirection: "column" }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: compacta ? 2 : 2.5, py: 2.25, borderBottom: `1px solid ${cores.barraLateralHover}` }}>
        <MarcaInstitucional />
        {!compacta && (
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography sx={{ fontWeight: 700, fontSize: 17, lineHeight: "22px", letterSpacing: "-0.01em" }}>Nexo</Typography>
            <Typography sx={{ fontSize: 12, color: cores.barraLateralMudo }}>Assistente institucional</Typography>
          </Box>
        )}
        {telaLarga && (
          <IconButton
            size="small"
            onClick={() => setRecolhida(!recolhida)}
            aria-label={recolhida ? "Expandir menu" : "Recolher menu"}
            sx={{ color: cores.barraLateralMudo, ml: compacta ? 0 : "auto" }}
          >
            {recolhida ? <ChevronsRight size={18} /> : <ChevronsLeft size={18} />}
          </IconButton>
        )}
      </Box>

      <Box sx={{ px: compacta ? 1.5 : 2, pt: 2 }}>
        <Tooltip title={compacta ? "Nova conversa" : ""} placement="right">
          <Button
            fullWidth
            variant="contained"
            onClick={() => {
              navegar("/assistente", { state: { nova: Date.now() } });
              setAberta(false);
            }}
            startIcon={compacta ? undefined : <Plus size={18} />}
            aria-label="Nova conversa"
            sx={{ minWidth: 0, px: compacta ? 0 : 2 }}
          >
            {compacta ? <Plus size={18} /> : "Nova conversa"}
          </Button>
        </Tooltip>
      </Box>

      <Box sx={{ flex: 1, overflowY: "auto", px: compacta ? 1 : 1.5, py: 1 }}>
        {grupos.map((grupo) => {
          const itens = grupo.itens.filter(permitido);
          if (!itens.length) return null;
          return (
            <Box key={grupo.titulo} sx={{ mt: 1.5 }}>
              {!compacta && (
                <Typography component="h2" sx={{ px: 1.5, pb: 0.5, fontSize: 12, fontWeight: 600, color: cores.barraLateralMudo }}>
                  {grupo.titulo}
                </Typography>
              )}
              {itens.map((item) => (
                <Tooltip key={item.para} title={compacta ? item.rotulo : ""} placement="right">
                  <Box
                    component={NavLink}
                    to={item.para}
                    onClick={() => setAberta(false)}
                    aria-current={ativo(item.para) ? "page" : undefined}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1.5,
                      px: 1.5,
                      py: 1,
                      my: 0.25,
                      borderRadius: 2,
                      color: ativo(item.para) ? cores.barraLateralTexto : "#CBD5E1",
                      bgcolor: ativo(item.para) ? cores.barraLateralHover : "transparent",
                      boxShadow: ativo(item.para) ? `inset 3px 0 0 ${cores.primaria}` : "none",
                      textDecoration: "none",
                      fontSize: 14,
                      fontWeight: ativo(item.para) ? 600 : 500,
                      justifyContent: compacta ? "center" : "flex-start",
                      "&:hover": { bgcolor: cores.barraLateralHover, color: cores.barraLateralTexto },
                    }}
                  >
                    <Badge color="primary" badgeContent={compacta ? item.contador : 0} max={99}>
                      {item.icone}
                    </Badge>
                    {!compacta && <Box sx={{ flex: 1 }}>{item.rotulo}</Box>}
                    {!compacta && item.atalho && (
                      <Box component="kbd" sx={{ fontSize: 11, color: cores.barraLateralMudo, border: `1px solid ${cores.barraLateralHover}`, borderRadius: 1, px: 0.75 }}>
                        {item.atalho}
                      </Box>
                    )}
                    {!compacta && !!item.contador && (
                      <Box sx={{ bgcolor: cores.primaria, color: "#fff", borderRadius: 99, px: 0.9, fontSize: 12, fontWeight: 600 }}>{item.contador}</Box>
                    )}
                  </Box>
                </Tooltip>
              ))}
            </Box>
          );
        })}
      </Box>

      <Box sx={{ borderTop: `1px solid ${cores.barraLateralHover}`, p: compacta ? 1.5 : 2, display: "flex", alignItems: "center", gap: 1.5 }}>
        <Avatar
          component={NavLink}
          to="/perfil"
          aria-label="Perfil e configurações"
          sx={{ width: 36, height: 36, bgcolor: cores.primaria, fontSize: 14, fontWeight: 600, textDecoration: "none" }}
        >
          {iniciais(usuario?.nome ?? "")}
        </Avatar>
        {!compacta && (
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography noWrap sx={{ fontSize: 14, fontWeight: 600 }}>
              {usuario?.nome}
            </Typography>
            <Typography noWrap sx={{ fontSize: 12, color: cores.barraLateralMudo }}>
              {usuario?.setor?.sigla ?? "Sem setor"}
              {usuario?.perfis[0] ? `, ${usuario.perfis[0].nome}` : ""}
            </Typography>
          </Box>
        )}
        {!compacta && (
          <Tooltip title="Ajuda sobre esta tela">
            <IconButton component={NavLink} to={`/ajuda?de=${encodeURIComponent(local.pathname)}`} aria-label="Ajuda sobre esta tela" sx={{ color: cores.barraLateralMudo }}>
              <HelpCircle size={18} />
            </IconButton>
          </Tooltip>
        )}
        {!compacta && (
          <Tooltip title="Sair">
            <IconButton onClick={sair} aria-label="Sair" sx={{ color: cores.barraLateralMudo }}>
              <LogOut size={18} />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    </Box>
  );

  const abaInferior = ["/assistente", "/repositorio", "/busca", "/perfil"].find((p) => local.pathname.startsWith(p)) ?? false;

  return (
    <Box sx={{ display: "flex", minHeight: "100dvh" }}>
      {telaLarga ? (
        <Box sx={{ width: largura, flexShrink: 0, position: "sticky", top: 0, height: "100dvh", transition: "width .2s" }}>{conteudoMenu}</Box>
      ) : (
        <Drawer open={aberta} onClose={() => setAberta(false)} PaperProps={{ sx: { bgcolor: cores.barraLateral } }}>
          {conteudoMenu}
        </Drawer>
      )}

      <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        {!telaLarga && (
          <Box
            component="header"
            sx={{
              position: "sticky",
              top: 0,
              zIndex: 10,
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1,
              py: 1,
              bgcolor: cores.superficie,
              borderBottom: `1px solid ${cores.borda}`,
            }}
          >
            <IconButton onClick={() => setAberta(true)} aria-label="Abrir menu">
              <Menu size={22} />
            </IconButton>
            <MarcaInstitucional tamanho={28} claro />
            <Typography sx={{ fontWeight: 700, flex: 1 }}>Nexo</Typography>
            <IconButton component={NavLink} to={`/ajuda?de=${encodeURIComponent(local.pathname)}`} aria-label="Ajuda sobre esta tela">
              <HelpCircle size={20} />
            </IconButton>
            <IconButton component={NavLink} to="/notificacoes" aria-label="Notificações">
              <Badge color="primary" badgeContent={contagem?.nao_lidas ?? 0}>
                <Bell size={20} />
              </Badge>
            </IconButton>
          </Box>
        )}

        <Box component="main" id="conteudo" sx={{ flex: 1, minWidth: 0, pb: celular ? "72px" : 0 }}>
          {children}
        </Box>

        {celular && (
          <BottomNavigation
            component="nav"
            aria-label="Navegação rápida"
            showLabels
            value={abaInferior}
            onChange={(_, v) => navegar(v)}
            sx={{ position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 20, borderTop: `1px solid ${cores.borda}`, height: 64, pb: "env(safe-area-inset-bottom)" }}
          >
            <BottomNavigationAction value="/assistente" label="Assistente" icon={<MessagesSquare size={20} />} />
            <BottomNavigationAction value="/repositorio" label="Repositório" icon={<Library size={20} />} />
            <BottomNavigationAction value="/busca" label="Buscar" icon={<Search size={20} />} />
            <BottomNavigationAction value="/perfil" label="Perfil" icon={<UserRound size={20} />} />
          </BottomNavigation>
        )}
      </Box>
    </Box>
  );
}
