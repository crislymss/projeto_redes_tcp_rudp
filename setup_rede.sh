#!/bin/bash
# setup_rede.sh — Configuração de cenários de rede com tc (netem)
# Projeto de Redes de Computadores — PPGCC/UFPI 2026-1
#
# COMO USAR (dentro do container cliente ou servidor):
#   chmod +x setup_rede.sh
#   ./setup_rede.sh A    → Cenário A: 0% perda / 10ms delay
#   ./setup_rede.sh B    → Cenário B: 10% perda / 50ms delay
#   ./setup_rede.sh C    → Cenário C: 20% perda / 100ms delay
#   ./setup_rede.sh limpar → Remove qualquer regra tc

INTERFACE="eth0"

# Remove qualquer regra de controle de trafego aplicada anteriormente.
# Isso evita que um cenario herde delay/perda de outro teste.
limpar_tc() {
    echo "[TC] Removendo regras existentes em $INTERFACE..."
    tc qdisc del dev $INTERFACE root 2>/dev/null || true
    echo "[TC] Interface $INTERFACE limpa."
}

aplicar_cenario() {
    # Aplica perda e atraso artificiais com tc netem na interface escolhida.
    # Parametros:
    #   $1 -> nome do cenario
    #   $2 -> percentual de perda
    #   $3 -> atraso configurado
    local CENARIO=$1
    local PERDA=$2
    local DELAY=$3

    limpar_tc
    echo "[TC] Aplicando Cenário $CENARIO: perda=$PERDA delay=$DELAY na interface $INTERFACE"
    tc qdisc add dev $INTERFACE root netem delay $DELAY loss $PERDA
    echo "[TC] Regras ativas:"
    tc qdisc show dev $INTERFACE
    echo "[TC] Configuração concluída."
}

# Seleciona o cenario solicitado na linha de comando.
case "$1" in
    A|a) aplicar_cenario "A" "0%"  "10ms" ;;
    B|b) aplicar_cenario "B" "10%" "50ms" ;;
    C|c) aplicar_cenario "C" "20%" "100ms" ;;
    limpar|clean) limpar_tc ;;
    *)
        echo "Uso: $0 {A|B|C|limpar}"
        echo "  A → 0% perda  / 10ms delay"
        echo "  B → 10% perda / 50ms delay"
        echo "  C → 20% perda / 100ms delay"
        exit 1
        ;;
esac
