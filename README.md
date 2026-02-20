# 🚗 OBD2 Connector

Ferramenta completa para conectar ao seu veículo via **Bluetooth (ELM327)** ou **cabo USB/Serial OBD2**, permitindo **leitura e escrita** de dados e configurações do carro diretamente pelo notebook.

---

## ✅ Funcionalidades

- 🔵 Conexão via **Bluetooth** (ELM327)
- 🔌 Conexão via **USB / Serial** (cabo OBD2)
- 📊 Leitura de sensores em tempo real (RPM, velocidade, temperatura, etc.)
- ✏️ Envio de comandos AT e OBD2 personalizados
- 🔧 Leitura e limpeza de **DTCs** (códigos de falha)
- 💾 Exportação de dados para CSV
- 🖥️ Interface via terminal (CLI) interativa

---

## 📦 Requisitos

- Python 3.8+
- Adaptador ELM327 (Bluetooth ou USB)

## 🔧 Instalação

```bash
git clone https://github.com/mariobignami/obd2-connector.git
cd obd2-connector
pip install -r requirements.txt
```

---

## 🚀 Uso

### Conexão Bluetooth
```bash
python main.py --mode bluetooth --port /dev/rfcomm0
# Windows:
python main.py --mode bluetooth --port COM3
```

### Conexão USB/Serial
```bash
python main.py --mode serial --port /dev/ttyUSB0
# Windows:
python main.py --mode serial --port COM4
```

### Modo Interativo
```bash
python main.py --interactive
```

---

## 📡 Comandos disponíveis no modo interativo

| Comando       | Descrição                          |
|---------------|------------------------------------|
| `scan`        | Escaneia todos os sensores         |
| `dtc`         | Lê os códigos de falha (DTC)       |
| `clear_dtc`   | Limpa os códigos de falha          |
| `send <cmd>`  | Envia comando AT/OBD2 customizado  |
| `export`      | Exporta dados para CSV             |
| `help`        | Lista todos os comandos            |
| `exit`        | Encerra a conexão                  |

---

## 🗂️ Estrutura do Projeto

```
obd2-connector/
├── main.py               # Entry point
├── connector/
│   ├── __init__.py
│   ├── bluetooth.py      # Conexão Bluetooth
│   ├── serial_conn.py    # Conexão USB/Serial
│   └── base.py           # Classe base de conexão
├── obd/
│   ├── __init__.py
│   ├── commands.py       # Comandos OBD2 e AT
│   ├── reader.py         # Leitura de sensores
│   └── writer.py         # Escrita / envio de comandos
├── cli/
│   ├── __init__.py
│   └── interface.py      # Interface de terminal
├── utils/
│   ├── __init__.py
│   └── export.py         # Exportação CSV
├── requirements.txt
└── README.md
```

---

## ⚠️ Aviso

Use com responsabilidade. Comandos de escrita podem alterar configurações do veículo. O autor não se responsabiliza por danos causados pelo uso indevido.

---

## 📄 Licença

MIT License