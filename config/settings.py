import os
from pathlib import Path
from typing import Dict, Any
import json
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / 'models'
LOGS_DIR = BASE_DIR / 'logs'
DATA_DIR = BASE_DIR / 'data'
ASSETS_DIR = BASE_DIR / 'assets'
for directory in [MODELS_DIR, LOGS_DIR, DATA_DIR, ASSETS_DIR]:
    directory.mkdir(exist_ok=True)
CAMERA_CONFIG = {'primary': {'type': 'basler', 'ip': None, 'max_retries': 3, 'timeout': 5000}, 'fallbacks': [{'type': 'webcam', 'index': 0, 'resolution': (1280, 720)}, {'type': 'mock', 'image_path': str(ASSETS_DIR / 'fallback_image.jpg')}]}
MODELS_CONFIG = {'segmentation': {'default_model': 'fruta', 'dir': str(MODELS_DIR / 'segmentation'), 'confidence_threshold': 0.45, 'iou_threshold': 0.8, 'image_size': 1280}, 'classification': {'default_model': 'fruta', 'dir': str(MODELS_DIR / 'classification'), 'confidence_threshold': 0.7, 'image_size': 640}}

def get_available_models(model_type: str):
    model_dir = Path(MODELS_CONFIG.get(model_type, {}).get('dir', ''))
    if not model_dir.exists():
        return []
    models = sorted([f.stem for f in model_dir.glob('*.pt')])
    return models

def get_model_path(model_type: str, model_name: str=None) -> str:
    config = MODELS_CONFIG.get(model_type, {})
    model_dir = Path(config.get('dir', ''))
    if model_name is None:
        model_name = config.get('default_model', 'fruta')
    return str(model_dir / f'{model_name}.pt')
WEB_CONFIG = {'host': '0.0.0.0', 'port': 8000, 'reload': True, 'workers': 1, 'cors_origins': ['*']}
DESKTOP_CONFIG = {'window_title': 'Sistema de Inspeção', 'window_size': (1024, 768), 'theme': 'dark', 'auto_detect_network': True, 'show_system_tray': True, 'stream_in_popup': True}
LOGGING_CONFIG = {'level': 'INFO', 'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}', 'rotation': '10 MB', 'retention': '30 days'}
SYSTEM_CONFIG = {'mode': 'auto', 'auto_open_browser': True, 'save_results': True, 'results_dir': str(DATA_DIR / 'results'), 'max_history': 100}

def save_config():
    config_dict = {'camera': CAMERA_CONFIG, 'models': MODELS_CONFIG, 'web': WEB_CONFIG, 'desktop': DESKTOP_CONFIG, 'system': SYSTEM_CONFIG}
    config_file = BASE_DIR / 'config.json'
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)
    print(f'Configuração salva em: {config_file}')

def load_config():
    config_file = BASE_DIR / 'config.json'
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
if __name__ == '__main__':
    save_config()
    print('✅ Configuração inicial criada com sucesso!')
    print(f'📁 Models dir: {MODELS_DIR}')
    print(f'📁 Logs dir: {LOGS_DIR}')