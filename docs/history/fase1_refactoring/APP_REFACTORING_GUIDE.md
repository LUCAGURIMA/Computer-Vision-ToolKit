# 📊 Análise: MainWindow em app.py

## 📈 Estatísticas

| Métrica | Valor | Avaliação |
|---------|-------|-----------|
| **Total de métodos em MainWindow** | **52 métodos** | ⚠️ ACIMA DO IDEAL |
| **Média recomendada (clean code)** | ~15-20 métodos | ❌ VIOLANDO |
| **Linhas de código** | ~2100 linhas | ⚠️ MUITO GRANDE |
| **Outras classes no arquivo** | 7 classes adicionais | ✅ OK |
| **Total de métodos no arquivo** | ~91 métodos | ❌ MUITO ALTO |

---

## 🔴 Problemas Identificados

### 1. **MainWindow Violando Single Responsibility Principle (SRP)**

```python
class MainWindow(QMainWindow):  # ❌ Está fazendo TUDO
    # Responsabilidades acumuladas:
    
    # 1. Gerenciar UI (tabelas, labels, botões)
    def _create_ui(self)
    def _create_capture_tab(self)
    def _create_inspection_tab(self)
    def _create_settings_tab(self)
    
    # 2. Gerenciar câmeras
    def update_camera_info(self)
    def _update_camera_combo(self)
    def reload_camera(self)
    def _reload_camera_parameters(self)
    def _create_parameter_widget(self)
    
    # 3. Gerenciar captura
    def capture_image(self)
    def on_image_captured(self)
    def display_image(self)
    
    # 4. Gerenciar inspeção
    def perform_inspection(self)
    def _start_inspection(self)
    def on_inspection_completed(self)
    def display_inspection_results(self)
    
    # 5. Gerenciar histórico
    def load_history(self)
    def view_history_item(self)
    def export_history(self)
    
    # 6. Gerenciar perfis
    def _create_new_profile(self)
    def _load_selected_profile(self)
    def _save_current_profile(self)
    def _delete_selected_profile(self)
    
    # 7. Gerenciar crop
    def _on_crop_toggled(self)
    def _reset_crop(self)
    def _open_crop_editor(self)
    
    # E mais...
```

**Impacto**: Difícil de testar, manter, entender e modificar.

---

## ✅ Solução: Refatorar em Submódulos

### **Antes** (problema atual):
```
MainWindow (52 métodos)
├── Captura (4 métodos)
├── Inspeção (6 métodos)
├── Histórico (3 métodos)
├── Câmera (7 métodos)
├── Perfis (4 métodos)
└── ... (28 outros)
```

### **Depois** (proposto):
```
MainWindow (10-15 métodos) - coordena apenas
├── CaptureManager (5-6 métodos)
│   ├── capture_image()
│   ├── display_image()
│   └── handle_captured_image()
├── InspectionManager (6-8 métodos)
│   ├── perform_inspection()
│   ├── display_results()
│   └── save_results()
├── HistoryManager (3-4 métodos)
│   ├── load_history()
│   ├── view_item()
│   └── export()
├── CameraManager (UI) (6-7 métodos)
│   ├── update_info()
│   ├── reload_parameters()
│   └── change_camera()
└── ProfileManager (UI) (4-5 métodos)
    ├── create_profile()
    ├── load_profile()
    └── delete_profile()
```

---

## 📋 Refatoração Proposta

### **Passo 1: Criar `CaptureManager`**

```python
# Novo arquivo: interfaces/desktop/managers/capture_manager.py

from typing import Optional, Callable
import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject

class CaptureManager(QObject):
    """Gerencia captura de imagens (separa lógica de UI)"""
    
    image_captured = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.current_image = None
        self.raw_image = None
        self.crop_enabled = False
        self.crop_bbox = None
    
    def capture_image(self):
        """Captura imagem (thread separada)"""
        # Thread de captura
        pass
    
    def display_image(self, image: np.ndarray):
        """Processa e retorna imagem para display"""
        return self._process_image(image)
    
    def apply_crop_if_enabled(self, image: np.ndarray):
        """Aplica crop se habilitado"""
        if self.crop_enabled and self.crop_bbox:
            return self.core.preprocess_image(image, self._get_crop_ops())
        return image
    
    def _get_crop_ops(self):
        """Retorna operações de crop"""
        return [{"name": "crop", "bbox": self.crop_bbox}]
```

### **Passo 2: Criar `InspectionManager`**

```python
# Novo arquivo: interfaces/desktop/managers/inspection_manager.py

class InspectionManager(QObject):
    """Gerencia inspeção (separa lógica de UI)"""
    
    inspection_completed = pyqtSignal(dict, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.current_results = None
        self.inspection_image = None
    
    def perform_inspection(self, image: np.ndarray, inspection_type: str, model_name: str):
        """Executa inspeção (thread separada)"""
        # Thread de inspeção
        pass
    
    def save_results(self, image: np.ndarray):
        """Salva resultados em disco"""
        pass
    
    def format_results(self, results: dict, inspection_type: str) -> str:
        """Formata resultados para exibição"""
        pass
```

### **Passo 3: Criar `HistoryManager`**

