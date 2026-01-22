# 📐 Refatoração Fase 2 - Reorganização de Managers

**Data**: 22/01/2026  
**Status**: 🔵 Planejamento  
**Prioridade**: P1 - Alto Impacto  
**Estimativa**: 20-30 horas  
**Impacto SOLID**: +20% (SRP + DI)  
**Impacto Reusabilidade**: +40%  
**Impacto Testabilidade**: +60%  

---

## 📖 Índice

1. [Visão Geral](#visão-geral)
2. [Problema Atual](#problema-atual)
3. [Solução Proposta](#solução-proposta)
4. [Estrutura Final](#estrutura-final)
5. [Plano de Implementação](#plano-de-implementação)
6. [Detalhamento de Tarefas](#detalhamento-de-tarefas)
7. [Testes de Verificação](#testes-de-verificação)
8. [Rollback](#rollback)

---

## 🎯 Visão Geral

### Objetivo

Reorganizar os **managers** para seguir **SOLID** corretamente, separando:

- **Lógica pura** (agnóstica) em `core/managers/`
- **Integração UI** (PyQt5) em `interfaces/desktop/managers/`
- **Integração web** (FastAPI) em `interfaces/web/managers/`

### Benefícios

| Aspecto | Antes | Depois | Ganho |
|---------|-------|--------|-------|
| **SOLID Compliance** | 8.5/10 | 9.5/10 | +11% |
| **Testabilidade** | 7.5/10 | 9.2/10 | +23% |
| **Reusabilidade** | 50% | 90% | +40% |
| **Manutenibilidade** | 8.7/10 | 9.3/10 | +7% |

---

## ❌ Problema Atual

### Estrutura Problemática

```
interfaces/desktop/managers/
├── capture_manager.py         ← Mistura:
│   ├── Threading (CaptureThread)
│   ├── PyQt5 (QThread, signals)
│   └── Lógica de captura
│
├── inspection_manager.py      ← Mistura:
│   ├── Threading
│   ├── PyQt5
│   └── Lógica de inspeção
│
└── history_manager.py         ← OK (agnóstico)
```

### Violações SOLID

1. **Single Responsibility** ❌
   - Cada manager tem 3 responsabilidades (threading + UI + lógica)

2. **Dependency Inversion** ❌
   - Core depende de PyQt5 indiretamente
   - Web não pode reutilizar sem PyQt5

3. **Interface Segregation** ❌
   - Não há interface clara entre lógica e UI

4. **Open/Closed** ❌
   - Adicionar novo interface (CLI, mobile) requer duplicação de código

### Código Problemático (Exemplo)

```python
# ❌ PROBLEMA: capture_manager.py (interfaces/desktop/managers/)
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot

class CaptureManager(QObject):  # ← Acoplado a PyQt5
    capture_completed = pyqtSignal(dict)  # ← PyQt5 específico
    error_occurred = pyqtSignal(str)
    
    def __init__(self, core, camera_profiles):
        super().__init__()
        self.core = core
        self.camera_profiles = camera_profiles
        self.capture_thread = None
        self.current_profile = None
    
    def start_capture(self):
        self.capture_thread = CaptureThread(self.core)  # ← Threading
        self.capture_thread.image_captured.connect(self._on_capture_complete)
        self.capture_thread.error_occurred.connect(self._on_capture_error)
        self.capture_thread.start()
    
    @pyqtSlot(dict)
    def _on_capture_complete(self, result):
        self.capture_completed.emit(result)  # ← Signal PyQt5

# ❌ PROBLEMA: Não pode usar em Web!
# FastAPI não sabe lidar com QThread, pyqtSignal, etc.
```

---

## ✅ Solução Proposta

### Arquitetura Corrigida: Separação em 3 Camadas

```
┌──────────────────────────────────────────────────┐
│           CAMADA 1: LÓGICA PURA                  │
│              core/managers/                      │
│  (agnóstica, testável, reutilizável)            │
├──────────────────────────────────────────────────┤
│         ↓         ↓         ↓                    │
├──────┬──────────┬──────┬────────┬──────┐        │
│      │          │      │        │      │        │
▼      ▼          ▼      ▼        ▼      ▼        │
┌──────────────┬────────────────┬──────────────┐  │
│   CAMADA 2   │   CAMADA 2     │  CAMADA 2    │  │
│ Desktop(Qt)  │   Web(FastAPI) │   CLI(CLI)   │  │
└──────────────┴────────────────┴──────────────┘  │
```

### Princípios

✅ **core/managers/** = Lógica pura (sem UI)  
✅ **interfaces/*/managers/** = Wrappers específicos  
✅ **Unidirecional**: Core → Interfaces (nunca reverso)  
✅ **Testável**: Testa core/ sem PyQt5  
✅ **Reutilizável**: Mesma lógica em desktop/web/CLI  

---

## 🏗️ Estrutura Final

### Estrutura Pós-Refatoração

```
Usseewa/
│
├── core/
│   ├── system_core.py
│   ├── managers/                    ← NOVO
│   │   ├── __init__.py
│   │   ├── capture_manager.py       (140 linhas)
│   │   ├── inspection_manager.py    (150 linhas)
│   │   ├── history_manager.py       (200 linhas)
│   │   └── base_manager.py          (50 linhas) - Classe abstrata
│   ├── camera/
│   ├── ml/
│   ├── image_processing/
│   ├── services/
│   └── utils/
│
├── interfaces/
│   ├── desktop/
│   │   ├── app.py
│   │   └── managers/                ← ADAPTADO
│   │       ├── __init__.py
│   │       ├── capture_manager_qt.py    (80 linhas)
│   │       ├── inspection_manager_qt.py (80 linhas)
│   │       └── history_manager_qt.py    (40 linhas)
│   │
│   └── web/
│       ├── server.py
│       └── managers/                ← NOVO
│           ├── __init__.py
│           ├── capture_manager_api.py    (60 linhas)
│           ├── inspection_manager_api.py (60 linhas)
│           └── history_manager_api.py    (50 linhas)
│
└── [resto da estrutura...]
```

### Comparação Linha por Linha

| Arquivo | Antes | Depois | Mudança |
|---------|-------|--------|---------|
| `core/managers/capture_manager.py` | ❌ N/A | ✅ 140 | +140 (novo) |
| `core/managers/inspection_manager.py` | ❌ N/A | ✅ 150 | +150 (novo) |
| `core/managers/history_manager.py` | ❌ N/A | ✅ 200 | +200 (novo) |
| `interfaces/desktop/managers/capture_manager.py` | ⚠️ 200 | ✅ 80 | -120 (-60%) |
| `interfaces/desktop/managers/inspection_manager.py` | ⚠️ 210 | ✅ 80 | -130 (-62%) |
| `interfaces/desktop/managers/history_manager.py` | ✅ 180 | ✅ 40 | -140 (-78%) |
| `interfaces/web/managers/capture_manager_api.py` | ❌ N/A | ✅ 60 | +60 (novo) |
| `interfaces/web/managers/inspection_manager_api.py` | ❌ N/A | ✅ 60 | +60 (novo) |
| `interfaces/web/managers/history_manager_api.py` | ❌ N/A | ✅ 50 | +50 (novo) |
| **TOTAL** | **590** | **920** | +330 (melhor organizado) |

---

## 🚀 Plano de Implementação

### Fases

```
FASE 1: Preparação (2 horas)
  └─→ Criar estrutura core/managers/
  └─→ Criar base_manager.py

FASE 2: Migração history_manager (2 horas)
  └─→ Mover para core/ (já é agnóstico)
  └─→ Criar wrapper em desktop/managers/
  └─→ Criar wrapper em web/managers/

FASE 3: Migração capture_manager (6 horas)
  └─→ Extrair lógica pura → core/
  └─→ Manter threading em desktop/managers/
  └─→ Criar REST wrapper em web/managers/
  └─→ Testes de integração

FASE 4: Migração inspection_manager (6 horas)
  └─→ Extrair lógica pura → core/
  └─→ Manter threading em desktop/managers/
  └─→ Criar REST wrapper em web/managers/
  └─→ Testes de integração

FASE 5: Atualizar MainWindow (3 horas)
  └─→ Usar novos managers em desktop/managers/
  └─→ Testar funcionamento

FASE 6: Atualizar WebServer (2 horas)
  └─→ Usar novos managers em web/managers/
  └─→ Testar endpoints

FASE 7: Testes Finais (3 horas)
  └─→ Testes unitários
  └─→ Testes de integração
  └─→ Regressão visual

TOTAL: 24 horas (+ 2-4 horas buffer = 26-28 horas)
```

---

## 🔧 Detalhamento de Tarefas

### FASE 1: Preparação (2 horas)

#### Tarefa 1.1: Criar estrutura base_manager.py

```python
# core/managers/base_manager.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseManager(ABC):
    """
    Classe abstrata base para todos os managers.
    Define interface comum.
    """
    
    def __init__(self, core):
        """
        Args:
            core: Instância do SystemCore
        """
        self.core = core
    
    @abstractmethod
    def initialize(self) -> bool:
        """Inicializa o manager"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Limpa recursos"""
        pass
    
    def _notify(self, event: str, data: Optional[Dict] = None) -> None:
        """Notifica via callbacks do core"""
        if hasattr(self.core, '_notify'):
            self.core._notify(event, data or {})
```

#### Tarefa 1.2: Criar `__init__.py` em core/managers/

```python
# core/managers/__init__.py
from .base_manager import BaseManager
from .capture_manager import CaptureManager
from .inspection_manager import InspectionManager
from .history_manager import HistoryManager

__all__ = [
    'BaseManager',
    'CaptureManager',
    'InspectionManager',
    'HistoryManager',
]
```

### FASE 2: Migração history_manager (2 horas)

#### Tarefa 2.1: Mover history_manager.py para core/

**Arquivo origem**: `interfaces/desktop/managers/history_manager.py`  
**Arquivo destino**: `core/managers/history_manager.py`

**Mudanças**:
- Remover imports PyQt5
- Remover qualquer referência a signals
- Manter lógica pura

```python
# core/managers/history_manager.py
from typing import List, Optional, Dict, Any
import json
from pathlib import Path
import csv
import shutil

from .base_manager import BaseManager
from core.utils.logger import log

class HistoryManager(BaseManager):
    """
    Gerencia histórico de inspeções (agnóstico de UI).
    """
    
    def __init__(self, core, results_dir: Optional[Path] = None):
        super().__init__(core)
        self.results_dir = Path(results_dir) if results_dir else Path("data/results")
        self.loaded_history: List[Dict] = []
    
    def initialize(self) -> bool:
        """Inicializa o manager"""
        self.load_history()
        return True
    
    def cleanup(self) -> None:
        """Limpa recursos"""
        self.loaded_history.clear()
    
    def load_history(self) -> List[Dict]:
        """Carrega histórico de inspeções do disco"""
        # ... [código original mantido] ...
    
    # ... [resto dos métodos] ...
```

#### Tarefa 2.2: Criar wrapper em interfaces/desktop/managers/

```python
# interfaces/desktop/managers/history_manager.py
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from core.managers import HistoryManager as CoreHistoryManager

class HistoryManagerQt(QObject):
    """
    Wrapper Qt para HistoryManager.
    Adiciona signals PyQt5.
    """
    
    history_loaded = pyqtSignal()
    history_changed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, core, results_dir=None):
        super().__init__()
        self.manager = CoreHistoryManager(core, results_dir)
    
    def load_history(self):
        """Carrega histórico e emite signal"""
        try:
            self.manager.load_history()
            self.history_loaded.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def get_history_item(self, index):
        return self.manager.get_history_item(index)
    
    # Delegar outros métodos...
```

#### Tarefa 2.3: Criar wrapper em interfaces/web/managers/

```python
# interfaces/web/managers/history_manager.py
from typing import List, Dict, Any
from core.managers import HistoryManager as CoreHistoryManager

class HistoryManagerAPI:
    """
    Adapter para HistoryManager em FastAPI.
    Converte resultados para JSON.
    """
    
    def __init__(self, core, results_dir=None):
        self.manager = CoreHistoryManager(core, results_dir)
    
    async def get_all_history(self) -> List[Dict]:
        """Retorna histórico completo"""
        self.manager.load_history()
        return self.manager.loaded_history
    
    async def get_history_item(self, index: int) -> Dict:
        """Retorna item específico"""
        item = self.manager.get_history_item(index)
        if not item:
            raise ValueError(f"Item {index} não encontrado")
        return item
    
    async def get_summary_stats(self) -> Dict:
        """Retorna estatísticas"""
        return self.manager.get_summary_stats()
    
    # ... adaptar outros métodos ...
```

### FASE 3: Migração capture_manager (6 horas)

#### Tarefa 3.1: Extrair lógica pura para core/

```python
# core/managers/capture_manager.py
from typing import Dict, Any, Optional
from pathlib import Path

from .base_manager import BaseManager
from core.camera.camera_profiles import CameraProfileManager
from core.utils.logger import log

class CaptureManager(BaseManager):
    """
    Gerencia captura de imagens (lógica pura).
    NÃO contém threading ou UI.
    """
    
    def __init__(self, core, camera_profiles: Optional[CameraProfileManager] = None):
        super().__init__(core)
        self.camera_profiles = camera_profiles
        self.last_capture: Optional[Dict] = None
    
    def initialize(self) -> bool:
        """Inicializa o manager"""
        if self.camera_profiles:
            return self.camera_profiles.load_profiles()
        return True
    
    def cleanup(self) -> None:
        """Limpa recursos"""
        self.last_capture = None
    
    def capture_image(self) -> Dict[str, Any]:
        """
        Captura uma imagem.
        Retorna dict com sucesso, imagem, etc.
        """
        try:
            result = self.core.capture_image()
            if result.get("success"):
                self.last_capture = result
                self._notify("capture_completed", result)
            return result
        except Exception as e:
            error_data = {"error": str(e)}
            self._notify("capture_error", error_data)
            raise
    
    def apply_profile(self, profile_name: str) -> bool:
        """Aplica um perfil de câmera"""
        if not self.camera_profiles:
            return False
        
        profile = self.camera_profiles.get_profile(profile_name)
        if not profile:
            log.error(f"Perfil não encontrado: {profile_name}")
            return False
        
        # Aplicar configurações do perfil
        return self.core.camera_manager.apply_profile(profile)
    
    def get_last_capture(self) -> Optional[Dict]:
        """Retorna última captura"""
        return self.last_capture
```

#### Tarefa 3.2: Criar wrapper com threading em desktop/managers/

```python
# interfaces/desktop/managers/capture_manager.py
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject
from typing import Optional
import numpy as np

from core.managers import CaptureManager as CoreCaptureManager

class CaptureThread(QThread):
    """Thread para captura não-bloqueante"""
    image_captured = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, capture_manager: CoreCaptureManager):
        super().__init__()
        self.capture_manager = capture_manager
    
    def run(self):
        try:
            result = self.capture_manager.capture_image()
            if result.get("success"):
                self.image_captured.emit(result)
            else:
                self.error_occurred.emit("Captura falhou")
        except Exception as e:
            self.error_occurred.emit(str(e))

class CaptureManagerQt(QObject):
    """Wrapper Qt para CaptureManager com threading"""
    
    image_captured = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, core, camera_profiles=None):
        super().__init__()
        self.manager = CoreCaptureManager(core, camera_profiles)
        self.capture_thread: Optional[CaptureThread] = None
    
    def start_capture(self):
        """Inicia captura em thread separada"""
        if self.capture_thread and self.capture_thread.isRunning():
            self.error_occurred.emit("Captura já em andamento")
            return
        
        self.capture_thread = CaptureThread(self.manager)
        self.capture_thread.image_captured.connect(self._on_image_captured)
        self.capture_thread.error_occurred.connect(self._on_error)
        self.capture_thread.start()
    
    @pyqtSlot(dict)
    def _on_image_captured(self, result):
        self.image_captured.emit(result)
    
    @pyqtSlot(str)
    def _on_error(self, error):
        self.error_occurred.emit(error)
    
    def apply_profile(self, profile_name: str) -> bool:
        """Aplica perfil de câmera"""
        return self.manager.apply_profile(profile_name)
    
    def get_last_capture(self) -> Optional[dict]:
        """Retorna última captura"""
        return self.manager.get_last_capture()
```

#### Tarefa 3.3: Criar adapter REST em web/managers/

```python
# interfaces/web/managers/capture_manager.py
from typing import Dict, Any
from core.managers import CaptureManager as CoreCaptureManager

class CaptureManagerAPI:
    """
    Adapter para CaptureManager em FastAPI.
    """
    
    def __init__(self, core, camera_profiles=None):
        self.manager = CoreCaptureManager(core, camera_profiles)
    
    async def capture_image(self) -> Dict[str, Any]:
        """
        Captura uma imagem e retorna resultado.
        Endpoints: POST /api/capture
        """
        try:
            result = self.manager.capture_image()
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def apply_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Aplica perfil de câmera.
        Endpoint: POST /api/camera/profile/{profile_name}
        """
        try:
            success = self.manager.apply_profile(profile_name)
            return {
                "success": success,
                "profile": profile_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_last_capture(self) -> Dict[str, Any]:
        """
        Retorna última captura em cache.
        Endpoint: GET /api/capture/last
        """
        capture = self.manager.get_last_capture()
        if capture:
            return {"success": True, "data": capture}
        return {"success": False, "error": "Nenhuma captura disponível"}
```

### FASE 4: Migração inspection_manager (6 horas)

**Similar à Fase 3**, mas para lógica de inspeção.

Estrutura dos arquivos:
- `core/managers/inspection_manager.py` (lógica pura)
- `interfaces/desktop/managers/inspection_manager_qt.py` (threading PyQt5)
- `interfaces/web/managers/inspection_manager_api.py` (REST adapter)

### FASE 5: Atualizar MainWindow (3 horas)

```python
# interfaces/desktop/app.py - ANTES
from .managers import CaptureManager, InspectionManager, HistoryManager

# interfaces/desktop/app.py - DEPOIS
from .managers import CaptureManagerQt, InspectionManagerQt, HistoryManagerQt

class MainWindow(QMainWindow):
    def __init__(self):
        # ...
        # ANTES (acoplado)
        # self.capture_mgr = CaptureManager(self.core, ...)
        
        # DEPOIS (desacoplado)
        self.capture_mgr = CaptureManagerQt(self.core, ...)
        self.inspection_mgr = InspectionManagerQt(self.core, ...)
        self.history_mgr = HistoryManagerQt(self.core, ...)
```

### FASE 6: Atualizar WebServer (2 horas)

```python
# interfaces/web/server.py
from .managers import CaptureManagerAPI, InspectionManagerAPI, HistoryManagerAPI

class WebServer:
    def __init__(self, core):
        self.core = core
        self.capture_mgr = CaptureManagerAPI(core)
        self.inspection_mgr = InspectionManagerAPI(core)
        self.history_mgr = HistoryManagerAPI(core)
    
    def _setup_routes(self):
        @self.app.post("/api/capture")
        async def capture():
            return await self.capture_mgr.capture_image()
        
        @self.app.post("/api/segmentation")
        async def segmentation(image_data):
            return await self.inspection_mgr.perform_segmentation(image_data)
```

### FASE 7: Testes (3 horas)

#### Testes Unitários (core/managers/)

```python
# tests/test_core_managers.py
import pytest
from unittest.mock import Mock, MagicMock
from core.managers import CaptureManager, InspectionManager, HistoryManager

class TestCaptureManager:
    @pytest.fixture
    def mock_core(self):
        core = Mock()
        core.capture_image = Mock(return_value={
            "success": True,
            "image": np.zeros((100, 100, 3))
        })
        return core
    
    def test_capture_image_success(self, mock_core):
        manager = CaptureManager(mock_core)
        result = manager.capture_image()
        
        assert result["success"] is True
        assert "image" in result
    
    def test_apply_profile(self, mock_core):
        camera_profiles = Mock()
        camera_profiles.get_profile = Mock(return_value={"name": "test"})
        
        manager = CaptureManager(mock_core, camera_profiles)
        success = manager.apply_profile("test")
        
        assert success is True
```

#### Testes de Integração (desktop)

```python
# tests/test_desktop_integration.py
def test_capture_manager_qt_signals(qtbot):
    core = Mock()
    core.capture_image = Mock(return_value={"success": True})
    
    manager = CaptureManagerQt(core)
    
    with qtbot.waitSignal(manager.image_captured, timeout=1000):
        manager.start_capture()
```

#### Testes de Regressão

```
✓ Desktop continua funcionando igual
✓ Web API retorna mesmos resultados
✓ Histórico carrega corretamente
✓ Fallback de câmeras funciona
✓ Signals PyQt5 funcionam
```

---

## ✅ Testes de Verificação

### Após completar cada fase, executar:

```bash
# FASE 1
pytest tests/test_base_manager.py -v

# FASE 2
pytest tests/test_history_manager.py -v
python launcher.py --mode desktop  # Verificar UI
curl http://localhost:8000/api/history  # Verificar API

# FASE 3
pytest tests/test_capture_manager.py -v
python launcher.py --mode desktop  # Capturar imagem
curl -X POST http://localhost:8000/api/capture  # Testar API

# FASE 4
pytest tests/test_inspection_manager.py -v
python launcher.py --mode desktop  # Fazer inspeção
curl -X POST http://localhost:8000/api/segmentation  # Testar API

# FASE 5
python launcher.py --mode desktop  # Teste visual completo

# FASE 6
python launcher.py --mode web  # Teste web completo

# FASE 7
pytest tests/ -v --cov=core --cov=interfaces  # Cobertura final
```

---

## 🔄 Rollback

Se algo der errado, posso reverter qualquer fase:

```bash
# Reverter FASE 2 (exemplo)
git revert <commit-hash-fase-2>

# Ou selectively
git checkout main -- interfaces/desktop/managers/history_manager.py
```

**Backup antes de começar**:
```bash
git branch refactoring-fase2-backup main
```

---

## 📋 Checklist de Conclusão

Ao final da refatoração:

- [ ] Todos os 3 managers em `core/managers/`
- [ ] Todos wrappers em `interfaces/*/managers/`
- [ ] MainWindow usa `*ManagerQt`
- [ ] WebServer usa `*ManagerAPI`
- [ ] Testes passam (100% dos testes relevantes)
- [ ] Desktop funciona igual
- [ ] Web funciona igual
- [ ] Histórico migrado
- [ ] Documentação atualizada
- [ ] SYSTEM_SUMMARY.md atualizado

---

## 📊 Resultado Esperado

Após a refatoração:

### ✅ Conformidade SOLID

| Princípio | Antes | Depois |
|-----------|-------|--------|
| **SRP** | 8.5/10 | 9.5/10 |
| **OCP** | 8.8/10 | 9.6/10 |
| **LSP** | 9.2/10 | 9.4/10 |
| **ISP** | 8.2/10 | 9.1/10 |
| **DIP** | 8.5/10 | 9.7/10 |

**Nota Final**: 8.5/10 → **9.4/10** (+10%)

### ✅ Reusabilidade

- Desktop usa `core/managers/` ✓
- Web usa `core/managers/` ✓
- CLI pode usar `core/managers/` ✓
- Reutilização: 50% → **90%**

### ✅ Testabilidade

- Testes core sem PyQt5 ✓
- Testes web sem FastAPI (mock) ✓
- Testes desktop com Qt ✓
- Coverage: 7.5/10 → **9.2/10**

---

## 🚀 Próximos Passos

1. **Hoje**: Revisar este plano
2. **Amanhã**: Iniciar FASE 1 (preparação)
3. **3-4 dias**: Completar FASES 1-7
4. **Depois**: Implementar Fase 3 (quebrar SystemCore)

---

**Plano criado**: 22/01/2026  
**Status**: 🔵 Pronto para implementação  
**Aprovação**: Aguardando feedback
