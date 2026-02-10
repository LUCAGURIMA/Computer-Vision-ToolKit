"""
Testes para BaseManager.

Verifica se a classe abstrata funciona corretamente
e garante que subclasses implementem interface esperada.
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.managers import BaseManager


class ConcreteManager(BaseManager):
    """Manager concreto para testes"""
    
    def initialize(self) -> bool:
        self._log("info", "Inicializando")
        return True
    
    def cleanup(self) -> None:
        self._log("info", "Limpando")


class TestBaseManager:
    """Testes da classe BaseManager"""
    
    @pytest.fixture
    def mock_core(self):
        """Cria mock do SystemCore"""
        core = Mock()
        core._notify = Mock()
        return core
    
    def test_create_concrete_manager(self, mock_core):
        """Testa criação de manager concreto"""
        manager = ConcreteManager(mock_core)
        
        assert manager.core is mock_core
        assert manager is not None
    
    def test_initialize_abstract_method(self, mock_core):
        """Testa que initialize é abstract"""
        # Não deve ser possível instanciar BaseManager diretamente
        with pytest.raises(TypeError):
            BaseManager(mock_core)
    
    def test_initialize_called(self, mock_core):
        """Testa que initialize pode ser chamado"""
        manager = ConcreteManager(mock_core)
        result = manager.initialize()
        
        assert result is True
    
    def test_cleanup_called(self, mock_core):
        """Testa que cleanup pode ser chamado"""
        manager = ConcreteManager(mock_core)
        manager.cleanup()  # Não deve falhar
    
    def test_notify_emits_event(self, mock_core):
        """Testa que _notify() chama core._notify()"""
        manager = ConcreteManager(mock_core)
        
        test_data = {"key": "value"}
        manager._notify("test_event", test_data)
        
        mock_core._notify.assert_called_once_with("test_event", test_data)
    
    def test_notify_without_data(self, mock_core):
        """Testa que _notify() funciona sem data"""
        manager = ConcreteManager(mock_core)
        
        manager._notify("test_event")
        
        mock_core._notify.assert_called_once_with("test_event", {})
    
    def test_notify_when_core_missing_notify(self):
        """Testa que _notify() é seguro se core não tem _notify"""
        core = Mock(spec=[])  # Sem método _notify
        manager = ConcreteManager(core)
        
        # Não deve falhar
        manager._notify("test_event", {"data": "value"})
    
    def test_repr(self, mock_core):
        """Testa representação em string"""
        manager = ConcreteManager(mock_core)
        repr_str = repr(manager)
        
        assert "ConcreteManager" in repr_str
        assert "Mock" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
