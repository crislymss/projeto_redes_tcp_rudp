# Dockerfile — Ambiente de testes

FROM ubuntu:22.04

# Evita prompts interativos durante a instalacao dos pacotes.
ENV DEBIAN_FRONTEND=noninteractive

# Pacotes necessarios para:
# - executar os clientes/servidores Python;
# - configurar cenarios de rede com tc;
# - capturar trafego com tcpdump;
# - fazer testes basicos de conectividade.
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    iproute2 \
    tcpdump \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python para análise
RUN pip3 install --break-system-packages pandas plotly seaborn matplotlib 2>/dev/null || \
    pip3 install pandas plotly seaborn matplotlib

WORKDIR /app

# Mantem o container aberto em modo shell para execucao manual dos testes.
CMD ["bash"]
