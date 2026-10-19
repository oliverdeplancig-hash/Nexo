import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";

import Layout from "./componentes/Layout";
import { useAutenticacao } from "./contexto/Autenticacao";
import { ProvedorEventos } from "./contexto/Eventos";
import Login from "./paginas/Login";
import PrimeiroAcesso from "./paginas/PrimeiroAcesso";
import { EsqueciSenha, RedefinirSenha } from "./paginas/RecuperarSenha";

const Dashboard = lazy(() => import("./paginas/Dashboard"));
const Chat = lazy(() => import("./paginas/Chat"));
const Repositorio = lazy(() => import("./paginas/Repositorio"));
const Documento = lazy(() => import("./paginas/Documento"));
const Busca = lazy(() => import("./paginas/Busca"));
const Setores = lazy(() => import("./paginas/Setores"));
const Importacao = lazy(() => import("./paginas/Importacao"));
const Administracao = lazy(() => import("./paginas/Administracao"));
const Auditoria = lazy(() => import("./paginas/Auditoria"));
const Regras = lazy(() => import("./paginas/Regras"));
const PainelAcervo = lazy(() => import("./paginas/PainelAcervo"));
const Notificacoes = lazy(() => import("./paginas/Notificacoes"));
const Perfil = lazy(() => import("./paginas/Perfil"));
const Historico = lazy(() => import("./paginas/Historico"));
const Colecoes = lazy(() => import("./paginas/Colecoes"));
const Ajuda = lazy(() => import("./paginas/Ajuda"));

function Carregando() {
  return (
    <Box sx={{ display: "grid", placeItems: "center", minHeight: "50vh" }} role="status" aria-label="Carregando">
      <CircularProgress size={28} />
    </Box>
  );
}

function Exige({ funcao, children }: { funcao: string | string[]; children: ReactNode }) {
  const { tem } = useAutenticacao();
  const lista = Array.isArray(funcao) ? funcao : [funcao];
  return lista.some(tem) ? <>{children}</> : <Navigate to="/" replace />;
}

export default function App() {
  const { usuario, carregando } = useAutenticacao();
  const local = useLocation();

  if (carregando) return <Carregando />;
  if (!usuario) {
    return (
      <Routes>
        <Route path="/entrar" element={<Login />} />
        <Route path="/esqueci-senha" element={<EsqueciSenha />} />
        <Route path="/redefinir-senha" element={<RedefinirSenha />} />
        <Route path="*" element={<Navigate to="/entrar" replace state={{ de: local.pathname }} />} />
      </Routes>
    );
  }

  // Senha temporária (ADR-018): nada além de criar a senha até que ela seja trocada.
  if (usuario.trocar_senha) return <PrimeiroAcesso />;

  return (
    <ProvedorEventos>
      <Layout>
        <Suspense fallback={<Carregando />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            {/* Rota única com parâmetro opcional: a tela não é remontada ao criar a conversa */}
            <Route path="/assistente/:conversaId?" element={<Chat />} />
            <Route path="/repositorio" element={<Repositorio />} />
            <Route path="/colecoes" element={<Colecoes />} />
            <Route path="/ajuda" element={<Ajuda />} />
            <Route path="/documentos/:id" element={<Documento />} />
            <Route path="/busca" element={<Busca />} />
            <Route path="/setores" element={<Setores />} />
            <Route path="/historico" element={<Historico />} />
            <Route path="/notificacoes" element={<Notificacoes />} />
            <Route path="/perfil" element={<Perfil />} />
            <Route path="/importacao" element={<Exige funcao="importar_documentos"><Importacao /></Exige>} />
            <Route path="/motor" element={<Exige funcao="gerir_regras"><Regras /></Exige>} />
            <Route path="/painel-acervo" element={<Exige funcao={["importar_documentos", "gerir_regras", "ver_auditoria"]}><PainelAcervo /></Exige>} />
            <Route
              path="/administracao"
              element={<Exige funcao={["admin_usuarios", "admin_permissoes"]}><Administracao /></Exige>}
            />
            <Route path="/auditoria" element={<Exige funcao="ver_auditoria"><Auditoria /></Exige>} />
            <Route path="/entrar" element={<Navigate to={(local.state as any)?.de ?? "/"} replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </Layout>
    </ProvedorEventos>
  );
}
