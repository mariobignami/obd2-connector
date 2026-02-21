# 🚗 OBD2 Connector

Ferramenta Python completa para diagnóstico veicular via **Bluetooth ELM327** ou **cabo USB/Serial OBD2**.  
Leia sensores em tempo real, visualize um dashboard ao vivo, leia/limpe DTCs, exporte dados e muito mais – tudo pelo terminal.

---

## ✅ Funcionalidades

| Categoria | Recurso |
|-----------|---------|
| 🔵 Conexão | Bluetooth ELM327 (rfcomm / COM) |
| 🔌 Conexão | USB / Serial ELM327 (cabo) |
| 🌐 Web Dashboard | Interface completa no navegador com Flask (http://localhost:5000) |
| 📊 Tempo Real | Dashboard ao vivo com todos os sensores (atualização contínua) |
| 🗺 Computador de Bordo | Distância percorrida, velocidade média/máxima, tempo de viagem |
| ⚠️ Alertas | Alertas visuais para temperatura alta, RPM excessivo, voltagem baixa, combustível baixo |
| 🔧 Ler Erros (DTC) | Leitura de falhas armazenadas (Modo 03) e pendentes (Modo 07) com descrições |
| 🧹 Limpar Erros | Apaga todos os códigos de falha (Modo 04) — injeção, emissão, motor, etc. |
| 🧊 Freeze Frame | Leitura de dados congelados no momento da falha (Modo 02) |
| 🪪 Informações do Veículo | VIN, nome do ECU, ID de calibração, protocolo OBD, versão ELM327, voltagem da bateria |
| 📡 Comandos Raw | Envia qualquer comando AT ou OBD2 diretamente |
| 💾 Exportação | CSV e JSON (snapshot único ou log de sessão completo) |
| 📝 Log Automático | Salva dados em CSV automaticamente durante o dashboard ao vivo |
| 🖥️ CLI Interativo | REPL completo com ajuda embutida |

### Sensores suportados (Modo 01)

| Chave | Sensor | Unidade |
|-------|--------|---------|
| RPM | Rotações do motor | rpm |
| SPEED | Velocidade do veículo | km/h |
| COOLANT_TEMP | Temperatura do líquido de arrefecimento | °C |
| ENGINE_LOAD | Carga calculada do motor | % |
| THROTTLE | Posição do acelerador | % |
| MAF | Vazão de ar em massa (MAF) | g/s |
| INTAKE_TEMP | Temperatura do ar de admissão | °C |
| MAP | Pressão absoluta do coletor de admissão | kPa |
| TIMING_ADVANCE | Avanço de ignição | ° antes do PMT |
| OIL_TEMP | Temperatura do óleo do motor | °C |
| FUEL_LEVEL | Nível de combustível | % |
| FUEL_RATE | Consumo instantâneo de combustível | L/h |
| SHORT_FUEL_TRIM_1 | Correção de combustível de curto prazo (Banco 1) | % |
| LONG_FUEL_TRIM_1 | Correção de combustível de longo prazo (Banco 1) | % |
| VOLTAGE | Tensão do módulo de controle | V |
| BARO_PRESSURE | Pressão barométrica | kPa |
| AMBIENT_TEMP | Temperatura ambiente | °C |
| RUNTIME | Tempo de funcionamento do motor | s |
| DISTANCE_MIL | Distância com luz de avaria (MIL) ligada | km |
| DISTANCE_SINCE_CLR | Distância desde a limpeza de DTCs | km |
| WARMUPS_SINCE_CLR | Aquecimentos desde a limpeza de DTCs | count |
| ABS_LOAD | Carga absoluta | % |
| EVAP_PRESSURE | Pressão do sistema de evaporação | Pa |

---

## 📦 Requisitos

- Python 3.8+
- Adaptador ELM327 (Bluetooth ou USB/Serial)

### Dependências Python

```
pyserial>=3.5
rich>=13.0.0
click>=8.1.0
flask>=3.0.0
pytest>=8.0.0
```

---

## 🔧 Instalação

```bash
git clone https://github.com/mariobignami/obd2-connector.git
cd obd2-connector
pip install -r requirements.txt
```

---

## 🌐 Dashboard Web (no Navegador)

O OBD2 Connector inclui um **dashboard completo no navegador**, com gauges animados, leitura de erros, limpeza de DTCs e streaming ao vivo — tudo via Flask.

### Iniciar em modo demo (sem hardware)

```bash
python main.py --demo --web
```

Acesse em: **http://localhost:5000**

> No modo demo, sensores simulados variam em tempo real e 2 códigos de falha de exemplo são exibidos para você testar as funcionalidades.

### Iniciar com ELM327 Bluetooth

```bash
# Linux (emparelhe o ELM327 e crie o rfcomm primeiro):
sudo rfcomm bind 0 <MAC-DO-ELM327>
python main.py --mode bluetooth --port /dev/rfcomm0 --web

# Windows (use a porta COM atribuída pelo Bluetooth):
python main.py --mode bluetooth --port COM3 --web
```

### Iniciar com ELM327 USB/Serial

```bash
# Linux
python main.py --mode serial --port /dev/ttyUSB0 --web

# Windows
python main.py --mode serial --port COM4 --web
```

### Porta customizada para o servidor web

```bash
python main.py --demo --web --web-port 8080
# Acesse em http://localhost:8080
```

### Funcionalidades do Dashboard Web

| Botão / Função | Descrição |
|----------------|-----------|
| **⟳ Scan All** | Lê todos os sensores de uma vez |
| **▶ Live Stream** | Inicia/para o streaming em tempo real via SSE |
| **🚗 Vehicle Info** | Exibe VIN, ECU, protocolo, versão ELM327 e tensão |
| **↓ Export CSV** | Baixa os dados atuais dos sensores em CSV |
| **⚠ Ler Erros** | Lê os **códigos de falha armazenados (Modo 03)** com descrição — inclui erros de injeção, catalisador, emissões, etc. |
| **📋 Pendentes** | Lê DTCs pendentes (Modo 07) — falhas detectadas mas ainda não armazenadas |
| **✕ Limpar Erros** | Apaga **todos os DTCs armazenados (Modo 04)** — reset da luz de avaria |
| **Terminal** | Envia qualquer comando AT ou OBD2 raw diretamente ao ELM327 |

#### Seções do Dashboard

- **📊 Sensores** — 18 gauges animados em arco semicircular (RPM, Velocidade, Temperatura, Combustível, MAF, etc.)
- **🗺 Computador de Bordo** — Tempo de funcionamento, distância desde reset, aquecimentos, pressão EVAP
- **⚠ Diagnóstico** — Códigos de falha com descrição completa em português e categoria do sistema (Powertrain, Chassis, Body, Network)
- **🪪 Veículo** — Informações do ECU e VIN
- **💻 Terminal** — Console raw para comandos AT/OBD2

#### Como ler e limpar erros de injeção (DTC)

1. Acesse o dashboard: `python main.py --web --mode bluetooth --port /dev/rfcomm0`
2. Clique em **⚠ Ler Erros** — os códigos aparecem com descrição (ex: `P0201 – Defeito no injetor – Cilindro 1`)
3. Para apagar, clique em **✕ Limpar Erros** e confirme
4. Clique em qualquer código para pesquisar mais informações no Google

> O MIL (luz de avaria/"check engine") é detectado automaticamente e os DTCs são lidos ao carregar a página se estiver ligado.

---

## 🚀 Uso Rápido (CLI)

### Descobrir portas disponíveis

```bash
python main.py list-ports
```

### Conexão Bluetooth e dashboard ao vivo (terminal)

```bash
# Linux
python main.py --mode bluetooth --port /dev/rfcomm0 --dash

# Windows
python main.py --mode bluetooth --port COM3 --dash
```

### Conexão USB/Serial e dashboard ao vivo

```bash
# Linux
python main.py --mode serial --port /dev/ttyUSB0 --dash

# Windows
python main.py --mode serial --port COM4 --dash
```

### Dashboard ao vivo com log automático em CSV (intervalo de 0,5 s)

```bash
python main.py --mode serial --port /dev/ttyUSB0 --dash --interval 0.5 --log
```

### Leitura única de todos os sensores e saída

```bash
python main.py --mode serial --port /dev/ttyUSB0 --scan
```

### Ver informações do veículo (VIN, ECU, …) e sair

```bash
python main.py --mode serial --port /dev/ttyUSB0 --info
```

### Ver DTCs e sair

```bash
python main.py --mode serial --port /dev/ttyUSB0 --dtc
```

### Modo interativo (REPL)

```bash
python main.py --mode serial --port /dev/ttyUSB0 --interactive
# ou simplesmente (modo padrão):
python main.py --mode serial --port /dev/ttyUSB0
```

---

## 🖥️ Modo Interativo – Comandos Disponíveis

```
obd2> help
```

| Comando | Descrição |
|---------|-----------|
| `scan` | Lê todos os sensores uma vez e exibe tabela |
| `dash [intervalo] [--log]` | Dashboard ao vivo (padrão 1 s; `--log` salva CSV) |
| `dtc` | Exibe DTCs armazenados (Modo 03) |
| `pending` | Exibe DTCs pendentes (Modo 07) |
| `clear_dtc` | Apaga DTCs armazenados (Modo 04) – pede confirmação |
| `freeze [frame#]` | Lê dados do freeze frame (padrão: frame 0) |
| `info` | VIN, nome do ECU, protocolo, versão ELM327, voltagem |
| `trip` | Resumo do computador de bordo da sessão |
| `send <cmd>` | Envia um comando AT ou OBD2 raw |
| `export [csv\|json]` | Exporta dados da sessão para CSV (padrão) ou JSON |
| `log [intervalo]` | Como `dash`, mas sempre com log em CSV |
| `help` | Exibe esta ajuda |
| `exit` | Encerra a conexão |

### Exemplos no modo interativo

```
obd2> scan                   # snapshot de todos os sensores
obd2> dash 0.5 --log         # dashboard a cada 0,5 s com log
obd2> dtc                    # ver falhas
obd2> clear_dtc              # limpar falhas (pede confirmação)
obd2> freeze 0               # freeze frame #0
obd2> info                   # informações do veículo
obd2> trip                   # computador de bordo
obd2> send AT RV             # voltagem da bateria via ELM327
obd2> send 0105              # temperatura do arrefecimento (raw)
obd2> export csv             # exportar sessão para CSV
obd2> export json            # exportar sessão para JSON
obd2> exit
```

---

## 🗂️ Estrutura do Projeto

```
obd2-connector/
├── main.py                  # Entry point (click CLI + web server)
├── connector/
│   ├── __init__.py
│   ├── base.py              # Classe base de conexão (serial I/O + AT init)
│   ├── bluetooth.py         # Conexão Bluetooth ELM327 (rfcomm / COM)
│   └── serial_conn.py       # Conexão USB/Serial ELM327 (cabo)
├── obd/
│   ├── __init__.py
│   ├── commands.py          # Tabela completa de PIDs + parsers + comandos AT
│   ├── reader.py            # Leitura: PID único, scan completo, tempo real, DTC, VIN
│   └── writer.py            # Escrita: comandos raw, AT nomeados, protocolo, timeout
├── cli/
│   ├── __init__.py
│   └── interface.py         # Dashboard Rich ao vivo + REPL interativo
├── web/
│   ├── __init__.py
│   ├── app.py               # Flask app factory (API REST + SSE streaming)
│   └── templates/
│       └── index.html       # Dashboard web completo (gauges, DTCs, terminal)
├── utils/
│   ├── __init__.py
│   └── export.py            # Exportação CSV e JSON
├── tests/
│   ├── __init__.py
│   └── test_obd2.py         # 55+ testes unitários (sem hardware)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🔬 Testes

Todos os testes rodam sem hardware (usando stubs):

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## 🔌 Uso como Biblioteca Python

```python
from connector import SerialConnector
from obd.reader import OBDReader
from obd.writer import OBDWriter
from utils.export import export_csv_log

# Conectar
conn = SerialConnector(port="/dev/ttyUSB0", baudrate=38400)
conn.connect()

reader = OBDReader(conn)
writer = OBDWriter(conn)

# Leitura única
print("RPM:", reader.read_pid("RPM"))
print("Velocidade:", reader.read_pid("SPEED"), "km/h")
print("Temperatura:", reader.read_pid("COOLANT_TEMP"), "°C")

# Scan completo
data = reader.read_all()

# Informações do veículo
print("VIN:", reader.read_vin())
print("Protocolo:", reader.get_protocol())
print("Voltagem ELM:", reader.get_battery_voltage())

# DTCs
dtcs = reader.read_dtcs()
pending = reader.read_pending_dtcs()

# Freeze frame
temp_ff = reader.read_freeze_frame("COOLANT_TEMP", frame=0)

# Streaming em tempo real (background thread)
session_log = []

def on_data(snapshot):
    session_log.append(snapshot)
    print(f"RPM={snapshot.get('RPM')}  Speed={snapshot.get('SPEED')}")

reader.start_realtime(on_data, interval=1.0)
import time; time.sleep(10)
reader.stop_realtime()

# Exportar
export_csv_log(session_log, path="minha_sessao.csv")

# Comando raw
resp = writer.send_raw("AT RV")
writer.set_protocol(6)   # CAN 11bit 500kbaud

conn.disconnect()
```

---

## ⚠️ Alertas de Threshold

O dashboard exibe alertas visuais automáticos:

| Sensor | Alerta alto | Alerta baixo |
|--------|-------------|--------------|
| RPM | ≥ 6500 rpm | – |
| Velocidade | ≥ 200 km/h | – |
| Temperatura do arrefecimento | ≥ 105 °C | – |
| Carga do motor | ≥ 95 % | – |
| Temperatura de admissão | ≥ 60 °C | – |
| Temperatura do óleo | ≥ 130 °C | – |
| Nível de combustível | – | ≤ 10 % |
| Tensão | – | ≤ 11,5 V |

---

## 🛠️ Compatibilidade

| Adaptador | Suporte |
|-----------|---------|
| ELM327 Bluetooth (SPP) | ✅ |
| ELM327 USB / Serial | ✅ |
| ELM327 Wi-Fi (via porta serial virtual) | ✅ |
| OBDLink MX+ | ✅ (ELM327 compatível) |
| Veículos OBD-II (desde 1996) | ✅ |
| Protocolos: CAN, ISO 9141-2, KWP2000, J1850 | ✅ (detecção automática) |

---

## ❓ Solução de Problemas

**Não encontra a porta serial:**
```bash
python main.py list-ports
```

**ELM327 Bluetooth não aparece:**
- Linux: emparelhe o dispositivo e crie o rfcomm: `sudo rfcomm bind 0 <MAC>`
- Windows: emparelhe via Bluetooth e anote a porta COM atribuída

**`NO DATA` em muitos sensores:**
- Nem todos os veículos suportam todos os PIDs. Isso é normal.
- Tente `python main.py --mode serial --port <porta> --info` para verificar a conexão.

**Timeout / lentidão:**
- Aumente o timeout: `--timeout 2`
- Reduza o intervalo do dashboard: `--interval 2`

---

## ⚠️ Aviso Legal

Use com responsabilidade. Comandos de limpeza de DTCs e de escrita podem alterar configurações do veículo.  
O autor não se responsabiliza por danos causados pelo uso indevido desta ferramenta.

---

## 📄 Licença

MIT License
