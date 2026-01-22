# 👤 USER GUIDE - Como Usar o Sistema Usseewa

**Versão**: 1.0  
**Última Atualização**: 13/01/2026  
**Públicos**: Desenvolvedores, QA, Usuários Finais

---

## 📖 Índice

1. [Instalação e Setup](#-instalação-e-setup)
2. [Modos de Execução](#-modos-de-execução)
3. [Interface Desktop](#-interface-desktop)
4. [Interface Web](#-interface-web)
5. [Interface CLI](#-interface-cli)
6. [Configuração](#-configuração)
7. [Operações Comuns](#-operações-comuns)
8. [Troubleshooting](#-troubleshooting)

---

## 🚀 Instalação e Setup

### Pré-requisitos

- Python 3.9+ (recomendado 3.11)
- Git
- Câmera conectada (opcional - pode usar mock)
- ~2GB disco livre (para modelos)
- 4GB RAM mínimo

### Passo 1: Clonar Repositório

```bash
git clone <repo-url> Usseewa
cd Usseewa
```

### Passo 2: Criar Virtual Environment

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Passo 3: Instalar Dependências

```bash
pip install -r requirements.txt
```

### Passo 4: Baixar Modelos (Opcional)

```bash
# Modelos serão baixados automaticamente na primeira execução
# OU baixe manualmente em models/

cd models
# Seguir instruções em models/README.md
```

### Passo 5: Verificar Instalação

```bash
python launcher.py --mode cli --camera mock
# Deve capturar imagem de teste e exibir "✅ OK"
```

---

## ▶️ Modos de Execução

### Modo 1: Desktop (Recomendado)

**O quê**: Interface gráfica completa com abas  
**Por quê**: Mais intuitiva, todas as features visíveis  
**Quando**: Trabalho local, desenvolvimento, testes manuais

```bash
python launcher.py --mode desktop
# Ou simplesmente:
python launcher.py
```

**Recursos**:
- ✅ Captura de imagens
- ✅ Seleção de câmera
- ✅ Inspeção em tempo real (segmentação/classificação)
- ✅ Histórico de inspeções
- ✅ Configurações de câmera
- ✅ Perfis salvos
- ✅ Crop customizado
- ✅ Visualização de logs

**Abas Disponíveis**:
1. **Captura**: Capturar e exibir imagens
2. **Inspeção**: Executar modelos (segmentação/classificação)
3. **Histórico**: Visualizar inspeções anteriores
4. **Configurações**: Câmera, perfis, parâmetros
5. **Logs**: Mensagens do sistema

### Modo 2: Web API

**O quê**: Servidor REST + WebSocket  
**Por quê**: Integração remota, múltiplos clientes  
**Quando**: Deploy, integração com outros sistemas

```bash
python launcher.py --mode web
```

**Acesso**:
- API REST: http://localhost:8000
- Documentação: http://localhost:8000/docs
- UI Básica: http://localhost:8000/

**Endpoints Principais**:

```bash
# Captura
curl -X POST http://localhost:8000/api/capture
# Response: { "status": "ok", "image": "base64", ... }

# Segmentação
curl -X POST http://localhost:8000/api/segment \
  -H "Content-Type: application/json" \
  -d '{"model": "default"}'

# Classificação
curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"model": "default"}'

# Status
curl http://localhost:8000/api/status
```

**WebSocket**:
```javascript
// Cliente JavaScript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Evento:', data.type);  // 'capture_completed', 'inspection_completed', etc.
};
```

### Modo 3: CLI

**O quê**: Interface linha de comando  
**Por quê**: Automação, testes, scripts  
**Quando**: Batch processing, CI/CD, desenvolvimento sem UI

```bash
python launcher.py --mode cli
```

**Exemplo de Interação**:
```
$ python launcher.py --mode cli

===== USSEEWA CLI =====

Câmeras disponíveis:
  [1] Basler acA1300-50gc
  [2] Webcam
  [3] Mock Camera

Selecione câmera (1-3): 2

Comandos disponíveis:
  capture     - Captura imagem
  segment     - Segmentação
  classify    - Classificação
  history     - Ver histórico
  exit        - Sair

> capture
✅ Captura completa. Imagem salva em: data/results/20260113_143022/

> segment
✅ Segmentação completa. Classe: OK, Conf: 0.95

> exit
```

### Modo 4: Ambos (Desktop + Web)

```bash
python launcher.py --mode both
# Executa Desktop E Web API simultaneamente
```

---

## 🖥️ Interface Desktop

### Layout Principal

```
┌─ USSEEWA ──────────────────────────────────────────────────┐
│                                                             │
│  Câmera: [Basler ▼]  Status: 🟢 Pronto                    │
│  Log: [Botão]  Info: [Resolução: (1280, 960) ...]         │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ ┌─ Captura ─┬─ Inspeção ─┬─ Histórico ─┬─ Config ─┐   ││
│ │ │ [Imagem]  │            │             │          │   ││
│ │ │           │            │             │          │   ││
│ │ │ [Capturar]│ [Executar] │ [Histórico] │ [Perfil] │   ││
│ │ │ [Contínuo]│            │             │ [Câmera] │   ││
│ │ │           │            │             │          │   ││
│ └─ ┴─────────┴─ ┴────────┴─────────────┴─────────┴──┘   ││
│                                                             │
│  Log:                                                       │
│  ✅ Sistema iniciado                                        │
│  🎥 Câmera conectada                                        │
│  ✨ Pronto para capturar                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Aba: Captura

**Objetivo**: Capturar e visualizar imagens

**Operações**:

1. **Captura Única**
   - Clique em "📷 Capturar"
   - Imagem aparece na tela
   - Informações: resolução, câmera, timestamp

2. **Captura Contínua (Streaming)**
   - Clique em "🎥 Streaming"
   - Abre janela popup com stream contínuo
   - Pressione ESC ou feche para parar

3. **Crop Customizado**
   - Ative checkbox "✂️ Crop"
   - Clique em "🖼️ Editar Crop"
   - Arraste retângulo na imagem
   - Salve com Enter
   - Próximas capturas usarão crop automaticamente

4. **Resetar Crop**
   - Clique em "🔄 Resetar Crop"
   - Próximas capturas sem crop

**Dicas**:
- Use crop para focar em região específica
- Streaming consome mais CPU
- Imagens salvas em `data/results/`

### Aba: Inspeção

**Objetivo**: Executar modelos (segmentação/classificação)

**Operações**:

1. **Selecionar Tipo**
   - Dropdown "Tipo": Segmentação ou Classificação
   - Modelos disponíveis aparecem

2. **Executar Inspeção**
   - Clique "🚀 Executar Inspeção"
   - Sistema carrega modelo (primeira vez: ~10s)
   - Exibe resultados com confiança (%)

3. **Capturar + Inspecionar**
   - Ative "📸 Capturar e Inspecionar"
   - Próxima captura automaticamente inspecciona

4. **Auto-Salvar**
   - Ative "💾 Auto-salvar resultados"
   - Inspeções salvas automaticamente em `data/results/`

**Resultados**:

**Classificação**:
```
✅ FRUTA BOA
Classe: OK
Confiança: 95.2%
```

**Segmentação**:
```
❌ FRUTA RUIM
Classe: Podre
Confiança: 87.3%
Área segmentada: 1250px²
```

**Dicas**:
- Primeira inspeção demora (carregamento modelo)
- GPU acelera muito (CUDA recomendado)
- Resultado salvo com timestamp

### Aba: Histórico

**Objetivo**: Visualizar inspeções anteriores

**Operações**:

1. **Carregar Histórico**
   - Clique "📂 Carregar Histórico"
   - Lista todas as inspeções em `data/results/`

2. **Visualizar Item**
   - Selecione item da lista
   - Informações mostradas:
     - Data/hora
     - Tipo (segmentação/classificação)
     - Modelo usado
     - Resultados

3. **Exportar**
   - Clique "📊 Exportar CSV"
   - Todos os items exportados para arquivo Excel

4. **Limpar**
   - Clique "🗑️ Limpar Tudo"
   - Remove todo histórico

**Dicas**:
- Histórico é persistente (sobrevive reinicialização)
- Sempre faça backup de data/results/

### Aba: Configurações

**Objetivo**: Configurar câmera e perfis

**Secções**:

**1. Câmera Atual**
```
Câmera: Basler acA1300-50gc
Status: Conectada ✅
Resolução: 1280x960
FPS: 30
```

**2. Parâmetros de Câmera**
```
Ganho (Gain): [slider 0-100]
Exposição: [slider 0-10000µs]
Brightness: [slider 0-100]
```

**3. Perfis**
```
Perfis salvos:
  ┌─────────────────────┐
  │ Perfil 1: Basler    │  [Carregar] [Deletar]
  │ Perfil 2: Webcam    │  [Carregar] [Deletar]
  └─────────────────────┘

  [Novo Perfil...]
```

**4. Servidor Web**
```
Status Web API: Desativado [Ativar ▼]
Porta: 8000
WebSocket: ws://localhost:8000/ws
```

**Operações**:

1. **Ajustar Câmera**
   - Use sliders para ajustar exposição/ganho
   - Imagem atualiza em tempo real na aba Captura

2. **Salvar Perfil**
   - Configure câmera
   - Clique "💾 Novo Perfil"
   - Nome: "Condição de Luz Forte"
   - Próximas vezes, carregue o perfil

3. **Trocar de Câmera**
   - Dropdown "Câmera"
   - Sistema reconecta automaticamente
   - Parâmetros resetam

---

## 🌐 Interface Web

### Usando a API REST

**URL Base**: `http://localhost:8000`

**Headers Padrão**:
```
Content-Type: application/json
Accept: application/json
```

### Endpoints Principais

#### 1. Captura
```
POST /api/capture

Response:
{
  "status": "ok",
  "timestamp": "20260113_143022",
  "camera_type": "Basler",
  "image_base64": "iVBORw0KGgo...",
  "shape": [960, 1280, 3]
}
```

#### 2. Segmentação
```
POST /api/segment

Body:
{
  "model": "default",
  "confidence": 0.5,
  "image_base64": "iVBORw0KGgo..."  // Opcional (usa última captura)
}

Response:
{
  "status": "ok",
  "results": {
    "class": "OK",
    "confidence": 0.95,
    "area": 1250,
    "mask_base64": "iVBORw0KGgo..."
  }
}
```

#### 3. Classificação
```
POST /api/classify

Body:
{
  "model": "default",
  "image_base64": "iVBORw0KGgo..."
}

Response:
{
  "status": "ok",
  "results": {
    "predicted_class": "OK",
    "confidence": 0.92,
    "class_scores": {
      "OK": 0.92,
      "Defeito": 0.05,
      "Podre": 0.03
    }
  }
}
```

#### 4. Status
```
GET /api/status

Response:
{
  "status": "ok",
  "timestamp": "2026-01-13 14:30:22",
  "camera": "Basler acA1300-50gc",
  "models_loaded": ["segmentation_best.pt"],
  "memory_usage_mb": 1250,
  "uptime_seconds": 3600
}
```

### WebSocket

**Conexão**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('Conectado ao servidor');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  // Tipos de evento
  if (message.type === 'capture_completed') {
    console.log('Captura concluída:', message.data);
  } else if (message.type === 'segmentation_completed') {
    console.log('Segmentação concluída:', message.data);
  } else if (message.type === 'error') {
    console.error('Erro:', message.data);
  }
};

ws.onerror = (error) => {
  console.error('Erro WebSocket:', error);
};

ws.onclose = () => {
  console.log('Desconectado');
};
```

### Documentação Interativa

Acesse: http://localhost:8000/docs

(Interface Swagger - teste endpoints aqui!)

---

## 💻 Interface CLI

### Iniciar

```bash
python launcher.py --mode cli
```

### Comandos Disponíveis

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `capture` | Captura imagem | `> capture` |
| `segment` | Segmentação | `> segment` |
| `classify` | Classificação | `> classify` |
| `history` | Listar histórico | `> history` |
| `export` | Exportar CSV | `> export` |
| `config` | Ver configuração | `> config` |
| `help` | Ajuda | `> help` |
| `exit` | Sair | `> exit` |

### Exemplos de Uso

```bash
$ python launcher.py --mode cli

===== USSEEWA CLI =====
Câmera: Basler acA1300-50gc
Status: ✅ Pronto

> capture
✅ Imagem capturada
  Resolução: 1280x960
  Caminho: data/results/20260113_143022/image.png

> segment
✅ Segmentação completa
  Classe: OK
  Confiança: 95.2%
  Tempo: 0.45s

> classify
✅ Classificação completa
  Classe: OK
  Confiança: 92.1%
  Tempo: 0.32s

> history
Histórico (10 últimas):
  [1] 20260113_143022 - Segmentação - OK (0.95)
  [2] 20260113_142015 - Classificação - OK (0.92)
  [3] 20260113_141003 - Segmentação - Defeito (0.87)
  ...

> export
📊 Exportado para: history_20260113.csv

> exit
Até logo!
```

---

## ⚙️ Configuração

### Arquivo: config/settings.py

Edite este arquivo para customizar comportamento:

```python
# Câmera padrão
DEFAULT_CAMERA = "basler"  # ou "webcam", "mock"

# Modelos padrão
DEFAULT_SEGMENTATION_MODEL = "yolo11n-seg.pt"
DEFAULT_CLASSIFICATION_MODEL = "classification_best.pt"

# Servidor Web
WEB_PORT = 8000
WEB_HOST = "0.0.0.0"

# Desktop UI
DESKTOP_WINDOW_SIZE = (1280, 800)
DESKTOP_THEME = "dark"  # ou "light"
```

### Variáveis de Ambiente

```bash
# Desabilitar CUDA (usar CPU)
export CUDA_VISIBLE_DEVICES=-1

# Debug mode
export DEBUG=1

# Port customizado (Web)
export PORT=9000

# Executar
python launcher.py
```

---

## 📝 Operações Comuns

### Workflow Típico: Inspecionar Fruta

1. **Iniciar sistema**
   ```bash
   python launcher.py --mode desktop
   ```

2. **Posicionar fruta na câmera**
   - Aguarde até ver preview

3. **Capturar imagem**
   - Clique "📷 Capturar"
   - Visualize resultado

4. **Executar inspeção**
   - Aba "Inspeção"
   - Clique "🚀 Executar"
   - Aguarde resultado

5. **Interpretar resultado**
   ```
   ✅ OK (95%)        → Fruta boa, embarque
   ❌ Defeito (87%)   → Encaminhar reprocesso
   🔶 Indeterminado   → Revisão manual
   ```

6. **Próxima fruta**
   - Remova fruta anterior
   - Clique "📷 Capturar"
   - Repita

### Batch Processing (CLI)

```python
# script_batch.py
from core.system_core import SystemCore
from config import DESKTOP_CONFIG
import os

core = SystemCore(DESKTOP_CONFIG)

# Processar 100 imagens
for i, image_file in enumerate(os.listdir("./input_images")):
    image_path = f"./input_images/{image_file}"
    
    # Segmentação
    results = core.run_model(
        image_path, 
        model_name="yolo11n-seg.pt",
        inspection_type="segmentation"
    )
    
    # Salvar resultado
    core.save_inspection(image_path, results)
    print(f"[{i+1}/100] {image_file}: {results['class']}")
```

```bash
python script_batch.py
```

### Extrair Histórico em CSV

```bash
# Interface Desktop
# Aba "Histórico" → "📊 Exportar CSV"
# Abre em Excel/Sheets

# Ou via CLI
python launcher.py --mode cli
> export

# Abre: history_YYYYMMDD.csv
```

---

## 🆘 Troubleshooting

### Erro: "Camera not found"

```
❌ ERROR: Nenhuma câmera detectada
```

**Soluções**:
1. Verificar conexão USB (Basler) ou drivers (Webcam)
2. Usar mock para teste: `--camera mock`
3. Verificar permissões de acesso

```bash
# Testar com mock
python launcher.py --mode cli --camera mock
```

### Erro: "Model loading failed"

```
❌ ERROR: Falha ao carregar modelo
```

**Soluções**:
1. Verificar se arquivo .pt existe em `models/`
2. Verificar espaço em disco (~100MB)
3. Baixar modelo faltante

```bash
cd models
# Seguir instruções em README.md
```

### Erro: "UI freezes"

```
❌ Interface fica congelada
```

**Soluções**:
1. Usar CLI em vez de Desktop
2. Aumentar timeout em config
3. Verificar logs: Aba "Logs"

```bash
# Debug mode
export DEBUG=1
python launcher.py
```

### Erro: "Out of memory"

```
❌ ERROR: Out of memory (CUDA/CPU)
```

**Soluções**:
1. Usar CPU em vez de GPU:
   ```bash
   export CUDA_VISIBLE_DEVICES=-1
   ```
2. Unload modelos entre uso:
   ```python
   core.model_manager.unload_all()
   ```
3. Aumentar RAM disponível

### Imagem invertida/distorcida

```
❌ Imagem de cabeça para baixo
```

**Soluções**:
1. Verificar orientação da câmera (física)
2. Configurar rotação em `basler_camera.py`
3. Reportar issue

---

## 📚 Referências Rápidas

| Tarefa | Comando | Resultado |
|--------|---------|-----------|
| Iniciar Desktop | `python launcher.py` | Abre interface gráfica |
| Iniciar Web API | `python launcher.py --mode web` | Servidor em :8000 |
| Testar sistema | `python launcher.py --mode cli --camera mock` | CLI com câmera fake |
| Ver ajuda | `python launcher.py --help` | Lista argumentos |
| Verificar versão | `python launcher.py --version` | Exibe versão |

---

## 📞 Suporte

**Problema com documentação?**
→ Consulte [ENGINEERING.md](ENGINEERING.md)

**Problema técnico?**
→ Consulte [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)

**Quer entender código?**
→ Consulte [docs/code_overview.txt](docs/code_overview.txt)

---

**Versão**: 1.0  
**Última Atualização**: 13/01/2026  
**Mantido por**: Equipe Usseewa
