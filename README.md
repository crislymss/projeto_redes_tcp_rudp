# Projeto de Redes de Computadores — PPGCC/UFPI 2026-1

Implementação experimental de transferência de arquivos usando sockets TCP e um protocolo confiável sobre UDP (R-UDP), com execução em Docker, simulação de cenários de rede, captura de tráfego com `tcpdump` e análise estatística dos resultados.

**Aluno:** Crisly Maria Silva dos Santos
**Matrícula:** 20261005038
**Autenticação usada nos testes:** `X-Custom-Auth: 20261005038 - Crisly`
**Disciplina:** Projeto de Redes de Computadores — PPGCC/UFPI 2026-1
**Professor:** Rayner Gomes de Sousa

---

## Sumário

- [Objetivo](#objetivo)
- [Arquitetura](#arquitetura)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Requisitos](#requisitos)
- [Como executar](#como-executar)
- [Cenários de rede](#cenários-de-rede)
- [Testes TCP](#testes-tcp)
- [Testes R-UDP](#testes-r-udp)
- [Captura e análise dos resultados](#captura-e-análise-dos-resultados)
- [Protocolo R-UDP](#protocolo-r-udp)
- [Arquivos gerados](#arquivos-gerados)
- [Validação](#validação)
- [Resultados dos experimentos](#resultados-dos-experimentos)

---

## Objetivo

O projeto compara o comportamento de duas estratégias de transferência de arquivos em diferentes condições de rede:

1. **TCP:** transferência confiável usando o protocolo nativo da pilha TCP/IP.
2. **R-UDP:** transferência sobre UDP com mecanismos de confiabilidade implementados na aplicação (Go-Back-N).

Os experimentos medem tempo de transferência, vazão, retransmissões e eficiência em cenários com diferentes níveis de atraso e perda de pacotes.

---

## Arquitetura

O ambiente é composto por dois containers Docker conectados pela mesma rede bridge:

- **servidor_redes:** executa os servidores TCP e R-UDP, recebe o arquivo e salva logs.
- **cliente_redes:** executa os clientes TCP e R-UDP, envia `arquivo_teste.bin` e registra métricas.

Os cenários de rede são aplicados com `tc netem` na interface `eth0`. As capturas de tráfego são feitas com `tcpdump` e exportadas para CSV para análise.

---

## Estrutura do projeto

```text
redes_computadores/
├── Dockerfile                  # Imagem Ubuntu com Python, tc, tcpdump
├── docker-compose.yml          # Define os containers servidor e cliente
├── servidor_tcp.py             # Servidor TCP com registro de métricas
├── cliente_tcp.py              # Cliente TCP com argumento de cenário
├── servidor_rudp.py            # Servidor R-UDP com Go-Back-N
├── cliente_rudp.py             # Cliente R-UDP com Go-Back-N
├── setup_rede.sh               # Aplica cenários A/B/C com tc netem
├── captura.sh                  # Inicia tcpdump e exporta captura para CSV
├── exportar_pcaps.sh           # Exporta todos os PCAPs para CSV
├── analisar_resultados.py      # Gera estatísticas e validação cruzada
├── arquivo_teste.bin           # Arquivo de 1 MB usado nas transferências
└── dados/                      # Resultados dos experimentos
    ├── resultado_tcp.csv           # Resultados consolidados TCP (5 rodadas × 3 cenários)
    ├── resultado_rudp.csv          # Resultados consolidados R-UDP (5 rodadas × 3 cenários)
    ├── estatisticas_resumo.csv     # Média e desvio padrão por protocolo e cenário
    ├── validacao_cruzada.csv       # Comparação aplicação vs tcpdump
    ├── log_cliente_tcp.csv         # Log detalhado do cliente TCP
    ├── log_servidor_tcp.csv        # Log detalhado do servidor TCP
    ├── log_cliente_rudp.csv        # Log detalhado do cliente R-UDP
    ├── log_servidor_rudp.csv       # Log detalhado do servidor R-UDP
    ├── captura_*.pcap              # Capturas brutas do tcpdump
    └── captura_*.csv               # Capturas exportadas para CSV
```

---

## Requisitos

- Docker Desktop (Windows/Mac) ou Docker Engine (Linux)
- Docker Compose

Não é necessário instalar Python, `tcpdump` ou `tc` na máquina local — todas as dependências estão dentro da imagem Docker.

---

## Como executar

### 1. Subir os containers

```bash
cd redes_computadores
docker compose up -d --build
docker compose ps
```

### 2. Abrir dois terminais

**Terminal 1 — Servidor:**
```bash
docker exec -it servidor_redes bash
chmod +x *.sh
```

**Terminal 2 — Cliente:**
```bash
docker exec -it cliente_redes bash
```

---

## Cenários de rede

| Cenário | Perda | Delay | Comando |
|---------|------:|------:|---------|
| A | 0%  | 10 ms  | `./setup_rede.sh A` |
| B | 10% | 50 ms  | `./setup_rede.sh B` |
| C | 20% | 100 ms | `./setup_rede.sh C` |

Para remover as regras: `./setup_rede.sh limpar`

---

## Testes TCP

**Terminal 1 (servidor)** — roda uma vez, fica ouvindo:
```bash
./setup_rede.sh A
./captura.sh tcp A
python3 servidor_tcp.py
```

**Terminal 2 (cliente)** — roda 5 vezes consecutivas:
```bash
python3 cliente_tcp.py A
python3 cliente_tcp.py A
python3 cliente_tcp.py A
python3 cliente_tcp.py A
python3 cliente_tcp.py A
```

**Terminal 1** — encerra após as 5 rodadas:
```bash
kill $(cat captura.pid)
# Ctrl+C para parar o servidor
```

Repita para os cenários `B` e `C`.

---

## Testes R-UDP

**Terminal 1 (servidor):**
```bash
./setup_rede.sh A
./captura.sh rudp A
python3 servidor_rudp.py
```

**Terminal 2 (cliente)** — 5 vezes:
```bash
python3 cliente_rudp.py A
python3 cliente_rudp.py A
python3 cliente_rudp.py A
python3 cliente_rudp.py A
python3 cliente_rudp.py A
```

**Terminal 1:**
```bash
kill $(cat captura.pid)
# Ctrl+C para parar o servidor
```

Repita para os cenários `B` e `C`.

---

## Captura e análise dos resultados

Após os testes, dentro do container servidor:

```bash
# Exporta todos os PCAPs para CSV
./exportar_pcaps.sh

# Gera estatísticas e validação cruzada
python3 analisar_resultados.py

# Verifica integridade do arquivo transferido
md5sum arquivo_teste.bin recebido_tcp.bin recebido_rudp.bin
```

---

## Protocolo R-UDP

Implementação de confiabilidade sobre UDP usando Go-Back-N:

| Item | Valor |
|------|-------|
| Porta | UDP 6000 |
| Tamanho do chunk | 4096 bytes |
| Janela (N) | 8 pacotes |
| Timeout | 0,5 s |
| Checksum | MD5 por bloco |
| Sinal de FIM | pacote especial `b"-1\|FIM"` |
| Autenticação | `X-Custom-Auth: 20261005038 - Crisly` |

**Formato dos pacotes:**
```
<seq>|<md5hex>|<conteúdo>
```

**Fluxo:**
1. Cliente envia autenticação → aguarda `ACK_AUTH`
2. Arquivo dividido em chunks de 4096 bytes
3. Cliente envia até N=8 pacotes por janela
4. Servidor confirma com ACK cumulativo
5. Timeout → retransmite toda a janela (Go-Back-N)
6. Cliente envia `-1|FIM` → aguarda `ACK_FIM`

---

## Arquivos gerados

| Arquivo | Descrição |
|---------|-----------|
| `dados/resultado_tcp.csv` | Uma linha por execução TCP |
| `dados/resultado_rudp.csv` | Uma linha por execução R-UDP |
| `dados/estatisticas_resumo.csv` | Média e desvio padrão por protocolo/cenário |
| `dados/validacao_cruzada.csv` | Comparação aplicação vs tcpdump |
| `dados/log_cliente_tcp.csv` | Eventos de envio TCP |
| `dados/log_servidor_tcp.csv` | Eventos de recebimento TCP |
| `dados/log_cliente_rudp.csv` | Eventos de envio, ACKs e timeouts R-UDP |
| `dados/log_servidor_rudp.csv` | Eventos de recebimento, duplicatas e descartes |
| `dados/captura_*.pcap` | Capturas brutas do tcpdump |
| `dados/captura_*.csv` | Capturas exportadas para CSV |

---

## Validação

```bash
# Verifica integridade do arquivo transferido
md5sum arquivo_teste.bin recebido_tcp.bin recebido_rudp.bin

# Confirma X-Custom-Auth nas capturas TCP
tcpdump -A -r dados/captura_tcp_cenarioA_*.pcap 2>/dev/null | grep "X-Custom-Auth"

# Confirma X-Custom-Auth nas capturas R-UDP
tcpdump -A -r dados/captura_rudp_cenarioA_*.pcap 2>/dev/null | grep "X-Custom-Auth"
```

---

## Resultados dos experimentos

Resultados completos disponíveis na pasta `dados/`. Resumo das médias:

| Protocolo | Cenário | Vazão Média (Mbps) | Desvio Padrão |
|-----------|---------|-------------------:|---------------|
| TCP   | A (0%/10ms)   | 62,92 | 21,90 |
| TCP   | B (10%/50ms)  | 32,77 |  2,09 |
| TCP   | C (20%/100ms) | 15,76 |  0,40 |
| R-UDP | A (0%/10ms)   | 17,91 |  2,64 |
| R-UDP | B (10%/50ms)  |  3,88 |  1,77 |
| R-UDP | C (20%/100ms) |  2,28 |  0,16 |

Análise completa com gráficos disponível no Google Colab:
> 🔗 **[Link do Colab]** — substituir pelo link real após publicar

---

*Projeto de Redes de Computadores — PPGCC/UFPI 2026-1*