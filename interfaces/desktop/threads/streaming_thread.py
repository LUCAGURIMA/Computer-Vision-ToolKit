"""Streaming thread for continuous frame capture."""

import time
from typing import TYPE_CHECKING
from PyQt5.QtCore import QThread, pyqtSignal
from core.utils.logger import log

if TYPE_CHECKING:
    from core.system_core import SystemCore


class StreamingThread(QThread):
    """Thread for continuous streaming at target FPS.
    
    Signals:
        frame_ready: Emitted when a new frame is captured
        error_occurred: Emitted when an error occurs
        fps_info: Emitted periodically with current FPS information
    """
    
    frame_ready = pyqtSignal(object)  # np.ndarray
    error_occurred = pyqtSignal(str)
    fps_info = pyqtSignal(float)

    def __init__(self, core: 'SystemCore', target_fps: int = 30):
        """Initialize streaming thread.
        
        Args:
            core: SystemCore instance for image capture
            target_fps: Target frames per second (default: 30)
        """
        super().__init__()
        self.core = core
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.running = True
        self.frame_count = 0
        self.start_time = time.time()
        self._logger_name = self.__class__.__name__

    def run(self):
        """Execute streaming loop in thread."""
        try:
            while self.running:
                loop_start = time.time()
                try:
                    result = self.core.capture_image()
                    if result and result.get('success'):
                        frame = result.get('image')
                        if frame is not None:
                            self.frame_ready.emit(frame)
                            self.frame_count += 1
                except Exception as e:
                    log.debug(f'[{self._logger_name}] Error capturing frame: {e}')
                    continue
                    
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
                if self.frame_count % 30 == 0:
                    current_fps = 30 / (time.time() - self.start_time + 0.001)
                    self.fps_info.emit(current_fps)
                    self.frame_count = 0
                    self.start_time = time.time()
        except Exception as e:
            log.error(f'[{self._logger_name}] Exception in streaming loop: {e}', exc_info=True)
            self.error_occurred.emit(str(e))

    def stop(self):
        """Stop streaming and wait for thread completion."""
        self.running = False
        self.wait()
