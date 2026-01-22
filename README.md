# 🔬 Usseewa - Sistema Híbrido de Visão Computacional e Inspeção

APP profissional de inspeção visual com suporte a múltiplas interfaces (Desktop PyQt5, Web API, CLI, Híbrido).

---

## 🚀 Quick Start

```bash
# 1. Clonar e preparar
git clone <repo>
cd Usseewa
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Executar
python launcher.py --mode desktop  # GUI
python launcher.py --mode web      # API + WebSocket
python launcher.py --mode cli      # Terminal
python launcher.py --mode both     # Desktop + API
```

---

### 1️⃣ Para **ENTENDER** o Sistema
👉 **[ENGINEERING.md](ENGINEERING.md)** - Arquitetura, componentes, padrões, design
- Visão geral da arquitetura
- 6 componentes principais
- 6 padrões de design utilizados
- Estrutura de diretórios
- Fluxos de dados
- Guia de extensão

### 2️⃣ Para **USAR** o Sistema
👉 **[USER_GUIDE.md](USER_GUIDE.md)** - Guias práticos passo-a-passo
- Instalação completa
- 4 modos de execução (Desktop, Web, CLI, Híbrido)
- Exemplos com screenshots (Desktop)
- Exemplos API REST com curl
- Exemplos WebSocket com Python
- Workflows típicos (inspeção de frutas)
- Troubleshooting

### 3️⃣ Para **VERIFICAR** o Sistema
👉 **[VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)** - Testes e validação completa
- Verificação de ambiente (Python, câmera, arquivos)
- Testes de sintaxe Python
- Testes de runtime (Mock, Desktop, Web)
- Verificação de features (captura, inspeção, salvamento)
- Testes de performance (tempo, memória)
- Checklist de deployment

---

## 🎯 Características

✅ **Múltiplas Interfaces**
- Desktop GUI com PyQt5 (completa com tabs)
- Web API com FastAPI + WebSocket (tempo real)
- CLI para scripts e automação
- Modo híbrido (Desktop + API simultânea)

✅ **Câmeras Suportadas**
- Basler (industrial, profissional)
- Webcam USB (padrão, fácil)
- Mock (sem hardware, para testes)
- Fallback automático entre câmeras

✅ **Modelos YOLO**
- Segmentação (yolo11n-seg.pt)
- Classificação (classification_best.pt)
- Detecção customizada (s_best.pt, c_best.pt)

✅ **Arquitetura Profissional**
- Padrões de design (Facade, Strategy, Singleton, Chain of Responsibility)
- Separação de responsabilidades (SRP)
- Logging estruturado e rotacionado
- Callbacks para eventos assíncronos
- Gerenciamento automático de recursos

---

## 📁 Estrutura de Diretórios

```
Usseewa/
├── launcher.py                      # 🎯 Ponto de entrada (use este!)
├── requirements.txt                 # Dependências
├── README.md                        # Bem-vindo (você está aqui)
│
├── 📖 DOCUMENTAÇÃO
├── ENGINEERING.md                   # Entender: Arquitetura e design
├── USER_GUIDE.md                    # Usar: Guias práticos
├── VERIFICATION_CHECKLIST.md        # Verificar: Testes
│
├── config/
│   ├── settings.py                  # ⚙️ Configurações principais
│   ├── __init__.py
│   └── __pycache__/
│
├── core/
│   ├── system_core.py               # 🎯 Facade (orquestra tudo)
│   ├── camera/                      # Câmeras
│   │   ├── icamera.py
│   │   ├── basler_camera.py
│   │   ├── webcam_camera.py
│   │   ├── mock_camera.py
│   │   ├── camera_manager.py
│   │   └── __pycache__/
│   ├── ml/                          # Modelos YOLO
│   │   ├── model_manager.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── image_processing/            # Processamento
│   │   ├── image_pipeline.py
│   │   └── __pycache__/
│   ├── services/                    # Serviços
│   │   ├── capture_scheduler.py
│   │   └── __pycache__/
│   ├── utils/                       # Helpers
│   │   ├── logger.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── __init__.py
│   └── __pycache__/
│
├── interfaces/
│   ├── desktop/                     # 🖥️ PyQt5 GUI
│   │   ├── app.py                   # MainWindow principal
│   │   ├── managers/                # Fase 1: Managers extraídos
│   │   │   ├── capture_manager.py
│   │   │   ├── inspection_manager.py
│   │   │   └── history_manager.py
│   │   ├── __pycache__/
│   │   └── ...
│   ├── web/                         # 🌐 FastAPI + WebSocket
│   │   ├── server.py
│   │   ├── static/
│   │   ├── templates/
│   │   │   └── index.html
│   │   ├── __pycache__/
│   │   └── ...
│
├── models/                          # 🤖 Modelos YOLO (download)
│   ├── yolo11n-seg.pt               # ~50MB
│   ├── classification_best.pt        # ~20MB
│   ├── s_best.pt
│   ├── c_best.pt
│   ├── README.md                    # Como baixar
│   └── ...
│
├── data/
│   ├── results/                     # 💾 Resultados de inspeções
│   │   ├── 20260113_093422/
│   │   │   └── inspection_data.json
│   │   └── 20260113_093531/
│   │       └── inspection_data.json
│   └── ...
│
├── logs/                            # 📋 Logs automáticos
│
└── tests/                           # 🧪 Testes (conforme necessário)
```

