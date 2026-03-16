"""Image conversion utilities for Qt display."""

from typing import Tuple
import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap


class ImageConverter:
    """Utility class for converting images between NumPy and Qt formats."""

    @staticmethod
    def numpy_to_qimage(image: np.ndarray) -> QImage:
        """Convert numpy array to QImage.
        
        Args:
            image: NumPy image array (BGR or grayscale)
            
        Returns:
            QImage object ready for display
        """
        if len(image.shape) == 3 and image.shape[2] == 3:
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = image_rgb.shape
            bytes_per_line = ch * w
            return QImage(
                image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888
            )
        else:
            # Grayscale image
            h, w = image.shape[:2]
            bytes_per_line = w
            return QImage(
                image.data, w, h, bytes_per_line, QImage.Format_Grayscale8
            )

    @staticmethod
    def numpy_to_pixmap(image: np.ndarray) -> QPixmap:
        """Convert numpy array to QPixmap.
        
        Args:
            image: NumPy image array
            
        Returns:
            QPixmap object ready for display
        """
        qimage = ImageConverter.numpy_to_qimage(image)
        return QPixmap.fromImage(qimage)

    @staticmethod
    def get_image_shape(image: np.ndarray) -> Tuple[int, int]:
        """Get image dimensions (height, width).
        
        Args:
            image: NumPy image array
            
        Returns:
            Tuple of (height, width)
        """
        if len(image.shape) >= 2:
            return image.shape[0], image.shape[1]
        return 0, 0
