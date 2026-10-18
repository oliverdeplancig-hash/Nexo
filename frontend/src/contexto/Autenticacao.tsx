import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { api } from "../api/cliente";
import type { Usuario } from "../api/tipos";

interface ValorAutenticacao {
  usuario: Usuario | null;
  carregando: boolean;
  entrar: (usuario: string, senha: string) => Promise<void>;
  sair: () => Promise<void>;
  tem: (funcao: string) => boolean;
}

const Contexto = createContext<ValorAutenticacao | null>(null);

export function ProvedorAutenticacao({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    api<Usuario>("/auth/eu/")
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCarregando(false));
    const expirou = () => {
      setUsuario(null);
      queryClient.clear();
    };
    window.addEventListener("nexo:sessao-expirada", expirou);
    return () => window.removeEventListener("nexo:sessao-expirada", expirou);
  }, [queryClient]);

  const entrar = useCallback(async (login: string, senha: string) => {
    const dados = await api<Usuario>("/auth/entrar/", { method: "POST", json: { usuario: login, senha } });
    setUsuario(dados);
  }, []);

  const sair = useCallback(async () => {
    try {
      await api("/auth/sair/", { method: "POST" });
    } finally {
      queryClient.clear();
      setUsuario(null);
    }
  }, [queryClient]);

  const valor = useMemo<ValorAutenticacao>(
    () => ({ usuario, carregando, entrar, sair, tem: (f) => !!usuario?.funcoes.includes(f) }),
    [usuario, carregando, entrar, sair],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAutenticacao() {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error("useAutenticacao fora do provedor");
  return ctx;
}
