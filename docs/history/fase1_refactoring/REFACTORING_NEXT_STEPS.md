# 🔄 Próximas Etapas da Refatoração

## Fase 2: InspectionManager Integration (2-3 horas)

### O que precisa ser feito:
1. Criar `InspectionUIManager` para coordenar UI de inspeção
2. Extrair métodos de inspeção do MainWindow
3. Integrar com o `InspectionManager` já criado

### Métodos a mover para InspectionUIManager:
```python
# De MainWindow para novo InspectionUIManager:
- _on_inspection_type_changed()         (line ~1615)
- _start_inspection()                   (line ~1635)
- _perform_inference()                  (line ~1680)
- on_inspection_completed()             (line ~1730)
- on_inspection_error()                 (line ~1743)
- display_inspection_results()          (line ~1750)
- _format_result_text()                 (line ~1800+)
```

### Arquitetura proposta:
```python
# managers/inspection_ui_manager.py (NOVO)
class InspectionUIManager(QObject):
    """Coordena UI de inspeção - signals de inspeção"""
    
    inspection_started = pyqtSignal()
    inspection_completed = pyqtSignal(dict, str)  # (results, type)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, core, inspection_mgr):
        self.core = core
        self.inspection_mgr = inspection_mgr  # Usa manager existente
    
    def start_inspection(self, image, type, model):
        """Inicia inspeção (coordena UI + core)"""
        self.inspection_started.emit()
        self.inspection_mgr.perform_inspection(image, type, model)
    
    def format_results_for_display(self, results, type):
        """Formata resultados para UI"""
        pass
```

### Integração no MainWindow:
```python
class MainWindow(QMainWindow):
    def __init__(self, core):
        # NOVO
        self.inspection_ui_mgr = InspectionUIManager(core, self.inspection_mgr)
        self.inspection_ui_mgr.inspection_completed.connect(self.on_inspection_completed)
        
        # VELHO (a remover depois)
        self._on_inspection_type_changed = self.inspection_ui_mgr._on_inspection_type_changed
        self._start_inspection = self.inspection_ui_mgr.start_inspection
```

---

## Fase 3: HistoryManager Integration (1-2 horas)

### O que precisa ser feito:
1. Atualizar `HistoryManager` para trabalhar com UI
2. Criar `HistoryUIManager` se necessário
3. Integrar com MainWindow

### Métodos a mover:
```python
# De MainWindow para novo HistoryUIManager:
- load_history()                  (line ~1900)
- view_history_item()             (line ~1920)
- _format_result_text()           (line ~1950+)
- export_history()                (line ~2000+)
- clear_results()                 (line ~2050+)
```

---

## Fase 4: CameraUIManager (2-3 horas)

### O que precisa ser feito:
1. Criar `CameraUIManager` para gerenciar UI de câmera
2. Extrair métodos de câmera do MainWindow
3. Integrar com `CameraManager` existente

### Métodos a mover:
```python
# De MainWindow:
- update_camera_info()             (line ~1350)
- _update_camera_combo()           (line ~1370)
- _on_camera_combo_changed()       (line ~1400)
- _after_camera_switch()           (line ~1420)
- reload_camera()                  (line ~1440)
- _reload_camera_parameters()      (line ~2200)
- _create_parameter_widget()       (line ~2230)
- _on_camera_parameter_changed()   (line ~2260)
```

---

## Fase 5: ProfileUIManager (1-2 horas)

### O que precisa ser feito:
1. Criar `ProfileUIManager` para gerenciar perfis
2. Extrair métodos de perfil do MainWindow
3. Integrar com sistema de perfis existente

### Métodos a mover:
```python
# De MainWindow:
- _reload_profiles_list()          (line ~2300)
- _on_profile_selected()           (line ~2330)
- _create_new_profile()            (line ~2360)
- _load_selected_profile()         (line ~2390)
- _save_current_profile()          (line ~2420)
- _delete_selected_profile()       (line ~2450)
```

---

## Fase 6: Limpeza Final (1 hora)

### O que fazer:
1. Remover variáveis duplicadas em MainWindow
2. Remover state local desnecessário
3. Sincronizar todo state com managers
4. Testes de integração completos
5. Validar que nenhuma funcionalidade foi perdida

