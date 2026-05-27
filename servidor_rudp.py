"""
servidor_rudp.py — Servidor R-UDP com Go-Back-N
Aceita múltiplas sessões seguidas (necessário para repetições de teste)

"""

import socket
import hashlib
import csv
import time

# Servidor R-UDP:
# - recebe pacotes UDP na porta 6000;
# - usa ACKs cumulativos para confirmar o ultimo pacote em ordem;
# - descarta pacotes corrompidos ou fora de ordem;
# - grava o arquivo reconstruido em recebido_rudp.bin.

PORTA       = 6000
BUFFER_SIZE = 4200
LOG_CSV     = "log_servidor_rudp.csv"


def iniciar_servidor():
    """
    Inicia o servidor R-UDP e processa sessoes em sequencia.

    Uma sessao comeca quando chega a autenticacao X-Custom-Auth e termina ao
    receber o pacote especial b"-1|FIM".
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('0.0.0.0', PORTA))
        print("[SERVIDOR R-UDP] Aguardando conexões na porta", PORTA)
        print("[SERVIDOR R-UDP] Ctrl+C para parar após os testes.\n")

        rodada = 0

        while True:
            # ── Autenticação ──────────────────────────────────────────
            try:
                # Aguarda autenticacao para iniciar uma nova rodada.
                auth_data, addr = s.recvfrom(1024)
            except KeyboardInterrupt:
                print("\n[SERVIDOR R-UDP] Encerrado.")
                break

            # Ignora pacotes que não sejam autenticação
            # Pacotes sem autenticacao sao ignorados ate uma sessao iniciar.
            if b"X-Custom-Auth" not in auth_data:
                continue

            rodada += 1
            auth_str = auth_data.decode(errors='replace')
            print(f"[SERVIDOR R-UDP] Rodada {rodada} — {addr}")
            print(f"[AUTH] {auth_str}")
            s.sendto(b"ACK_AUTH", addr)

            esperado    = 0
            total_bytes = 0
            eventos     = []
            inicio      = time.time()

            with open("recebido_rudp.bin", "wb") as f:
                while True:
                    try:
                        pacote, addr = s.recvfrom(BUFFER_SIZE)
                    except Exception as e:
                        print(f"[ERRO recvfrom] {e}")
                        continue

                    ts = round(time.time() - inicio, 6)

                    # ── Sinal de FIM ──────────────────────────────────
                    # Sinal de encerramento enviado pelo cliente.
                    if pacote == b"-1|FIM":
                        s.sendto(b"ACK_FIM", addr)
                        print(f"[FIM] Recebido sinal de encerramento (rodada {rodada}).")
                        break

                    # Se o ACK_AUTH se perder no cenario com perda, o cliente
                    # reenvia a autenticacao. Confirma de novo e segue
                    # aguardando dados da mesma rodada.
                    if b"X-Custom-Auth" in pacote:
                        s.sendto(b"ACK_AUTH", addr)
                        eventos.append((ts, esperado, "AUTH_DUPLICADO"))
                        continue

                    try:
                        partes = pacote.split(b'|', 2)
                        if len(partes) != 3:
                            raise ValueError("Formato de pacote inválido")

                        seq               = int(partes[0].decode())
                        checksum_recebido = partes[1].decode()
                        conteudo          = partes[2]
                        checksum_local    = hashlib.md5(conteudo).hexdigest()
                        integro           = (checksum_recebido == checksum_local)

                        # Pacote correto: grava os dados e avanca o ACK.
                        if integro and seq == esperado:
                            f.write(conteudo)
                            total_bytes += len(conteudo)
                            s.sendto(str(esperado).encode(), addr)
                            eventos.append((ts, seq, "OK"))
                            esperado += 1

                        # Pacote duplicado: reenvia o ultimo ACK valido.
                        elif integro and seq < esperado:
                            s.sendto(str(esperado - 1).encode(), addr)
                            eventos.append((ts, seq, "DUPLICADO"))

                        # Pacote corrompido ou fora de ordem: descarta e
                        # informa o ultimo pacote recebido corretamente.
                        else:
                            ack_nak = esperado - 1
                            s.sendto(str(ack_nak).encode(), addr)
                            status = "CORROMPIDO" if not integro else "FORA_DE_ORDEM"
                            eventos.append((ts, seq, status))

                    except Exception as e:
                        print(f"[ERRO parse] {e}")
                        ack_nak = esperado - 1
                        s.sendto(str(ack_nak).encode(), addr)

            duracao = time.time() - inicio
            vazao   = (total_bytes * 8) / (duracao * 1_000_000) if duracao > 0 else 0
            ok_ct   = sum(1 for e in eventos if e[2] == "OK")
            dup_ct  = sum(1 for e in eventos if e[2] == "DUPLICADO")
            err_ct  = sum(1 for e in eventos if e[2] not in ("OK", "DUPLICADO"))

            print("══════════════════════════════════════")
            print(f"  RESULTADOS — SERVIDOR R-UDP (rodada {rodada})")
            print("══════════════════════════════════════")
            print(f"  Bytes recebidos : {total_bytes:,} bytes")
            print(f"  Duração total   : {duracao:.4f} s")
            print(f"  Vazão estimada  : {vazao:.4f} Mbps")
            print(f"  Pacotes OK      : {ok_ct}")
            print(f"  Duplicatas      : {dup_ct}")
            print(f"  Erros/descarte  : {err_ct}")
            print("══════════════════════════════════════\n")

            with open(LOG_CSV, "w", newline="") as csvf:
                writer = csv.writer(csvf)
                writer.writerow(["timestamp_s", "seq", "status"])
                writer.writerows(eventos)
            print(f"[LOG] {LOG_CSV} salvo ({len(eventos)} eventos).\n")


if __name__ == "__main__":
    iniciar_servidor()