```python
# Novo arquivo: interfaces/desktop/managers/history_manager.py

class HistoryManager(QObject):
    """Gerencia histórico de inspeções"""
    
    def __init__(self, core):
        super().__init__()
        self.core = core
    
    def load_history(self) -> List[dict]:
        """Carrega histórico de resultados"""
        pass
    
    def view_item(self, result_dir: Path) -> dict:
        """Carrega dados de uma inspeção anterior"""
        pass
    
    def export_csv(self, output_path: Path):
        """Exporta histórico como CSV"""
        pass
```

### **Passo 4: Simplificar MainWindow**

```python
class MainWindow(QMainWindow):
    """Janela principal - apenas coordena managers"""
    
    def __init__(self, core: SystemCore):
        super().__init__()
        self.core = core
        
        # Cria managers (delegados)
        self.capture_mgr = CaptureManager(core)
        self.inspection_mgr = InspectionManager(core)
        self.history_mgr = HistoryManager(core)
        
        # Conecta signals
        self.capture_mgr.image_captured.connect(self.on_image_captured)
        self.inspection_mgr.inspection_completed.connect(self.on_inspection_completed)
        
        # Cria UI
        self._create_ui()
    
    # ========== UI (5-10 métodos) ==========
    def _create_ui(self):
        """Cria abas principais"""
        self._create_capture_tab()
        self._create_inspection_tab()
        self._create_results_tab()
        self._create_settings_tab()
    
    def _create_capture_tab(self):
        """Cria apenas a estrutura UI"""
        # Botão conecta a:
        btn_capture.clicked.connect(self.capture_mgr.capture_image)
    
    # ========== Handlers (5-8 métodos) ==========
    def on_image_captured(self, result: dict):
        """Delegado de captura"""
        self.capture_mgr.apply_crop_if_enabled(result["image"])
        self.display_image(result["image"])
    
    def on_inspection_completed(self, result: dict, inspection_type: str):
        """Delegado de inspeção"""
        self.display_inspection_results(result, inspection_type)
        if self.auto_save_check.isChecked():
            self.inspection_mgr.save_results(...)
    
    # ========== Display (3-4 métodos) ==========
    def display_image(self, image: np.ndarray):
        """Apenas exibe, sem lógica"""
        pixmap = self._numpy_to_pixmap(image)
        self.image_label.setPixmap(pixmap)
    
    def display_inspection_results(self, result: dict, inspection_type: str):
        """Apenas exibe resultados formatados"""
        formatted = self.inspection_mgr.format_results(result, inspection_type)
        self.results_text.setText(formatted)
```

---

## 🎯 Benefícios da Refatoração

| Benefício | Antes | Depois |
|-----------|-------|--------|
| **Métodos por classe** | 52 | ~15 (MainWindow) + ~6 (cada manager) |
| **Responsabilidades** | 7+ | 1 por classe |
| **Testabilidade** | Difícil (UI acoplada) | Fácil (managers testáveis sem UI) |
| **Reutilização** | Impossível | ✅ Managers reutilizáveis |
| **Manutenção** | Complicada | Simples e modular |
| **Linhas MainWindow** | ~2100 | ~300 |

---

## 📝 Exemplo de Teste com Refatoração

```python
# test_managers.py
import unittest

class TestCaptureManager(unittest.TestCase):
    
    def setUp(self):
        self.core = MockSystemCore()
        self.mgr = CaptureManager(self.core)
    
    def test_capture_image(self):
        """Testa captura sem UI"""
        self.mgr.capture_image()
        # Verifica resultado
    
    def test_apply_crop(self):
        """Testa crop sem UI"""
        image = np.zeros((100, 100, 3))
        self.mgr.crop_enabled = True
        self.mgr.crop_bbox = [10, 10, 50, 50]
        
        result = self.mgr.apply_crop_if_enabled(image)
        self.assertEqual(result.shape, (40, 40, 3))

class TestInspectionManager(unittest.TestCase):
    
    def test_inspection_classification(self):
        """Testa inspeção sem UI"""
        # Testa lógica pura
        pass
```

---

## 🚀 Cronograma de Refatoração

**Fase 1 (Fácil - 1-2 horas)**
- ✅ Criar `CaptureManager`
- ✅ Mover métodos de captura

**Fase 2 (Médio - 2-3 horas)**
- ✅ Criar `InspectionManager`
- ✅ Criar `HistoryManager`

**Fase 3 (Médio - 2-3 horas)**
- ✅ Criar managers de câmera e perfil
- ✅ Testar integração

**Fase 4 (Fácil - 1 hora)**
- ✅ Simplificar MainWindow
- ✅ Limpar código

---

## 🎓 Conclusão

### ❌ **Estado Atual: VIOLANDO SRP**
- 52 métodos em uma classe
- 2100+ linhas
- Múltiplas responsabilidades
- Difícil de testar

### ✅ **Estado Proposto: SEGUINDO SRP**
- MainWindow: ~15 métodos (coordenação)
- Cada Manager: ~6 métodos (especializado)
- ~300 linhas por classe
- Fácil de testar e manter

### 📌 **Prioridade: ALTA**
Esta refatoração melhoraria significativamente:
- Manutenibilidade
- Testabilidade
- Reusabilidade
- Clareza do código
