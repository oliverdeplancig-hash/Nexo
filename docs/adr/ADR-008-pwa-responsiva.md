# ADR-008 — Versão mobile como PWA responsiva

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
A especificação pede versões desktop, notebook, tablet e smartphone. Há um único desenvolvedor.

## Decisão
Um único frontend React + MUI responsivo, instalável como **PWA** (`vite-plugin-pwa`). No celular: menu
recolhível, navegação inferior, tabelas como cartões e compositor do chat fixo. O service worker guarda
apenas a casca do app — nenhuma resposta da API ou documento é armazenado no dispositivo.

## Alternativas consideradas
- **App nativo Expo/React Native:** rejeitado agora — segunda base de código e distribuição por lojas/MDM.
- **Site só responsivo, sem PWA:** rejeitado — perde instalação e atalho na tela inicial.

## Consequências
- Funciona offline apenas para abrir o app; consultas exigem conexão.
- Backlog: notificações push (Web Push) mediante avaliação de segurança.
