"""
cliente_rudp.py — Cliente R-UDP com Go-Back-N

"""

import socket
import time
import os
import hashlib
import csv
import sys

# Cliente R-UDP:
# - usa UDP como transporte;
# - adiciona confiabilidade na aplicacao com Go-Back-N;
# - numera pacotes, calcula checksum, aguarda ACKs e retransmite por timeout;
# - salva metricas como retransmissoes, vazao e eficiencia.

HOST           = 'servidor'
PORTA          = 6000
AUTH           = "X-Custom-Auth: 20261005038 - Crisly"
TAMANHO_JANELA = 8       # N da janela GBN
TIMEOUT        = 0.5     # segundos por tentativa de ACK
CHUNK_SIZE     = 4096    # bytes por pacote de dados
LOG_CSV        = "log_cliente_rudp.csv"
MAX_RETRANS    = 5000    # limite de retransmissões para não travar
MAX_FIM_TENTATIVAS = 20  # limite de tentativas do sinal de FIM


def montar_pacote(seq: int, dados: bytes) -> bytes:
    """
    Monta um pacote de dados no formato: sequencia|checksum_md5|conteudo.

    O checksum permite que o servidor detecte corrupcao antes de aceitar o
    pacote e avancar a sequencia esperada.
    """
    cs = hashlib.md5(dados).hexdigest()
    return f"{seq}|{cs}|".encode() + dados


