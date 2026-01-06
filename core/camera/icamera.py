"""
Interface (contrato) para todas as câmeras do sistema.

POR QUE USAR INTERFACE?
1. Qualquer câmera que implemente esta interface funcionará no sistema
2. Fácil trocar câmera sem mudar o resto do código
3. Podemos ter múltiplas implementações (Basler, Webcam, Mock, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any
import numpy as np

class ICamera(ABC):
    """
    Interface que define o CONTRATO que toda câmera deve seguir.
    É como um "contrato de trabalho" - se cumprir esses métodos, pode trabalhar aqui.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Inicializa a câmera.
        
        Returns:
            bool: True se inicializou com sucesso, False caso contrário
        """
        pass
    
    @abstractmethod
    def capture(self) -> Optional[np.ndarray]:
        """
        Captura uma imagem.
        
        Returns:
            Optional[np.ndarray]: Imagem como array numpy, ou None se falhou
        """
        pass
    
    @abstractmethod
    def release(self):
        """
        Libera recursos da câmera.
        Deve ser chamado quando não for mais usar a câmera.
        """
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre a câmera.
        
        Returns:
            Dict[str, Any]: Dicionário com informações da câmera
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica se a câmera está disponível.
        
        Returns:
            bool: True se disponível, False se não
        """
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Retorna parâmetros ajustáveis da câmera.
        
        Returns:
            Dict[str, Any]: Dicionário de parâmetros
                {
                    "param_name": {
                        "value": valor_atual,
                        "type": "int|float|bool|enum",
                        "label": "Nome amigável",
                        "min": valor_min (opcional),
                        "max": valor_max (opcional),
                        "step": incremento (opcional),
                        "options": [lista de opções] (opcional, para enum),
                        "description": "Descrição do parâmetro"
                    },
                    ...
                }
        """
        return {}  # Padrão: sem parâmetros ajustáveis
    
    def set_parameter(self, param_name: str, value: Any) -> bool:
        """
        Define um parâmetro da câmera.
        
        Args:
            param_name (str): Nome do parâmetro
            value (Any): Novo valor
            
        Returns:
            bool: True se conseguiu ajustar, False caso contrário
        """
        return False  # Padrão: não suporta ajuste