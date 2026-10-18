import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/jetbrains-mono/500.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssBaseline, ThemeProvider } from "@mui/material";

import App from "./App";
import { ProvedorAutenticacao } from "./contexto/Autenticacao";
import tema from "./tema";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (falhas, erro: any) => falhas < 2 && !(erro?.status >= 400 && erro?.status < 500),
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={tema}>
        <CssBaseline />
        <BrowserRouter>
          <ProvedorAutenticacao>
            <App />
          </ProvedorAutenticacao>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