---

## ⚙️ Configuração Rápida

Editar [config/settings.py](config/settings.py):

```python
# Câmera padrão (qual usar?)
DEFAULT_CAMERA = 'mock'  # 'basler' | 'webcam' | 'mock'

# Modelos YOLO
DEFAULT_SEGMENTATION_MODEL = 'yolo11n-seg.pt'
DEFAULT_CLASSIFICATION_MODEL = 'classification_best.pt'

# Servidor Web
WEB_HOST = '0.0.0.0'
WEB_PORT = 8000

# Saída de resultados
DATA_OUTPUT_DIR = './data/results'
```

---

## 🏗️ Arquitetura (Visão Geral)

```
┌─────────────────────────────────────────────┐
│ Interfaces de Usuário                       │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│ │ Desktop  │  │   Web    │  │   CLI    │   │
│ │  (PyQt5) │  │ (FastAPI)│  │(terminal)│   │
│ └─────┬────┘  └────┬─────┘  └────┬─────┘   │
└───────┼────────────┼─────────────┼─────────┘
        │            │             │
        └────────────┼─────────────┘
                     │
            ┌────────▼────────┐
            │  SystemCore     │ (Facade)
            │ (orquestra tudo)│
            └────────┬────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
    ┌───▼───┐    ┌───▼────┐  ┌───▼────┐
    │Camera │    │ Models │  │ Storage│
    │Manager│    │Manager │  │ & Logs │
    └───────┘    └────────┘  └────────┘
```

**Padrões de Design**:
- **Facade**: SystemCore orquestra câmeras, modelos, storage
- **Strategy**: ICamera com Basler/Webcam/Mock
- **Singleton**: ModelManager carregado uma vez em memória
- **Chain of Responsibility**: Fallback automático entre câmeras
- **Observer**: Callbacks para eventos
- **Manager Pattern**: CaptureManager, InspectionManager, HistoryManager (Fase 1)

---

## 🚀 Como Executar

### Desktop GUI (Recomendado para Iniciantes)
```bash
python launcher.py --mode desktop
# Abre janela gráfica com tabs
# Clique em "Capture", veja resultado, clique em "Inspect"
```

### Web API + Interface Web
```bash
python launcher.py --mode web
# Abra navegador em http://localhost:8000
# Ou use curl:
curl -X POST http://localhost:8000/api/capture
```

### CLI (Scripts e Automação)
```bash
python launcher.py --mode cli
# Digite comandos: capture, inspect, list, exit
```

### Híbrido (Desktop + API Simultânea)
```bash
python launcher.py --mode both
# Desktop aberto, API rodando em background
```

---

## ✅ Verificação Rápida

```bash
# 1. Sintaxe OK?
python -m py_compile launcher.py core/system_core.py

# 2. Imports funcionam?
python -c "from core.system_core import SystemCore; print('✅')"

# 3. Mock camera funciona?
python launcher.py --mode cli --camera mock <<< "capture
exit"

# 4. Web API funciona?
python launcher.py --mode web &
sleep 2
curl http://localhost:8000/api/status
pkill -f launcher
```

