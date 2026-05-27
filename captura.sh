#!/bin/bash
# captura.sh — Captura de tráfego com tcpdump e exportação CSV
# Projeto de Redes de Computadores — PPGCC/UFPI 2026-1
#
# COMO USAR (dentro do container servidor):
#   chmod +x captura.sh
#   ./captura.sh tcp A                         → captura TCP no cenário A
#   ./captura.sh rudp B                        → captura R-UDP no cenário B
#   ./captura.sh exportar arquivo.pcap saida.csv → exporta PCAP para CSV
#
# A captura fica em background; para encerrar use: kill $(cat captura.pid)

INTERFACE="eth0"
PROTOCOLO=${1:-tcp}     # "tcp" ou "rudp"
CENARIO=${2:-A}         # "A", "B" ou "C"

exportar_csv() {
    # Converte uma captura PCAP em CSV usando tcpdump e awk.
    # O CSV gerado e usado posteriormente por analisar_resultados.py.
    local PCAP_FILE=$1
    local CSV_FILE=$2

    if [ -z "$PCAP_FILE" ] || [ -z "$CSV_FILE" ]; then
        echo "Uso: $0 exportar arquivo.pcap saida.csv"
        exit 1
    fi

    if [ ! -f "$PCAP_FILE" ]; then
        echo "Arquivo PCAP não encontrado: $PCAP_FILE"
        exit 1
    fi

    echo "timestamp_s,src,dst,protocolo,ip_len,info" > "$CSV_FILE"
    tcpdump -tt -n -r "$PCAP_FILE" -v 2>/dev/null | awk '
        /^reading from file/ { next }
        /^[0-9]/ {
            ts=$1
            proto="IP"
            ip_len=""
            src=""
            dst=""

            for (i=1; i<=NF; i++) {
                if ($i == "proto") {
                    proto=$(i+1)
                    gsub(/[(),]/, "", proto)
                }
                if ($i == "length" && ip_len == "") {
                    ip_len=$(i+1)
                    gsub(/[):,]/, "", ip_len)
                    src=$(i+2)
                    dst=$(i+4)
                    gsub(/:$/, "", dst)
                }
            }

            info=$0
            gsub(/"/, "\"\"", info)
            printf "%s,%s,%s,%s,%s,\"%s\"\n", ts, src, dst, proto, ip_len, info
        }
    ' >> "$CSV_FILE"

    echo "[TCPDUMP] CSV exportado: $CSV_FILE"
}

# Modo de exportacao manual: ./captura.sh exportar entrada.pcap saida.csv
if [ "$PROTOCOLO" = "exportar" ]; then
    exportar_csv "$2" "$3"
    exit 0
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
NOME_BASE="captura_${PROTOCOLO}_cenario${CENARIO}_${TIMESTAMP}"
PCAP_FILE="${NOME_BASE}.pcap"
CSV_FILE="${NOME_BASE}.csv"

# Define filtro de porta conforme o protocolo
if [ "$PROTOCOLO" = "tcp" ]; then
    FILTRO="port 5000"
elif [ "$PROTOCOLO" = "rudp" ]; then
    FILTRO="udp port 6000"
else
    echo "Protocolo inválido. Use: tcp ou rudp"
    exit 1
fi

echo "============================================"
echo " Iniciando captura tcpdump"
echo " Protocolo : $PROTOCOLO  |  Cenário : $CENARIO"
echo " Interface : $INTERFACE"
echo " Filtro    : $FILTRO"
echo " Saída PCAP: $PCAP_FILE"
echo "============================================"

# Captura em background e salva o PID para encerramento posterior.
tcpdump -i $INTERFACE -w $PCAP_FILE $FILTRO &
echo $! > captura.pid
echo "[TCPDUMP] Captura iniciada (PID: $(cat captura.pid))"
echo "[TCPDUMP] Para encerrar: kill \$(cat captura.pid)"
echo ""
echo ">>> Execute o cliente agora. Ao terminar, encerre a captura."
echo ">>> Depois execute: ./captura.sh exportar $PCAP_FILE $CSV_FILE"
