"""
servidor_tcp.py — Servidor TCP com registro de métricas
Aceita múltiplas conexões seguidas (necessário para repetições de teste)

"""

import socket
import time
import csv
import os

# Servidor TCP:
# - escuta conexoes na porta 5000;
# - recebe primeiro a autenticacao enviada pelo cliente;
# - grava o arquivo recebido em recebido_tcp.bin;
# - registra metricas e eventos para comparacao com os demais testes.

PORTA   = 5000
LOG_CSV = "log_servidor_tcp.csv"


def iniciar_servidor():
    """
    Inicia o servidor TCP e processa multiplas rodadas em sequencia.

    O processo fica ativo ate Ctrl+C. Cada conexao aceita corresponde a uma
    execucao do cliente TCP.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Permite reiniciar o servidor sem esperar a liberacao da porta.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', PORTA))
        s.listen(1)
        print(f"[SERVIDOR TCP] Aguardando conexões na porta {PORTA}...")
        print(f"[SERVIDOR TCP] Ctrl+C para parar após os testes.\n")

        rodada = 0

        while True:
            try:
                conn, addr = s.accept()
            except KeyboardInterrupt:
                print("\n[SERVIDOR TCP] Encerrado.")
                break

            rodada += 1
            print(f"[SERVIDOR TCP] Rodada {rodada} — Conectado: {addr}")

            with conn:
                # ── Autenticação ──────────────────────────────────────
                # Primeira mensagem esperada: cabecalho de autenticacao.
                auth = conn.recv(1024).decode(errors='replace').strip()
                print(f"[AUTH] {auth}")

                # ── Recebe arquivo ────────────────────────────────────
                # Recebe dados ate o cliente fechar a conexao.
                total_bytes = 0
                eventos     = []
                inicio      = time.time()

                with open("recebido_tcp.bin", "wb") as f:
                    while True:
                        dados = conn.recv(4096)
                        if not dados:
                            break
                        f.write(dados)
                        total_bytes += len(dados)
                        ts = round(time.time() - inicio, 6)
                        eventos.append((ts, len(dados), total_bytes))

                duracao = time.time() - inicio
                vazao   = (total_bytes * 8) / (duracao * 1_000_000) if duracao > 0 else 0

                print("══════════════════════════════════════")
                print(f"  RESULTADOS — SERVIDOR TCP (rodada {rodada})")
                print("══════════════════════════════════════")
                print(f"  Bytes recebidos : {total_bytes:,} bytes")
                print(f"  Duração total   : {duracao:.4f} s")
                print(f"  Vazão estimada  : {vazao:.4f} Mbps")
                print("══════════════════════════════════════\n")

                # ── Grava CSV de eventos (sobrescreve a cada rodada) ──
                with open(LOG_CSV, "w", newline="") as csvf:
                    writer = csv.writer(csvf)
                    writer.writerow(["timestamp_s", "bytes_recebidos_no_recv", "total_acumulado"])
                    writer.writerows(eventos)
                print(f"[LOG] {LOG_CSV} salvo ({len(eventos)} recebimentos).\n")


if __name__ == "__main__":
    iniciar_servidor()