---

## 📋 Versões Mínimas

| Pacote | Versão | Nota |
|--------|--------|------|
| Python | 3.9+ | Ideal 3.11+ |
| PyQt5 | 5.15+ | Interface Desktop |
| FastAPI | 0.95+ | API Web |
| OpenCV | 4.8+ | Processamento de imagem |
| PyTorch | 2.0+ | YOLO |
| CUDA | 12.0+ | Opcional (GPU) |

---

## 📖 Documentação Completa

| Documento | Para Quem | Conteúdo |
|-----------|----------|---------|
| [ENGINEERING.md](ENGINEERING.md) | Devs, Arquitetos | Arquitetura, padrões, extensão |
| [USER_GUIDE.md](USER_GUIDE.md) | Usuários, QA | Como usar, exemplos, workflows |
| [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) | QA, DevOps, Ops | Testes, validação, deployment |

---

## 🔧 Troubleshooting

**"ModuleNotFoundError: No module named 'core'"**
```bash
# Certifique-se que está na pasta Usseewa:
ls launcher.py config/ core/ interfaces/
# Deve listar todos esses
```

**"Câmera não encontrada"**
```bash
# Use mock para testar:
python launcher.py --mode cli --camera mock
```

**"Modelo não carregado"**
```bash
# Verifique arquivo existe:
ls -la models/*.pt
# Se vazio, baixe conforme models/README.md
```

**"Porta 8000 em uso"**
```bash
# Mude em config/settings.py:
WEB_PORT = 9000
# Ou na linha de comando (se suportado)
```

Veja [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) para troubleshooting completo.

---

## 📝 Git - O Que Versionar

**NÃO versione** (adicionar a `.gitignore`):
```
venv/                  # Ambiente virtual (local)
__pycache__/          # Cache Python
*.pyc                 # Bytecode compilado
models/*.pt            # Modelos muito grandes (100MB+)
data/                  # Dados de produção
logs/                  # Logs gerados
.env                   # Credenciais sensíveis
.vscode/              # Configurações locais
.DS_Store             # macOS
```

**Versione** (commit e push):
```
launcher.py            # Código principal
core/                  # Lógica do sistema
interfaces/            # UIs (desktop, web, cli)
config/settings.py     # Config padrão
requirements.txt       # Dependências (com versões!)
README.md              # Documentação
*.md                   # Todos os .md
tests/                 # Testes
models/README.md       # Como baixar modelos
```

---

## 🚢 Deploy para Produção

Veja [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) → Seção "Checklist de Deployment"

```bash
# 1. Criar novo venv
python -m venv venv_prod

# 2. Ativar
source venv_prod/bin/activate  # Linux/Mac
# ou
venv_prod\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Iniciar
python launcher.py --mode both

# 5. Verificar saúde
curl http://localhost:8000/api/status
```

---

## 📞 Próximas Ações

1. **Quer aprender?** → Leia [ENGINEERING.md](ENGINEERING.md)
2. **Quer usar?** → Leia [USER_GUIDE.md](USER_GUIDE.md)
3. **Quer verificar?** → Use [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)
4. **Quer contribuir?** → Veja [ENGINEERING.md](ENGINEERING.md) seção "Extension Guide"

---

## 📊 Status do Projeto

✅ **Arquitetura**: Completa (Facade, Strategy, Singleton, Chain of Responsibility)  
✅ **Implementação Fase 1**: Managers extraídos (CaptureManager, InspectionManager, HistoryManager)  
✅ **Documentação**: Consolidada (ENGINEERING, USER_GUIDE, VERIFICATION)  
✅ **Testes**: Checklist pronto  
✅ **Production-Ready**: Sim  

---

**Versão**: 2.0  
**Status**: ✅ Production-Ready  
**Última Atualização**: 13 de Janeiro de 2026  

---

### 🎯 Comece Aqui

```bash
# 1. Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Teste rápido
python launcher.py --mode cli --camera mock

# 3. Use normalmente
python launcher.py --mode desktop

# 4. Leia docs se tiver dúvidas
# → ENGINEERING.md (o que é)
# → USER_GUIDE.md (como usar)
# → VERIFICATION_CHECKLIST.md (como testar)
```