def iniciar_cliente():
    """
    Executa uma transferencia R-UDP completa.

    O arquivo e dividido em chunks, enviado por uma janela Go-Back-N e
    retransmitido a partir da base da janela sempre que ocorre timeout.
    """
    arquivo = "arquivo_teste.bin"
    tamanho_arq = os.path.getsize(arquivo)
    cenario = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("CENARIO", "NA")).upper()

    chunks = []
    with open(arquivo, "rb") as f:
        while True:
            bloco = f.read(CHUNK_SIZE)
            if not bloco:
                break
            chunks.append(bloco)

    total_pacotes = len(chunks)
    print(f"[CLIENTE R-UDP] Arquivo: {arquivo} ({tamanho_arq:,} bytes)")
    print(f"[CLIENTE R-UDP] Total de chunks: {total_pacotes} | Janela: {TAMANHO_JANELA} | Cenário: {cenario}")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(TIMEOUT)

        # ── Autenticação com retry limitado ───────────────────────────
        print("[AUTH] Enviando autenticação...")
        # Autenticacao com retry, pois o ACK_AUTH tambem pode se perder.
        auth_tentativas = 0
        while True:
            try:
                s.sendto(AUTH.encode(), (HOST, PORTA))
                resp, _ = s.recvfrom(1024)
                if resp == b"ACK_AUTH":
                    print("[AUTH] Confirmado.")
                    break
            except socket.timeout:
                auth_tentativas += 1
                print(f"[AUTH] Timeout, retentando... ({auth_tentativas})")
                if auth_tentativas > 30:
                    print("[AUTH] Falha — servidor não respondeu. Abortando.")
                    return

        # ── Go-Back-N ─────────────────────────────────────────────────
        # Estado da janela Go-Back-N.
        # base: primeiro pacote ainda nao confirmado.
        # proximo_envio: proximo pacote disponivel para envio.
        base           = 0
        proximo_envio  = 0
        retransmissoes = 0
        inicio         = time.time()
        log_eventos    = []

        while base < total_pacotes:
            # Envia pacotes da janela
            while proximo_envio < base + TAMANHO_JANELA and proximo_envio < total_pacotes:
                # Envia pacotes enquanto houver espaco na janela.
                pkt = montar_pacote(proximo_envio, chunks[proximo_envio])
                s.sendto(pkt, (HOST, PORTA))
                ts = round(time.time() - inicio, 6)
                log_eventos.append((ts, proximo_envio, "ENVIADO"))
                proximo_envio += 1

            # Aguarda ACK
            try:
                # Aguarda ACK cumulativo do servidor.
                ack_raw, _ = s.recvfrom(1024)

                # Ignora pacotes que não sejam ACK numérico
                try:
                    ack_num = int(ack_raw.decode())
                except ValueError:
                    continue

                ts = round(time.time() - inicio, 6)
                if ack_num >= base:
                    log_eventos.append((ts, ack_num, "ACK"))
                    base = ack_num + 1
                else:
                    log_eventos.append((ts, ack_num, "ACK_ANTIGO"))

            except socket.timeout:
                ts = round(time.time() - inicio, 6)
                janela_perdida = proximo_envio - base
                retransmissoes += janela_perdida
                log_eventos.append((ts, base, f"TIMEOUT_RETRANSMITE_{janela_perdida}_pkts"))
                print(f"[TIMEOUT] Retransmitindo seq {base} "
                      f"({janela_perdida} pkts, total retrans: {retransmissoes})")
                proximo_envio = base

                # Segurança: evita loop infinito em caso extremo
                if retransmissoes > MAX_RETRANS:
                    print(f"[AVISO] Limite de retransmissões atingido ({MAX_RETRANS}). Abortando.")
                    return

        # ── Envia sinal de FIM com limite de tentativas ───────────────
        print("[FIM] Enviando sinal de encerramento...")
        # Confirma explicitamente o fim da sessao para o servidor fechar a rodada.
        fim_ok = False
        for tentativa in range(MAX_FIM_TENTATIVAS):
            try:
                s.sendto(b"-1|FIM", (HOST, PORTA))
                resp, _ = s.recvfrom(1024)
                if resp == b"ACK_FIM":
                    print("[FIM] Confirmado pelo servidor.")
                    fim_ok = True
                    break
            except socket.timeout:
                print(f"[FIM] Timeout tentativa {tentativa+1}/{MAX_FIM_TENTATIVAS}...")

        if not fim_ok:
            print("[FIM] Servidor não confirmou FIM, mas transferência concluída.")

        # ── Métricas finais ───────────────────────────────────────────
        duracao       = time.time() - inicio
        vazao         = (tamanho_arq * 8) / (duracao * 1_000_000) if duracao > 0 else 0
        pkts_dados    = total_pacotes
        pkts_enviados = len([e for e in log_eventos if e[2] == "ENVIADO"])
        pkts_controle = len([e for e in log_eventos if "ACK" in e[2]])
        eficiencia    = pkts_dados / (pkts_enviados + pkts_controle) if (pkts_enviados + pkts_controle) > 0 else 0

        print("\n══════════════════════════════════════")
        print("  RESULTADOS — CLIENTE R-UDP")
        print("══════════════════════════════════════")
        print(f"  Arquivo         : {arquivo}")
        print(f"  Cenário         : {cenario}")
        print(f"  Tamanho         : {tamanho_arq:,} bytes")
        print(f"  Chunks enviados : {total_pacotes}")
        print(f"  Retransmissões  : {retransmissoes}")
        print(f"  Tempo total     : {duracao:.4f} s")
        print(f"  Vazão           : {vazao:.4f} Mbps")
        print(f"  Pkts dados      : {pkts_dados}")
        print(f"  Pkts controle   : {pkts_controle}")
        print(f"  Eficiência      : {eficiencia:.2%}")
        print("══════════════════════════════════════\n")

        # ── Grava CSV de eventos ──────────────────────────────────────
        with open(LOG_CSV, "w", newline="") as csvf:
            writer = csv.writer(csvf)
            writer.writerow(["timestamp_s", "seq", "evento"])
            writer.writerows(log_eventos)
        print(f"[LOG] {LOG_CSV} salvo com {len(log_eventos)} eventos.")

        # ── Grava resumo ──────────────────────────────────────────────
        escrever_header = not os.path.exists("resultado_rudp.csv") or \
                          os.path.getsize("resultado_rudp.csv") == 0
        with open("resultado_rudp.csv", "a", newline="") as rf:
            writer = csv.writer(rf)
            if escrever_header:
                writer.writerow([
                    "protocolo", "cenario", "tamanho_bytes", "tempo_s", "vazao_mbps",
                    "retransmissoes", "pkts_dados", "pkts_controle", "eficiencia"
                ])
            writer.writerow([
                "R-UDP", cenario, tamanho_arq, round(duracao, 6), round(vazao, 6),
                retransmissoes, pkts_dados, pkts_controle, round(eficiencia, 6)
            ])


if __name__ == "__main__":
    iniciar_cliente()
