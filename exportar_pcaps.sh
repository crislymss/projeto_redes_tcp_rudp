#!/bin/bash
# exportar_pcaps.sh — Exporta todos os PCAPs para CSV
# Projeto de Redes de Computadores — PPGCC/UFPI 2026-1
#
# COMO USAR:
#   chmod +x exportar_pcaps.sh
#   ./exportar_pcaps.sh

set -e

ENCONTROU=0

# Percorre todas as capturas geradas pelo experimento e cria um CSV para cada
# PCAP que ainda nao foi exportado.
for pcap in captura_*_cenario*.pcap; do
    [ -f "$pcap" ] || continue
    ENCONTROU=1
    csv="${pcap%.pcap}.csv"

    if [ -f "$csv" ]; then
        echo "[EXPORT] $csv já existe, pulando."
        continue
    fi

    echo "[EXPORT] $pcap → $csv"

    # Grava cabeçalho
    # Grava cabecalho do CSV de saida.
    echo "timestamp_s,src,dst,protocolo,ip_len,info" > "$csv"

    # Extrai campos com tcpdump -tt (timestamp unix) e -n (sem DNS)
    # Extrai campos com tcpdump -tt (timestamp Unix) e -n (sem DNS).
    tcpdump -tt -n -r "$pcap" -v 2>/dev/null | awk '
        /^reading from file/ { next }
        /^[0-9]/ {
            ts=$1
            ip_len=""
            src=""
            dst=""
            proto="IP"

            for (i=1; i<=NF; i++) {
                if ($i == "proto") {
                    proto=$(i+1)
                    gsub(/[(),]/, "", proto)
                }
                if ($i == "length" && ip_len == "") {
                    ip_len=$(i+1)
                    gsub(/[):,]/, "", ip_len)
                }
                if ($i == ">") {
                    src=$(i-1)
                    dst=$(i+1)
                    gsub(/:$/, "", dst)
                }
            }

            info=$0
            gsub(/"/, "\"\"", info)
            printf "%s,%s,%s,%s,%s,\"%s\"\n", ts, src, dst, proto, ip_len, info
        }
    ' >> "$csv"

    echo "[EXPORT] Concluído: $csv"
done

if [ $ENCONTROU -eq 0 ]; then
    echo "[EXPORT] Nenhum arquivo .pcap encontrado."
    echo "[EXPORT] Rode os testes primeiro."
    exit 1
fi

echo ""
echo "[EXPORT] Todos os PCAPs exportados para CSV."
echo "[EXPORT] Agora rode: python3 analisar_resultados.py"
