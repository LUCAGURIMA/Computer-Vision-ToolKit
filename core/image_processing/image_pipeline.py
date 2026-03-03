from typing import List, Dict, Any, Tuple
import numpy as np
import cv2

class ImagePipeline:

    def __init__(self, config: Dict[str, Any]=None):
        self.config = config or {}

    def crop(self, image: np.ndarray, bbox: List[int]) -> np.ndarray:
        x1, y1, x2, y2 = map(int, bbox)
        h, w = image.shape[:2]
        x1 = max(0, min(w - 1, x1))
        x2 = max(0, min(w, x2))
        y1 = max(0, min(h - 1, y1))
        y2 = max(0, min(h, y2))
        if x2 <= x1 or y2 <= y1:
            return image
        return image[y1:y2, x1:x2]

    def resize(self, image: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
        h, w = size
        return cv2.resize(image, (w, h))

    def normalize(self, image: np.ndarray) -> np.ndarray:
        return image.astype('float32') / 255.0

    def apply(self, image: np.ndarray, ops: List[Dict[str, Any]]) -> np.ndarray:
        out = image
        for op in ops or []:
            name = op.get('name')
            if name == 'crop':
                out = self.crop(out, op.get('bbox', [0, 0, out.shape[1], out.shape[0]]))
            elif name == 'resize':
                out = self.resize(out, tuple(op.get('size', (out.shape[0], out.shape[1]))))
            elif name == 'normalize':
                out = self.normalize(out)
        return out