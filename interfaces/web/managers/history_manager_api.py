"""
HistoryManager API - Adapter REST para HistoryManager do core.

Adapta manager core para endpoints FastAPI.

Tipo: Adapter Pattern
"""

from typing import Dict, Any, List
from pathlib import Path

from core.managers import HistoryManager as CoreHistoryManager


class HistoryManagerAPI:
    """
    Adapter para HistoryManager em FastAPI.
    
    Converte resultados do core para JSON e vice-versa.
    
    Design:
    - Usa composition (não herança)
    - Cria uma instância do manager core
    - Traduz para/de JSON
    - Trata erros HTTP
    """
    
    def __init__(self, core, results_dir: str = None):
        """
        Inicializa o adapter API.
        
        Args:
            core: Instância do SystemCore
            results_dir: Diretório de resultados (padrão: data/results)
        """
        results_path = Path(results_dir) if results_dir else None
        self.manager = CoreHistoryManager(core, results_path)
    
    # Métodos de ciclo de vida
    
    def initialize(self) -> bool:
        """Inicializa o manager"""
        return self.manager.initialize()
    
    def cleanup(self) -> None:
        """Limpa recursos"""
        self.manager.cleanup()
    
    # Métodos API
    
    async def get_all_history(self) -> Dict[str, Any]:
        """
        Retorna histórico completo.
        
        Endpoint: GET /api/history
        
        Returns:
            {
                "success": bool,
                "count": int,
                "data": [inspeção, ...]
            }
        """
        try:
            self.manager.load_history()
            return {
                "success": True,
                "count": self.manager.get_history_count(),
                "data": self.manager.loaded_history
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_history_item(self, index: int) -> Dict[str, Any]:
        """
        Retorna item específico.
        
        Endpoint: GET /api/history/{index}
        
        Args:
            index: Índice na lista (0-based)
        
        Returns:
            {
                "success": bool,
                "data": {inspeção} ou null
            }
        """
        try:
            item = self.manager.get_history_item(index)
            if item:
                return {
                    "success": True,
                    "data": item
                }
            else:
                return {
                    "success": False,
                    "error": f"Item {index} não encontrado"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_history_by_timestamp(self, timestamp: str) -> Dict[str, Any]:
        """
        Retorna item por timestamp.
        
        Endpoint: GET /api/history/timestamp/{timestamp}
        
        Args:
            timestamp: Timestamp (YYYYMMDD_HHMMSS)
        
        Returns:
            {
                "success": bool,
                "data": {inspeção} ou null
            }
        """
        try:
            item = self.manager.get_history_by_timestamp(timestamp)
            if item:
                return {
                    "success": True,
                    "data": item
                }
            else:
                return {
                    "success": False,
                    "error": f"Timestamp {timestamp} não encontrado"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_history_count(self) -> Dict[str, Any]:
        """
        Retorna contagem de inspeções.
        
        Endpoint: GET /api/history/count
        
        Returns:
            {
                "success": bool,
                "count": int
            }
        """
        try:
            count = self.manager.get_history_count()
            return {
                "success": True,
                "count": count
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_summary_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas.
        
        Endpoint: GET /api/history/stats
        
        Returns:
            {
                "success": bool,
                "stats": {
                    "total": int,
                    "segmentation": int,
                    "classification": int,
                    "models": {model: count, ...}
                }
            }
        """
        try:
            stats = self.manager.get_summary_stats()
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def view_history_item(self, index: int) -> Dict[str, Any]:
        """
        Retorna item formatado para visualização.
        
        Endpoint: GET /api/history/{index}/view
        
        Args:
            index: Índice na lista
        
        Returns:
            {
                "success": bool,
                "formatted": str ou null
            }
        """
        try:
            view = self.manager.view_history_item(index)
            if view:
                return {
                    "success": True,
                    "formatted": view
                }
            else:
                return {
                    "success": False,
                    "error": f"Item {index} não encontrado"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def export_to_csv(self, output_filename: str) -> Dict[str, Any]:
        """
        Exporta histórico para CSV.
        
        Endpoint: POST /api/history/export
        
        Args:
            output_filename: Nome do arquivo (salvo em data/results/)
        
        Returns:
            {
                "success": bool,
                "path": str ou error
            }
        """
        try:
            output_path = Path("data") / "exports" / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            success = self.manager.export_to_csv(output_path)
            if success:
                return {
                    "success": True,
                    "path": str(output_path),
                    "filename": output_filename
                }
            else:
                return {
                    "success": False,
                    "error": "Histórico vazio para exportar"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_history_item(self, timestamp: str) -> Dict[str, Any]:
        """
        Deleta item do histórico.
        
        Endpoint: DELETE /api/history/{timestamp}
        
        Args:
            timestamp: Timestamp do item
        
        Returns:
            {
                "success": bool,
                "deleted": str ou error
            }
        """
        try:
            success = self.manager.delete_history_item(timestamp)
            if success:
                return {
                    "success": True,
                    "deleted": timestamp
                }
            else:
                return {
                    "success": False,
                    "error": f"Item {timestamp} não encontrado"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def clear_all_history(self) -> Dict[str, Any]:
        """
        Deleta TODO o histórico.
        
        ⚠️ OPERAÇÃO IRREVERSÍVEL
        
        Endpoint: DELETE /api/history (com header especial)
        
        Returns:
            {
                "success": bool,
                "message": "Histórico limpo" ou error
            }
        """
        try:
            success = self.manager.clear_all_history()
            if success:
                return {
                    "success": True,
                    "message": "Todo o histórico foi permanentemente deletado"
                }
            else:
                return {
                    "success": False,
                    "error": "Falha ao limpar histórico"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
