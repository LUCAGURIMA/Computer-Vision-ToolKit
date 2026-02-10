"""
Testes para HistoryManager (core/managers/history_manager.py).

Testes focam na lógica de negócio pura (sem UI).
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from core.managers import HistoryManager


@pytest.fixture
def mock_core():
    """Cria mock do SystemCore"""
    core = Mock()
    core._notify = Mock()
    return core


@pytest.fixture
def temp_results_dir():
    """Cria diretório temporário para testes"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_inspection_data():
    """Amostra de dados de inspeção"""
    return {
        "timestamp": "20260122_093000",
        "inspection_type": "segmentation",
        "model_name": "fruta",
        "results": {
            "class": "banana",
            "confidence": 0.95,
            "area": 1500
        }
    }


@pytest.fixture
def populated_results_dir(temp_results_dir, sample_inspection_data):
    """Cria diretório com dados de teste"""
    # Criar primeira inspeção
    result_dir1 = temp_results_dir / "20260122_093000"
    result_dir1.mkdir()
    with open(result_dir1 / "inspection_data.json", "w") as f:
        json.dump(sample_inspection_data, f)
    
    # Criar segunda inspeção (classificação)
    result_dir2 = temp_results_dir / "20260122_094000"
    result_dir2.mkdir()
    with open(result_dir2 / "inspection_data.json", "w") as f:
        json.dump({
            "timestamp": "20260122_094000",
            "inspection_type": "classification",
            "model_name": "frutas_class",
            "results": {
                "predicted_class": "apple",
                "confidence": 0.88,
                "class_confidences": {
                    "apple": 0.88,
                    "banana": 0.10,
                    "orange": 0.02
                }
            }
        }, f)
    
    return temp_results_dir