---

## 📊 Estrutura Final Esperada

```
MainWindow (30-40 métodos)
│
├── _create_ui()                  (UI creation)
├── _connect_core_callbacks()     (core integration)
├── on_event_from_ui()            (UI events)
│
└── Delegados:
    ├── CaptureManager (11 métodos)        ✅ DONE
    ├── InspectionUIManager (6-8 métodos)  ⏳ TODO
    ├── HistoryUIManager (4-6 métodos)     ⏳ TODO
    ├── CameraUIManager (8-10 métodos)     ⏳ TODO
    └── ProfileUIManager (6-8 métodos)     ⏳ TODO
```

---

## 🔍 Como Refatorar Cada Fase

### Template para mover método:

1. **Criar novo arquivo**: `interfaces/desktop/managers/xxx_manager.py`

2. **Extrair métodos relacionados**:
   ```python
   # Copiar método de MainWindow
   def method_name(self, param):
       # ... código do MainWindow
   ```

3. **Adaptar para manager** (remover dependências Qt quando possível):
   ```python
   # No manager - remover self.ui_element
   # Substituir por signals
   self.signal.emit(resultado)
   ```

4. **Atualizar MainWindow**:
   ```python
   # Novo em __init__
   self.xxx_mgr = XXXUIManager(...)
   self.xxx_mgr.signal.connect(self.on_signal)
   
   # Remover método original ou fazer delegation:
   def method_name(self):
       self.xxx_mgr.method_name()
   ```

5. **Validar**:
   - Sintaxe: `python -m py_compile interfaces/desktop/managers/xxx_manager.py`
   - Imports: `from interfaces.desktop.managers import XXXUIManager`
   - Funcionalidade: Testar no sistema

---

## 📋 Checklist para Cada Fase

### Antes de começar:
- [ ] Criar branch (ou cópia de backup)
- [ ] Documentar métodos atuais
- [ ] Planejar dependências

### Durante a implementação:
- [ ] Copiar método para novo manager
- [ ] Remover dependências de MainWindow
- [ ] Adicionar docstrings
- [ ] Criar signals necessários
- [ ] Adicionar testes unitários

### Após implementação:
- [ ] Validar sintaxe
- [ ] Validar imports
- [ ] Testar funcionamento
- [ ] Remover código antigo
- [ ] Atualizar documentação

---

## 🧪 Testes Recomendados

### Para cada fase:
```python
# test_managers.py

def test_capture_manager():
    mgr = CaptureManager(mock_core)
    mgr.set_crop_settings(True, bbox)
    result = mgr.process_captured_image(image, info, ts)
    assert result is not None

def test_inspection_manager():
    mgr = InspectionManager(mock_core)
    result = mgr.perform_inspection(image, "segmentation", "model")
    assert "results" in result

# etc...
```

---

## ⚡ Dicas para Acelerar

1. **Use Find & Replace**: Buscar todos os usos do método antes de mover
2. **Documente Signals**: Cada manager deve documentar seus signals
3. **Reutilize Padrão**: Use o mesmo padrão de CaptureManager para outros
4. **Teste Incrementalmente**: Teste cada fase separadamente
5. **Mantenha Compatibilidade**: Não quebre código antigo até ter tudo pronto

---

## 🎯 Meta Final

Após todas as 6 fases:

```
✅ MainWindow: 30-40 métodos (agora: 52)
✅ Cada manager: especializado em 1 coisa
✅ Código testável sem PyQt5
✅ Reutilizável em web/CLI
✅ Documentação completa
✅ Testes unitários inclusos
✅ 0 código duplicado
```

---

## 📞 Suporte

Se tiver dúvidas durante a refatoração:
1. Consulte [APP_REFACTORING_GUIDE.md](APP_REFACTORING_GUIDE.md)
2. Veja [REFACTORING_PHASE1_REPORT.md](REFACTORING_PHASE1_REPORT.md) como exemplo
3. Compare com `CaptureManager` implementado
4. Mantenha padrão: Manager + Signals + Sem Qt no core

---

**Status**: Ready for Phase 2 🚀
