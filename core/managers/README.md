# 🧩 Core Managers

## Descrição

Managers agnósticos de UI que encapsulam a lógica de negócio do sistema.

**Características**:
- ✅ Sem dependência de PyQt5, FastAPI ou qualquer UI
- ✅ Testáveis sem mockagem complexa
- ✅ Reutilizáveis em múltiplas interfaces (desktop, web, CLI)
- ✅ Seguem padrão BaseManager (interface comum)
- ✅ Usam sistema de callbacks para notificação

## Estrutura

```
core/managers/
├── __init__.py              # Exports dos managers
├── base_manager.py          # Classe abstrata base
├── capture_manager.py       # Captura de imagens (lógica pura)
├── inspection_manager.py    # Execução de inspeções (lógica pura)
└── history_manager.py       # Gerenciamento de histórico (lógica pura)
```

## Princípios

### 1. **Single Responsibility**
- Cada manager tem UMA responsabilidade única
- CaptureManager = captura
- InspectionManager = inspeção
- HistoryManager = histórico

### 2. **Agnóstico de UI**
```python
# ✅ CORRETO (agnóstico)
class CaptureManager(BaseManager):
    def capture_image(self) -> Dict:
        return self.core.capture_image()

# ❌ ERRADO (acoplado)
class CaptureManager(QObject):
    capture_completed = pyqtSignal(dict)  # ← PyQt5 específico!
```

### 3. **Observável (Callbacks)**
```python
# Notifica listeners sem acoplamento
self._notify("capture_completed", {"image": img})
```

### 4. **Testável**
```python
# Pode testar sem UI
manager = CaptureManager(mock_core)
result = manager.capture_image()
assert result["success"]
```

## BaseManager - Interface Comum

Todos os managers herdam de `BaseManager` que define:

### Métodos Obrigatórios

```python
class MyManager(BaseManager):
    def initialize(self) -> bool:
        """Preparar recursos. Chamado na startup."""
        pass
    
    def cleanup(self) -> None:
        """Liberar recursos. Chamado no shutdown."""
        pass
```

### Métodos Utilitários

```python
# Notificar listeners
self._notify("event_name", {"data": value})

# Log com prefixo do manager
self._log("info", "Mensagem")      # [ManagerName] Mensagem
self._log("warning", "Aviso")
self._log("error", "Erro")
self._log("debug", "Debug info")
```

## Uso

### Em Testes

```python
from core.managers import CaptureManager

def test_capture():
    core = Mock()
    manager = CaptureManager(core)
    
    result = manager.capture_image()
    assert result["success"]
```

### Em Desktop (PyQt5)

```python
from core.managers import CaptureManager
from interfaces.desktop.managers import CaptureManagerQt

# Manager core (lógica pura)
core_manager = CaptureManager(core)

# Wrapper Qt (threading + signals)
qt_manager = CaptureManagerQt(core)
qt_manager.image_captured.connect(on_image_captured)
qt_manager.start_capture()  # Executa em thread
```

### Em Web (FastAPI)

```python
from core.managers import CaptureManager

class CaptureManagerAPI:
    def __init__(self, core):
        self.manager = CaptureManager(core)
    
    async def capture(self):
        result = self.manager.capture_image()
        return {"success": True, "data": result}

# Endpoint
@app.post("/api/capture")
async def capture_endpoint():
    return await api_manager.capture()
```

## Callbacks Disponíveis

Cada manager notifica eventos específicos:

### CaptureManager
- `"capture_completed"` - Captura finalizada com sucesso
- `"capture_error"` - Erro durante captura

### InspectionManager
- `"inspection_started"` - Inspeção iniciada
- `"inspection_completed"` - Inspeção concluída
- `"inspection_error"` - Erro durante inspeção

### HistoryManager
- `"history_loaded"` - Histórico carregado
- `"history_modified"` - Histórico modificado
- `"history_error"` - Erro ao manipular histórico

## Exemplo Completo

### 1. Manager Lógica Pura (core/)

```python
# core/managers/my_manager.py
class MyManager(BaseManager):
    def initialize(self) -> bool:
        self._log("info", "Inicializando")
        return True
    
    def cleanup(self) -> None:
        self._log("info", "Limpando")
    
    def do_something(self) -> Dict:
        """Executa operação de negócio"""
        try:
            result = self.core.do_something_core()
            self._notify("something_completed", result)
            return {"success": True, "data": result}
        except Exception as e:
            self._notify("something_error", {"error": str(e)})
            return {"success": False, "error": str(e)}
```

### 2. Wrapper Qt (interfaces/desktop/)

```python
# interfaces/desktop/managers/my_manager_qt.py
class MyManagerQt(QObject):
    something_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, core):
        super().__init__()
        self.manager = MyManager(core)
    
    def do_something_async(self):
        """Executa em thread separada"""
        thread = Thread(self.manager.do_something)
        thread.completed.connect(self._on_completed)
        thread.error.connect(self._on_error)
        thread.start()
    
    def _on_completed(self, result):
        self.something_completed.emit(result)
```

### 3. REST Adapter (interfaces/web/)

```python
# interfaces/web/managers/my_manager_api.py
class MyManagerAPI:
    def __init__(self, core):
        self.manager = MyManager(core)
    
    async def do_something(self) -> Dict:
        """Endpoint: POST /api/something"""
        return self.manager.do_something()
```

## Testes

Para testar os managers:

```bash
# Testar base_manager
pytest tests/test_base_manager.py -v

# Testar todos os managers
pytest tests/test_*_manager.py -v

# Com cobertura
pytest tests/ -v --cov=core.managers
```

## Status

- ✅ `BaseManager` - Implementado
- ⏳ `CaptureManager` - Em implementação (Fase 3)
- ⏳ `InspectionManager` - Em implementação (Fase 4)
- ⏳ `HistoryManager` - Em implementação (Fase 2)

## Próximos Passos

1. **FASE 2**: Migrar HistoryManager para core/managers/
2. **FASE 3**: Migrar CaptureManager para core/managers/
3. **FASE 4**: Migrar InspectionManager para core/managers/

---

**Última atualização**: 22/01/2026  
**Status**: 🟢 Pronto para Fase 2