class TestHistoryManager:
    """Testes para HistoryManager"""
    
    def test_create_history_manager(self, mock_core, temp_results_dir):
        """Testa criação de HistoryManager"""
        manager = HistoryManager(mock_core, temp_results_dir)
        
        assert manager.core is mock_core
        assert manager.results_dir == temp_results_dir
        assert manager.loaded_history == []
    
    def test_initialize(self, mock_core, temp_results_dir):
        """Testa inicialização do manager"""
        manager = HistoryManager(mock_core, temp_results_dir)
        result = manager.initialize()
        
        assert result is True
    
    def test_cleanup(self, mock_core, temp_results_dir):
        """Testa limpeza de recursos"""
        manager = HistoryManager(mock_core, temp_results_dir)
        manager.loaded_history = [{"test": "data"}]
        
        manager.cleanup()
        
        assert manager.loaded_history == []
    
    def test_load_empty_history(self, mock_core, temp_results_dir):
        """Testa carregamento de histórico vazio"""
        manager = HistoryManager(mock_core, temp_results_dir)
        history = manager.load_history()
        
        assert history == []
        mock_core._notify.assert_called()
    
    def test_load_history_with_data(self, mock_core, populated_results_dir):
        """Testa carregamento de histórico com dados"""
        manager = HistoryManager(mock_core, populated_results_dir)
        history = manager.load_history()
        
        assert len(history) == 2
        assert history[0]["inspection_type"] in ["segmentation", "classification"]
        assert "timestamp" in history[0]
        assert "data" in history[0]
    
    def test_load_history_order(self, mock_core, populated_results_dir):
        """Testa ordenação do histórico (mais recente primeiro)"""
        manager = HistoryManager(mock_core, populated_results_dir)
        history = manager.load_history()
        
        # Mais recente deve vir primeiro
        assert history[0]["timestamp"] == "20260122_094000"
        assert history[1]["timestamp"] == "20260122_093000"
    
    def test_get_history_item_valid(self, mock_core, populated_results_dir):
        """Testa obtenção de item por índice válido"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        item = manager.get_history_item(0)
        
        assert item is not None
        assert "timestamp" in item
        assert "inspection_type" in item
    
    def test_get_history_item_invalid(self, mock_core, temp_results_dir):
        """Testa obtenção de item com índice inválido"""
        manager = HistoryManager(mock_core, temp_results_dir)
        manager.load_history()
        
        item = manager.get_history_item(999)
        
        assert item is None
    
    def test_get_history_by_timestamp(self, mock_core, populated_results_dir):
        """Testa busca por timestamp"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        item = manager.get_history_by_timestamp("20260122_093000")
        
        assert item is not None
        assert item["timestamp"] == "20260122_093000"
    
    def test_get_history_by_invalid_timestamp(self, mock_core, populated_results_dir):
        """Testa busca por timestamp inexistente"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        item = manager.get_history_by_timestamp("99999999_999999")
        
        assert item is None
    
    def test_get_history_count(self, mock_core, populated_results_dir):
        """Testa contagem de itens"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        count = manager.get_history_count()
        
        assert count == 2
    
    def test_view_history_item_segmentation(self, mock_core, populated_results_dir):
        """Testa formatação de item segmentação"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        # Encontrar item de segmentação
        for i, item in enumerate(manager.loaded_history):
            if item["inspection_type"] == "segmentation":
                view = manager.view_history_item(i)
                assert view is not None
                assert "banana" in view
                break
    
    def test_view_history_item_classification(self, mock_core, populated_results_dir):
        """Testa formatação de item classificação"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        # Encontrar item de classificação
        for i, item in enumerate(manager.loaded_history):
            if item["inspection_type"] == "classification":
                view = manager.view_history_item(i)
                assert view is not None
                assert "apple" in view
                break
    
    def test_export_to_csv(self, mock_core, populated_results_dir, temp_results_dir):
        """Testa exportação para CSV"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        csv_path = temp_results_dir / "export.csv"
        success = manager.export_to_csv(csv_path)
        
        assert success is True
        assert csv_path.exists()
        
        # Validar conteúdo do CSV
        with open(csv_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == 3  # header + 2 items
            assert "Timestamp" in lines[0]
    
    def test_export_empty_history(self, mock_core, temp_results_dir):
        """Testa exportação com histórico vazio"""
        manager = HistoryManager(mock_core, temp_results_dir)
        
        csv_path = temp_results_dir / "export.csv"
        success = manager.export_to_csv(csv_path)
        
        assert success is False
        assert not csv_path.exists()
    
    def test_delete_history_item(self, mock_core, populated_results_dir):
        """Testa deleção de item"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        original_count = manager.get_history_count()
        success = manager.delete_history_item("20260122_093000")
        
        assert success is True
        assert manager.get_history_count() == original_count - 1
    
    def test_delete_nonexistent_item(self, mock_core, populated_results_dir):
        """Testa deleção de item inexistente"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        success = manager.delete_history_item("99999999_999999")
        
        assert success is False
    
    def test_clear_all_history(self, mock_core, populated_results_dir):
        """Testa limpeza total"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        success = manager.clear_all_history()
        
        assert success is True
        assert manager.get_history_count() == 0
        # Diretório deve ter sido recriado
        assert populated_results_dir.exists()
    
    def test_get_summary_stats(self, mock_core, populated_results_dir):
        """Testa estatísticas"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        stats = manager.get_summary_stats()
        
        assert stats["total"] == 2
        assert stats["segmentation"] == 1
        assert stats["classification"] == 1
        assert "fruta" in stats["models"]
        assert "frutas_class" in stats["models"]
    
    def test_get_summary_stats_empty(self, mock_core, temp_results_dir):
        """Testa estatísticas com histórico vazio"""
        manager = HistoryManager(mock_core, temp_results_dir)
        
        stats = manager.get_summary_stats()
        
        assert stats["total"] == 0
        assert stats["segmentation"] == 0
        assert stats["classification"] == 0
    
    def test_notify_on_load(self, mock_core, populated_results_dir):
        """Testa que notificação é emitida ao carregar"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        # Verificar que _notify foi chamado
        calls = [call[0][0] for call in mock_core._notify.call_args_list]
        assert "history_loaded" in calls
    
    def test_notify_on_delete(self, mock_core, populated_results_dir):
        """Testa que notificação é emitida ao deletar"""
        manager = HistoryManager(mock_core, populated_results_dir)
        manager.load_history()
        
        mock_core._notify.reset_mock()
        manager.delete_history_item("20260122_093000")
        
        # Verificar notificação
        calls = [call[0][0] for call in mock_core._notify.call_args_list]
        assert "history_modified" in calls


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
