import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Alert, Snackbar } from "@mui/material";

import { SocketNexo } from "../api/socket";

const Contexto = createContext<SocketNexo | null>(null);

/** Canal de eventos do usuário: notificações e progresso de processamento. */
export function ProvedorEventos({ children }: { children: ReactNode }) {
  const socket = useRef<SocketNexo | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const queryClient = useQueryClient();

  if (!socket.current) socket.current = new SocketNexo("/ws/eventos/");

  useEffect(() => {
    const s = socket.current!;
    s.conectar();
    const parar = s.ouvir((evento) => {
      if (evento.tipo === "notificacao") {
        setAviso(evento.notificacao.titulo);
        queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
      }
      if (evento.tipo === "processamento") {
        queryClient.invalidateQueries({ queryKey: ["fila"] });
      }
    });
    return () => {
      parar();
      s.encerrar();
    };
  }, [queryClient]);

  return (
    <Contexto.Provider value={socket.current}>
      {children}
      <Snackbar open={!!aviso} autoHideDuration={5000} onClose={() => setAviso(null)} anchorOrigin={{ vertical: "bottom", horizontal: "right" }}>
        <Alert severity="info" variant="filled" onClose={() => setAviso(null)} sx={{ bgcolor: "#0F172A" }}>
          {aviso}
        </Alert>
      </Snackbar>
    </Contexto.Provider>
  );
}

export function useEventos() {
  return useContext(Contexto);
}
