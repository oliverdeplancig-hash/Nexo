import { Box, Tooltip } from "@mui/material";

/**
 * Espaço reservado para a identidade visual da instituição.
 * Substitua o conteúdo por <img src="/marca-instituicao.svg" alt="..."> quando
 * a marca oficial for fornecida — o Nexo não cria logotipos institucionais.
 */
export default function MarcaInstitucional({ tamanho = 40, claro = false }: { tamanho?: number; claro?: boolean }) {
  return (
    <Tooltip title="Espaço reservado para a identidade visual da instituição">
      <Box
        role="img"
        aria-label="Identidade visual da instituição"
        sx={{
          width: tamanho,
          height: tamanho,
          flexShrink: 0,
          borderRadius: 1.5,
          display: "grid",
          placeItems: "center",
          bgcolor: claro ? "#0A1128" : "#F8FAFC",
          border: claro ? "none" : "1px dashed #94A3B8",
        }}
      >
        <svg width={tamanho * 0.62} height={tamanho * 0.62} viewBox="0 0 64 64" aria-hidden>
          <g fill="none" stroke={claro ? "#F8FAFC" : "#0A1128"} strokeWidth="5" strokeLinecap="round">
            <circle cx="20" cy="22" r="6" />
            <circle cx="44" cy="22" r="6" />
            <circle cx="32" cy="44" r="6" />
            <path d="M25 25l4 13M39 25l-4 13M26 22h12" />
          </g>
          <circle cx="32" cy="44" r="3" fill="#2563EB" />
        </svg>
      </Box>
    </Tooltip>
  );
}
