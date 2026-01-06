"""
Módulo de configuração - expõe as configurações
"""
from .settings import (
    BASE_DIR, MODELS_DIR, LOGS_DIR, DATA_DIR, ASSETS_DIR,
    CAMERA_CONFIG, MODELS_CONFIG, WEB_CONFIG, DESKTOP_CONFIG,
    SYSTEM_CONFIG, LOGGING_CONFIG, get_model_path, get_available_models, save_config, load_config
)

__all__ = [
    'BASE_DIR', 'MODELS_DIR', 'LOGS_DIR', 'DATA_DIR', 'ASSETS_DIR',
    'CAMERA_CONFIG', 'MODELS_CONFIG', 'WEB_CONFIG', 'DESKTOP_CONFIG',
    'SYSTEM_CONFIG', 'LOGGING_CONFIG', 'get_model_path', 'get_available_models', 'save_config', 'load_config'
]