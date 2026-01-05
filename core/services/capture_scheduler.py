"""
Serviço de captura periódica em thread separada.

`CaptureScheduler` usa um `camera_manager` (instância de CameraManager) para
capturar imagens periodicamente e salvá-las em `save_dir`.

Callbacks: recebe `on_saved` opcional para notificar quando um arquivo é gravado.
"""
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np


class CaptureScheduler:
    def __init__(self, camera_manager, save_dir: Path, on_saved: Optional[Callable] = None, preprocess_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None):
        self.camera_manager = camera_manager
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.on_saved = on_saved
        # Função opcional que recebe imagem (np.ndarray) e deve retornar imagem processada
        self.preprocess_fn = preprocess_fn

        self._stop_event = threading.Event()
        self._thread = None

    def _loop(self, interval: float):
        idx = 0
        while not self._stop_event.wait(interval):
            try:
                img = self.camera_manager.capture()
                if img is None:
                    continue
                # Aplica pré-processamento se fornecido
                if self.preprocess_fn:
                    try:
                        img = self.preprocess_fn(img)
                    except Exception:
                        # Se pré-processamento falhar, pula esta captura
                        continue
                fname = self.save_dir / f"capture_{int(time.time())}_{idx}.jpg"
                cv2.imwrite(str(fname), img)
                idx += 1
                if self.on_saved:
                    try:
                        self.on_saved({"path": str(fname), "timestamp": time.time()})
                    except Exception:
                        pass
            except Exception:
                # Não deixamos a thread morrer por erro transitório
                continue

    def start(self, interval: float):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
