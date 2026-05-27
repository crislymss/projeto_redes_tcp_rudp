"""
cliente_tcp.py — Cliente TCP com registro de métricas

"""

import socket
import time
import os
import csv
import sys

# Cliente TCP:
# - conecta ao servico "servidor" definido no docker-compose.yml;
# - envia o cabecalho de autenticacao exigido no trabalho;
# - transmite arquivo_teste.bin em blocos;
# - salva metricas da rodada em CSV para analise posterior.

HOST   = 'servidor'
PORTA  = 5000
AUTH   = "X-Custom-Auth: 20261005038 - Crisly\n"
RESULTADO_CSV = "resultado_tcp.csv"


def iniciar_cliente():
    """
    Executa uma transferencia TCP completa e registra os resultados.

    O parametro do cenario pode ser informado pela linha de comando, como
    `python3 cliente_tcp.py A`, ou pela variavel de ambiente CENARIO.
    """
    arquivo     = "arquivo_teste.bin"
    tamanho_arq = os.path.getsize(arquivo)
    cenario     = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("CENARIO", "NA")).upper()

    print(f"[CLIENTE TCP] Arquivo: {arquivo} ({tamanho_arq:,} bytes)")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORTA))
        print(f"[CLIENTE TCP] Conectado ao servidor.")

        # ── Autenticação ──────────────────────────────────────────────
        # Envia a autenticacao antes dos bytes do arquivo.
        s.sendall(AUTH.encode())

        # ── Envia o arquivo e registra eventos ────────────────────────
        # Registra o instante relativo de cada bloco enviado.
        eventos = []
        inicio  = time.time()

        with open(arquivo, "rb") as f:
            while True:
                bloco = f.read(4096)
                if not bloco:
                    break
                s.sendall(bloco)
                ts = round(time.time() - inicio, 6)
                eventos.append((ts, len(bloco)))

        duracao = time.time() - inicio
        vazao   = (tamanho_arq * 8) / (duracao * 1_000_000) if duracao > 0 else 0

        print("\n══════════════════════════════════════")
        print("  RESULTADOS — CLIENTE TCP")
        print("══════════════════════════════════════")
        print(f"  Arquivo         : {arquivo}")
        print(f"  Tamanho         : {tamanho_arq:,} bytes")
        print(f"  Tempo total     : {duracao:.4f} s")
        print(f"  Vazão           : {vazao:.4f} Mbps")
        print("══════════════════════════════════════\n")

        # ── Grava CSV de eventos ──────────────────────────────────────
        with open("log_cliente_tcp.csv", "w", newline="") as csvf:
            writer = csv.writer(csvf)
            writer.writerow(["timestamp_s", "bytes_enviados_no_send"])
            writer.writerows(eventos)
        print("[LOG] log_cliente_tcp.csv salvo.")

        # ── Grava resumo para análise estatística ─────────────────────
        with open(RESULTADO_CSV, "a", newline="") as rf:
            writer = csv.writer(rf)
            if rf.tell() == 0:
                writer.writerow([
                    "protocolo", "cenario", "tamanho_bytes", "tempo_s", "vazao_mbps",
                    "retransmissoes", "pkts_dados", "pkts_controle", "eficiencia"
                ])
            writer.writerow([
                "TCP", cenario, tamanho_arq, round(duracao, 6), round(vazao, 6),
                0, 0, 0, 1.0   # sem retransmissões, sem controle de eficiência
            ])


if __name__ == "__main__":
    iniciar_cliente()
