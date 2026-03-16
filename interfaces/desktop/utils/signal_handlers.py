"""Signal handling utilities for desktop interface."""

from typing import Callable, Dict, Any


class SignalHandlers:
    """Utility class for managing signal handlers and callbacks."""

    @staticmethod
    def safe_connect(signal, slot: Callable, error_callback: Callable = None):
        """Safely connect signal to slot with error handling.
        
        Args:
            signal: PyQt signal to connect
            slot: Target slot function
            error_callback: Optional callback for connection errors
        """
        try:
            signal.connect(slot)
        except Exception as e:
            if error_callback:
                error_callback(str(e))
            raise

    @staticmethod
    def emit_safe(signal, *args, error_callback: Callable = None):
        """Safely emit signal with error handling.
        
        Args:
            signal: PyQt signal to emit
            *args: Signal arguments
            error_callback: Optional callback for emission errors
        """
        try:
            signal.emit(*args)
        except Exception as e:
            if error_callback:
                error_callback(str(e))
            raise
