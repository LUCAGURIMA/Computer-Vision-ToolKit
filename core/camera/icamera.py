from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any
import numpy as np

class ICamera(ABC):

    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def capture(self) -> Optional[np.ndarray]:
        pass

    @abstractmethod
    def release(self):
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    def get_parameters(self) -> Dict[str, Any]:
        return {}

    def set_parameter(self, param_name: str, value: Any) -> bool:
        return False