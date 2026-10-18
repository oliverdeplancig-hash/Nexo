import { createTheme } from "@mui/material/styles";

/** Tokens do design system "Institutional Intelligence" (stitch/DESIGN.md). */
export const cores = {
  barraLateral: "#0A1128",
  barraLateralPainel: "#0F172A",
  barraLateralHover: "#1E293B",
  barraLateralTexto: "#F8FAFC",
  barraLateralMudo: "#94A3B8",
  fundo: "#F8FAFC",
  superficie: "#FFFFFF",
  borda: "#E2E8F0",
  bordaSutil: "#F1F5F9",
  bordaForte: "#CBD5E1",
  primaria: "#2563EB",
  primariaHover: "#1D4ED8",
  primariaAtiva: "#1E40AF",
  primariaFundo: "#EFF6FF",
  primariaBorda: "#BFDBFE",
  titulo: "#0F172A",
  texto: "#1E293B",
  textoSecundario: "#475569",
  verificado: { texto: "#065F46", fundo: "#ECFDF5", borda: "#A7F3D0", forte: "#059669" },
  semantico: { texto: "#0E7490", fundo: "#ECFEFF", borda: "#A5F3FC", forte: "#0891B2" },
  cautela: { texto: "#92400E", fundo: "#FFFBEB", borda: "#FDE68A", forte: "#D97706" },
  erro: "#BA1A1A",
};

export const sombras = {
  n1: "0 1px 2px 0 rgba(15, 23, 42, 0.04)",
  n2: "0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04)",
  n3: "0 20px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.04)",
  foco: "0 0 0 2px #FFFFFF, 0 0 0 4px #2563EB",
};

export const medidas = { barraLateral: 280, barraLateralRecolhida: 80, painel: 380, conteudoMax: 896 };

export const fonteMono = '"JetBrains Mono", ui-monospace, monospace';

const tema = createTheme({
  palette: {
    mode: "light",
    primary: { main: cores.primaria, dark: cores.primariaHover, contrastText: "#FFFFFF" },
    secondary: { main: "#565E74" },
    error: { main: cores.erro },
    warning: { main: cores.cautela.forte },
    success: { main: cores.verificado.forte },
    background: { default: cores.fundo, paper: cores.superficie },
    text: { primary: cores.texto, secondary: cores.textoSecundario },
    divider: cores.borda,
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif',
    h1: { fontSize: 32, lineHeight: "40px", fontWeight: 700, letterSpacing: "-0.02em", color: cores.titulo },
    h2: { fontSize: 24, lineHeight: "32px", fontWeight: 600, letterSpacing: "-0.015em", color: cores.titulo },
    h3: { fontSize: 20, lineHeight: "28px", fontWeight: 600, letterSpacing: "-0.01em", color: cores.titulo },
    h4: { fontSize: 16, lineHeight: "24px", fontWeight: 600, color: cores.titulo },
    body1: { fontSize: 16, lineHeight: "26px" },
    body2: { fontSize: 14, lineHeight: "22px" },
    caption: { fontSize: 13, lineHeight: "18px", color: cores.textoSecundario },
    button: { textTransform: "none", fontWeight: 500, fontSize: 14 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { fontVariantNumeric: "tabular-nums", backgroundColor: cores.fundo },
        "@keyframes girar": { from: { transform: "rotate(0deg)" }, to: { transform: "rotate(360deg)" } },
        ".girando": { animation: "girar 1s linear infinite" },
        "*:focus-visible:not(input):not(textarea)": { outline: "none", boxShadow: sombras.foco, borderRadius: 4 },
        "input:focus-visible, textarea:focus-visible": { outline: "none" },
        "@media (prefers-reduced-motion: reduce)": {
          "*, *::before, *::after": { animationDuration: "0.01ms !important", transitionDuration: "0.01ms !important" },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { height: 40, padding: "0 16px", borderRadius: 8 },
        sizeSmall: { height: 32, padding: "0 12px" },
        containedPrimary: {
          border: `1px solid ${cores.primariaHover}`,
          "&:hover": { backgroundColor: cores.primariaHover },
          "&:active": { backgroundColor: cores.primariaAtiva },
        },
        outlined: {
          borderColor: cores.bordaForte,
          color: cores.titulo,
          backgroundColor: cores.superficie,
          "&:hover": { backgroundColor: cores.fundo, borderColor: "#94A3B8" },
        },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: { outlined: { borderColor: cores.borda, boxShadow: sombras.n1 } },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: cores.superficie,
          "& .MuiOutlinedInput-notchedOutline": { borderColor: cores.bordaForte },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": { borderColor: cores.primaria, borderWidth: 1 },
          "&.Mui-focused": { boxShadow: "0 0 0 3px rgba(37, 99, 235, 0.15)" },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 600, fontSize: 13, color: cores.textoSecundario, backgroundColor: cores.fundo },
        root: { borderColor: cores.bordaSutil, fontSize: 14 },
      },
    },
    MuiChip: { styleOverrides: { root: { borderRadius: 4, fontWeight: 500 } } },
    MuiTooltip: { styleOverrides: { tooltip: { fontSize: 12, backgroundColor: cores.barraLateralPainel } } },
    MuiDialog: { styleOverrides: { paper: { borderRadius: 12, boxShadow: sombras.n3, border: "1px solid #94A3B8" } } },
  },
});

export default tema;
