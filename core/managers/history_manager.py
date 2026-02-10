"""
HistoryManager - Gerencia histórico de inspeções (agnóstico de UI).

Responsabilidade: Gerenciar carregamento, visualização, exportação e deleção
de histórico de inspeções sem dependência de UI.

Design: Lógica pura - pode ser usada em desktop, web, CLI, etc.
"""

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
    
    Funcionalidades:
    - Carregar histórico do disco
    - Buscar inspeções por índice ou timestamp
    - Visualizar formatado
    - Exportar para CSV
    - Deletar itens
    - Obter estatísticas
    
    Não contém: Threading, signals, UI, etc.
    """
    
    def __init__(self, core, results_dir: Optional[Path] = None):
        """
        Inicializa o gerenciador de histórico.
        
        Args:
            core: Instância do SystemCore
            results_dir: Diretório de resultados (padrão: data/results)
        """
        super().__init__(core)
        self.results_dir = Path(results_dir) if results_dir else Path("data/results")
        self.loaded_history: List[Dict] = []
        self._log("info", f"Inicializado com diretório: {self.results_dir}")
    
    def initialize(self) -> bool:
        """
        Inicializa o manager.
        
        Carrega histórico na startup.
        """
        try:
            self.load_history()
            return True
        except Exception as e:
            self._log("error", f"Falha ao inicializar: {e}")
            return False
    
    def cleanup(self) -> None:
        """Limpa recursos do manager"""
        self.loaded_history.clear()
        self._log("info", "Limpeza completa")
    
    def load_history(self) -> List[Dict]:
        """
        Carrega histórico de inspeções do disco.
        
        Procura por pastas com padrão YYYYMMDD_HHMMSS em results_dir
        e carrega arquivo inspection_data.json de cada uma.
        
        Returns:
            Lista de dicts com metadados de cada inspeção
        
        Exemplo de retorno:
            [
                {
                    "timestamp": "20260122_093000",
                    "inspection_type": "segmentation",
                    "model_name": "fruta",
                    "path": "/data/results/20260122_093000",
                    "data": {"class": "banana", "confidence": 0.95}
                },
                ...
            ]
        """
        try:
            self.loaded_history.clear()
            
            if not self.results_dir.exists():
                self._log("warning", f"Diretório não existe: {self.results_dir}")
                return []
            
            history = []
            
            # Procura todas as pastas com padrão YYYYMMDD_HHMMSS
            for result_dir in sorted(self.results_dir.iterdir(), reverse=True):
                if not result_dir.is_dir():
                    continue
                
                inspection_file = result_dir / "inspection_data.json"
                if inspection_file.exists():
                    try:
                        with open(inspection_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        history.append({
                            "timestamp": data.get("timestamp"),
                            "inspection_type": data.get("inspection_type"),
                            "model_name": data.get("model_name"),
                            "path": str(result_dir),
                            "data": data.get("results", {}),
                        })
                    except Exception as e:
                        self._log("warning", f"Falha ao carregar {inspection_file}: {e}")
            
            self.loaded_history = history
            self._notify("history_loaded", {"count": len(history)})
            self._log("info", f"Histórico carregado: {len(history)} inspeções")
            
            return history
        
        except Exception as e:
            self._log("error", f"Erro ao carregar histórico: {e}")
            self._notify("history_error", {"error": str(e)})
            return []
    
    def get_history_item(self, index: int) -> Optional[Dict]:
        """
        Retorna item específico do histórico carregado.
        
        Args:
            index: Índice na lista (0-based)
        
        Returns:
            Dict com dados da inspeção ou None se índice inválido
        
        Exemplo:
            item = manager.get_history_item(0)
            if item:
                print(f"Tipo: {item['inspection_type']}")
        """
        if 0 <= index < len(self.loaded_history):
            return self.loaded_history[index]
        return None
    
    def get_history_by_timestamp(self, timestamp: str) -> Optional[Dict]:
        """
        Retorna item do histórico por timestamp.
        
        Args:
            timestamp: Timestamp no formato YYYYMMDD_HHMMSS
        
        Returns:
            Dict com dados da inspeção ou None se não encontrado
        
        Exemplo:
            item = manager.get_history_by_timestamp("20260122_093000")
        """
        for item in self.loaded_history:
            if item["timestamp"] == timestamp:
                return item
        return None
    
    def get_history_count(self) -> int:
        """
        Retorna número total de inspeções no histórico.
        
        Returns:
            int: Quantidade de inspeções carregadas
        """
        return len(self.loaded_history)
    
    def view_history_item(self, item_index: int) -> Optional[str]:
        """
        Formata item do histórico para visualização (string).
        
        Args:
            item_index: Índice na lista
        
        Returns:
            String formatada com informações da inspeção, ou None
        
        Exemplo:
            display = manager.view_history_item(0)
            if display:
                print(display)
        """
        item = self.get_history_item(item_index)
        if not item:
            return None
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"Data/Hora: {item.get('timestamp', 'N/A')}")
        lines.append(f"Tipo: {item.get('inspection_type', 'N/A').upper()}")
        lines.append(f"Modelo: {item.get('model_name', 'N/A')}")
        lines.append("=" * 60)
        
        results = item.get("data", {})
        
        if item.get("inspection_type") == "segmentation":
            lines.append(f"Classe: {results.get('class', 'N/A')}")
            lines.append(f"Confiança: {results.get('confidence', 0):.2%}")
            lines.append(f"Área: {results.get('area', 'N/A')}")
        
        elif item.get("inspection_type") == "classification":
            lines.append(f"Classe Predita: {results.get('predicted_class', 'N/A')}")
            lines.append(f"Confiança: {results.get('confidence', 0):.2%}")
            
            if "class_confidences" in results:
                lines.append("\nConfiança por classe:")
                for cls, conf in results["class_confidences"].items():
                    lines.append(f"  - {cls}: {conf:.2%}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def export_to_csv(self, output_path: Path) -> bool:
        """
        Exporta histórico para arquivo CSV.
        
        Args:
            output_path: Path do arquivo CSV a criar
        
        Returns:
            True se sucesso, False se erro
        
        Colunas do CSV:
            - Timestamp
            - Tipo (segmentation/classification)
            - Modelo
            - Resultado (classe detectada)
            - Confiança (percentual)
        
        Exemplo:
            success = manager.export_to_csv(Path("historico.csv"))
        """
        try:
            if not self.loaded_history:
                self._log("warning", "Histórico vazio para exportar")
                return False
            
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    "Timestamp",
                    "Tipo",
                    "Modelo",
                    "Resultado",
                    "Confiança"
                ])
                
                # Dados
                for item in self.loaded_history:
                    timestamp = item.get("timestamp", "")
                    inspection_type = item.get("inspection_type", "")
                    model_name = item.get("model_name", "")
                    data = item.get("data", {})
                    
                    # Resultado varia por tipo
                    if inspection_type == "segmentation":
                        resultado = data.get("class", "N/A")
                    else:
                        resultado = data.get("predicted_class", "N/A")
                    
                    confianca = f"{data.get('confidence', 0):.2%}"
                    
                    writer.writerow([
                        timestamp,
                        inspection_type,
                        model_name,
                        resultado,
                        confianca
                    ])
            
            self._log("info", f"Histórico exportado para: {output_path}")
            self._notify("history_exported", {"path": str(output_path)})
            return True
        
        except Exception as e:
            self._log("error", f"Erro ao exportar CSV: {e}")
            self._notify("history_error", {"error": str(e)})
            return False
    
    def delete_history_item(self, timestamp: str) -> bool:
        """
        Deleta item específico do histórico.
        
        Remove tanto do disco quanto da memória.
        
        Args:
            timestamp: Timestamp do item a deletar (formato YYYYMMDD_HHMMSS)
        
        Returns:
            True se sucesso, False se erro
        
        Exemplo:
            success = manager.delete_history_item("20260122_093000")
        """
        try:
            result_dir = self.results_dir / timestamp
            if result_dir.exists():
                shutil.rmtree(result_dir)
                self._log("info", f"Deletado diretório: {result_dir}")
            
            # Remove da lista
            original_count = len(self.loaded_history)
            self.loaded_history = [
                item for item in self.loaded_history
                if item["timestamp"] != timestamp
            ]
            
            deleted = original_count - len(self.loaded_history)
            if deleted > 0:
                self._notify("history_modified", {"deleted": deleted})
                self._log("info", f"Item {timestamp} removido do histórico")
                return True
            
            return False
        
        except Exception as e:
            self._log("error", f"Erro ao deletar histórico: {e}")
            self._notify("history_error", {"error": str(e)})
            return False
    
    def clear_all_history(self) -> bool:
        """
        Deleta TODO o histórico (disco e memória).
        
        ⚠️ OPERAÇÃO IRREVERSÍVEL
        
        Returns:
            True se sucesso, False se erro
        
        Exemplo:
            success = manager.clear_all_history()
        """
        try:
            if self.results_dir.exists():
                shutil.rmtree(self.results_dir)
                self._log("warning", "Histórico completamente deletado do disco")
            
            self.results_dir.mkdir(parents=True, exist_ok=True)
            self.loaded_history.clear()
            
            self._notify("history_modified", {"cleared": True})
            self._log("warning", "Todo o histórico foi limpo")
            return True
        
        except Exception as e:
            self._log("error", f"Erro ao limpar histórico: {e}")
            self._notify("history_error", {"error": str(e)})
            return False
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas agregadas sobre o histórico.
        
        Returns:
            Dict com:
            - total: Quantidade total de inspeções
            - segmentation: Quantidade de segmentações
            - classification: Quantidade de classificações
            - models: Dict com contagem por modelo
        
        Exemplo:
            stats = manager.get_summary_stats()
            print(f"Total: {stats['total']}")
            print(f"Modelos: {stats['models']}")
        """
        if not self.loaded_history:
            return {"total": 0, "segmentation": 0, "classification": 0, "models": {}}
        
        segmentation_count = sum(
            1 for item in self.loaded_history
            if item.get("inspection_type") == "segmentation"
        )
        classification_count = sum(
            1 for item in self.loaded_history
            if item.get("inspection_type") == "classification"
        )
        
        # Conta por modelo
        models = {}
        for item in self.loaded_history:
            model = item.get("model_name", "Unknown")
            models[model] = models.get(model, 0) + 1
        
        return {
            "total": len(self.loaded_history),
            "segmentation": segmentation_count,
            "classification": classification_count,
            "models": models,
        }
