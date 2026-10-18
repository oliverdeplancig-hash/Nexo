/**
 * Conexão WebSocket com reconexão automática (backoff exponencial com teto)
 * e batimento (ping) para detectar quedas silenciosas.
 */

export type EstadoConexao = "conectando" | "conectado" | "reconectando" | "desconectado";

type Ouvinte = (evento: Record<string, any>) => void;

export class SocketNexo {
  private ws: WebSocket | null = null;
  private tentativas = 0;
  private encerrado = false;
  private batimento: number | undefined;
  private ouvintes = new Set<Ouvinte>();
  private ouvintesEstado = new Set<(e: EstadoConexao) => void>();
  private fila: string[] = [];
  estado: EstadoConexao = "desconectado";

  constructor(private caminho: string) {}

  conectar() {
    this.encerrado = false;
    this.mudarEstado(this.tentativas ? "reconectando" : "conectando");
    const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocolo}://${window.location.host}${this.caminho}`);
    this.ws = ws;
    ws.onopen = () => {
      this.tentativas = 0;
      this.mudarEstado("conectado");
      this.fila.splice(0).forEach((m) => ws.send(m));
      window.clearInterval(this.batimento);
      this.batimento = window.setInterval(() => this.enviar({ tipo: "ping" }), 25000);
    };
    ws.onmessage = (e) => {
      try {
        const dado = JSON.parse(e.data);
        this.ouvintes.forEach((o) => o(dado));
      } catch {
        /* mensagem inválida é ignorada */
      }
    };
    ws.onclose = (e) => {
      window.clearInterval(this.batimento);
      if (this.encerrado || e.code === 4401) {
        this.mudarEstado("desconectado");
        if (e.code === 4401) window.dispatchEvent(new CustomEvent("nexo:sessao-expirada"));
        return;
      }
      this.tentativas += 1;
      this.mudarEstado("reconectando");
      const espera = Math.min(15000, 500 * 2 ** this.tentativas) + Math.random() * 300;
      window.setTimeout(() => !this.encerrado && this.conectar(), espera);
    };
  }

  enviar(dado: Record<string, unknown>) {
    const texto = JSON.stringify(dado);
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(texto);
    else if (dado.tipo !== "ping") this.fila.push(texto);
  }

  ouvir(o: Ouvinte) {
    this.ouvintes.add(o);
    return () => this.ouvintes.delete(o);
  }

  ouvirEstado(o: (e: EstadoConexao) => void) {
    this.ouvintesEstado.add(o);
    return () => this.ouvintesEstado.delete(o);
  }

  encerrar() {
    this.encerrado = true;
    window.clearInterval(this.batimento);
    this.ws?.close();
  }

  private mudarEstado(e: EstadoConexao) {
    this.estado = e;
    this.ouvintesEstado.forEach((o) => o(e));
  }
}
