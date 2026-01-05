"""
Image preprocessing pipeline utilities.

Classe `ImagePipeline` com operações reutilizáveis: crop, resize, normalize e um
método `apply` que recebe uma lista de operações para compor um pipeline.

As operações são dicts simples, ex:
  {"name": "crop", "bbox": [x1, y1, x2, y2]}
  {"name": "resize", "size": [height, width]}
  {"name": "normalize"}

Esta classe é intencionalmente pequena e sem estado para facilitar testes.
"""
from typing import List, Dict, Any, Tuple
import numpy as np
import cv2


class ImagePipeline:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def crop(self, image: np.ndarray, bbox: List[int]) -> np.ndarray:
        """Recorta a imagem pela bbox [x1, y1, x2, y2].

        Exemplo de uso:
            out = pipeline.crop(img, [100, 50, 400, 300])
        """
        x1, y1, x2, y2 = map(int, bbox)
        # Proteções mínimas
        h, w = image.shape[:2]
        x1 = max(0, min(w - 1, x1))
        x2 = max(0, min(w, x2))
        y1 = max(0, min(h - 1, y1))
        y2 = max(0, min(h, y2))
        if x2 <= x1 or y2 <= y1:
            return image  # bbox inválida -> retorna original
        return image[y1:y2, x1:x2]

    def resize(self, image: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
        """Redimensiona para (height, width).

        Exemplo:
            out = pipeline.resize(img, (512, 512))
        """
        h, w = size
        return cv2.resize(image, (w, h))

    def normalize(self, image: np.ndarray) -> np.ndarray:
        """Normaliza pixels para float32 em [0,1]."""
        return image.astype("float32") / 255.0

    def apply(self, image: np.ndarray, ops: List[Dict[str, Any]]) -> np.ndarray:
        """Aplica uma sequência de operações sobre a imagem.

        ops é uma lista de dicionários onde cada dicionário deve ter a chave
        "name". Exemplo:
            ops = [
                {"name": "crop", "bbox": [100,50,400,300]},
                {"name": "resize", "size": [256,256]},
                {"name": "normalize"}
            ]
        """
        out = image
        for op in ops or []:
            name = op.get("name")
            if name == "crop":
                out = self.crop(out, op.get("bbox", [0, 0, out.shape[1], out.shape[0]]))
            elif name == "resize":
                out = self.resize(out, tuple(op.get("size", (out.shape[0], out.shape[1]))))
            elif name == "normalize":
                out = self.normalize(out)
            # futuras operações podem ser adicionadas aqui
        return out
