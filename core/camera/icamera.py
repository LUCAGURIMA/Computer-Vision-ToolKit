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