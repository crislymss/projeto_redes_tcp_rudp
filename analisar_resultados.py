#!/usr/bin/env python3
"""
Consolida os resultados da aplicacao e dos CSVs exportados do tcpdump.

Saidas:
- estatisticas_resumo.csv: media/desvio por protocolo e cenario.
- validacao_cruzada.csv: bytes/tempo da aplicacao versus tcpdump.
"""

import csv
import glob
import math
import os
import re
from collections import defaultdict


CENARIOS_PADRAO = ["A", "B", "C"]


def media(valores):
    """Calcula a media aritmetica de uma lista numerica."""
    return sum(valores) / len(valores) if valores else 0.0


def desvio(valores):
    """Calcula o desvio padrao amostral de uma lista numerica."""
    if len(valores) < 2:
        return 0.0
    m = media(valores)
    return math.sqrt(sum((v - m) ** 2 for v in valores) / (len(valores) - 1))


def numero(valor, padrao=0.0):
    """Converte valores vindos de CSV para float com fallback seguro."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def ler_resultado_app(caminho, protocolo):
    """
    Le os CSVs gerados pelos clientes TCP/R-UDP.

    Aceita o formato atual com cabecalho e tambem um formato antigo sem
    cabecalho, mantendo compatibilidade com execucoes anteriores.
    """
    if not os.path.exists(caminho):
        return []

    with open(caminho, newline="") as f:
        linhas = list(csv.reader(f))

    if not linhas:
        return []

    cabecalho = [c.strip().lower() for c in linhas[0]]
    tem_cabecalho = "protocolo" in cabecalho and "tempo_s" in cabecalho
    dados = linhas[1:] if tem_cabecalho else linhas
    registros = []

    for idx, row in enumerate(dados):
        if not row:
            continue

        if tem_cabecalho:
            item = dict(zip(cabecalho, row))
            cenario = item.get("cenario") or CENARIOS_PADRAO[idx % len(CENARIOS_PADRAO)]
            registros.append({
                "protocolo": item.get("protocolo", protocolo),
                "cenario": cenario.upper(),
                "tamanho_bytes": numero(item.get("tamanho_bytes")),
                "tempo_s": numero(item.get("tempo_s")),
                "vazao_mbps": numero(item.get("vazao_mbps")),
                "retransmissoes": numero(item.get("retransmissoes")),
                "pkts_dados": numero(item.get("pkts_dados")),
                "pkts_controle": numero(item.get("pkts_controle")),
                "eficiencia": numero(item.get("eficiencia")),
            })
        else:
            # Formato antigo: protocolo,tamanho,tempo,vazao,retrans,pkts_dados,pkts_controle,eficiencia
            cenario = CENARIOS_PADRAO[idx % len(CENARIOS_PADRAO)]
            registros.append({
                "protocolo": row[0] if len(row) > 0 else protocolo,
                "cenario": cenario,
                "tamanho_bytes": numero(row[1] if len(row) > 1 else 0),
                "tempo_s": numero(row[2] if len(row) > 2 else 0),
                "vazao_mbps": numero(row[3] if len(row) > 3 else 0),
                "retransmissoes": numero(row[4] if len(row) > 4 else 0),
                "pkts_dados": numero(row[5] if len(row) > 5 else 0),
                "pkts_controle": numero(row[6] if len(row) > 6 else 0),
                "eficiencia": numero(row[7] if len(row) > 7 else 0),
            })

    return registros


def ler_tcpdump_csvs():
    """
    Le os CSVs exportados das capturas PCAP.

    Para cada arquivo, extrai protocolo, cenario, bytes capturados, tempo
    observado e quantidade de pacotes.
    """
    registros = []
    padrao = re.compile(r"captura_(tcp|rudp)_cenario([abc])_", re.IGNORECASE)

    for caminho in glob.glob("captura_*_cenario*.csv"):
        nome = os.path.basename(caminho)
        match = padrao.search(nome)
        if not match:
            continue

        protocolo = "R-UDP" if match.group(1).lower() == "rudp" else "TCP"
        cenario = match.group(2).upper()
        timestamps = []
        bytes_ip = 0.0
        pacotes = 0

        with open(caminho, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = numero(row.get("timestamp_s"), None)
                ip_len = numero(row.get("ip_len"), 0.0)
                if ts is not None:
                    timestamps.append(ts)
                bytes_ip += ip_len
                pacotes += 1

        tempo = (max(timestamps) - min(timestamps)) if len(timestamps) >= 2 else 0.0
        registros.append({
            "arquivo": nome,
            "protocolo": protocolo,
            "cenario": cenario,
            "bytes_pcap": bytes_ip,
            "tempo_pcap": tempo,
            "pacotes_pcap": pacotes,
        })

    return registros


def agrupar_app(registros):
    """Agrupa os resultados da aplicacao por protocolo e cenario."""
    grupos = defaultdict(list)
    for item in registros:
        grupos[(item["protocolo"], item["cenario"])].append(item)
    return grupos


def escrever_estatisticas(grupos):
    """Gera estatisticas_resumo.csv com medias e desvios por grupo."""
    campos = [
        "protocolo", "cenario", "amostras",
        "vazao_media_mbps", "vazao_desvio_mbps",
        "tempo_medio_s", "tempo_desvio_s",
        "retrans_media", "retrans_desvio",
        "eficiencia_media",
    ]

    with open("estatisticas_resumo.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for (protocolo, cenario), itens in sorted(grupos.items()):
            writer.writerow({
                "protocolo": protocolo,
                "cenario": cenario,
                "amostras": len(itens),
                "vazao_media_mbps": round(media([i["vazao_mbps"] for i in itens]), 6),
                "vazao_desvio_mbps": round(desvio([i["vazao_mbps"] for i in itens]), 6),
                "tempo_medio_s": round(media([i["tempo_s"] for i in itens]), 6),
                "tempo_desvio_s": round(desvio([i["tempo_s"] for i in itens]), 6),
                "retrans_media": round(media([i["retransmissoes"] for i in itens]), 6),
                "retrans_desvio": round(desvio([i["retransmissoes"] for i in itens]), 6),
                "eficiencia_media": round(media([i["eficiencia"] for i in itens]), 6),
            })


def escrever_validacao(grupos_app, pcaps):
    """
    Gera validacao_cruzada.csv comparando aplicacao e tcpdump.

    A comparacao ajuda a observar overhead de bytes e diferencas de tempo entre
    a metrica medida pela aplicacao e a metrica observada na captura.
    """
    campos = [
        "protocolo", "cenario", "arquivo_pcap_csv",
        "bytes_app_medio", "bytes_pcap", "overhead_bytes_pct",
        "tempo_app_medio_s", "tempo_pcap_s", "delta_tempo_ms",
        "pacotes_pcap",
    ]

    with open("validacao_cruzada.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()

        for pcap in sorted(pcaps, key=lambda x: (x["protocolo"], x["cenario"], x["arquivo"])):
            itens = grupos_app.get((pcap["protocolo"], pcap["cenario"]), [])
            if not itens:
                continue

            bytes_app = media([i["tamanho_bytes"] for i in itens])
            tempo_app = media([i["tempo_s"] for i in itens])
            overhead = ((pcap["bytes_pcap"] - bytes_app) / bytes_app * 100) if bytes_app else 0.0
            delta_ms = (pcap["tempo_pcap"] - tempo_app) * 1000

            writer.writerow({
                "protocolo": pcap["protocolo"],
                "cenario": pcap["cenario"],
                "arquivo_pcap_csv": pcap["arquivo"],
                "bytes_app_medio": round(bytes_app, 2),
                "bytes_pcap": round(pcap["bytes_pcap"], 2),
                "overhead_bytes_pct": round(overhead, 4),
                "tempo_app_medio_s": round(tempo_app, 6),
                "tempo_pcap_s": round(pcap["tempo_pcap"], 6),
                "delta_tempo_ms": round(delta_ms, 3),
                "pacotes_pcap": pcap["pacotes_pcap"],
            })


def main():
    """Ponto de entrada: consolida resultados e escreve os CSVs finais."""
    app = []
    app.extend(ler_resultado_app("resultado_tcp.csv", "TCP"))
    app.extend(ler_resultado_app("resultado_rudp.csv", "R-UDP"))

    if not app:
        raise SystemExit("Nenhum resultado da aplicacao encontrado.")

    grupos = agrupar_app(app)
    escrever_estatisticas(grupos)

    pcaps = ler_tcpdump_csvs()
    if pcaps:
        escrever_validacao(grupos, pcaps)
        print("Gerados: estatisticas_resumo.csv e validacao_cruzada.csv")
    else:
        print("Gerado: estatisticas_resumo.csv")
        print("Aviso: nenhum CSV de tcpdump encontrado. Exporte os PCAPs com ./captura.sh exportar.")


if __name__ == "__main__":
    main()
