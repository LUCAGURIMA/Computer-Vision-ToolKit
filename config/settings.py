"""
Arquivo de configuração central do sistema.
Define todos os parâmetros ajustáveis em um só lugar.
"""

import os
from pathlib import Path
from typing import Dict, Any
import json

# ============================================
# CONFIGURAÇÕES DE CAMINHOS
# ============================================
BASE_DIR = Path(__file__).parent.parent

# Diretórios principais
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

# Cria diretórios se não existirem
for directory in [MODELS_DIR, LOGS_DIR, DATA_DIR, ASSETS_DIR]:
    directory.mkdir(exist_ok=True)

# ============================================
# CONFIGURAÇÕES DA CÂMERA
# ============================================
CAMERA_CONFIG = {
    "fallbacks": [
        {
            "type": "webcam",
            "index": 0,             # índice da webcam
            "resolution": (1280, 720)
        },
        {
            "type": "mock",
            "image_path": str(ASSETS_DIR / "fallback_image.jpg")
        }
    ]
}

# ============================================
# CONFIGURAÇÕES DOS MODELOS ML
# ============================================
# Suporta múltiplos modelos por tipo em pastas
# Estrutura: models/segmentation/modelo.pt, models/classification/modelo.pt
MODELS_CONFIG = {
    "segmentation": {
        "default_model": "fruta",  # nome do modelo sem .pt
        "dir": str(MODELS_DIR / "segmentation"),
        "confidence_threshold": 0.45,
        "iou_threshold": 0.8,
        "image_size": 1280
    },
    "classification": {
        "default_model": "fruta",  # nome do modelo sem .pt
        "dir": str(MODELS_DIR / "classification"),
        "confidence_threshold": 0.7,  # Se < 0.7 = INDETERMINADO
        "image_size": 640
    }
}

def get_available_models(model_type: str):
    """
    Lista modelos disponíveis para um tipo específico.
    
    Args:
        model_type (str): "segmentation" ou "classification"
        
    Returns:
        list: Lista de nomes de modelos (sem .pt)
    """
    model_dir = Path(MODELS_CONFIG.get(model_type, {}).get("dir", ""))
    if not model_dir.exists():
        return []
    
    # Lista arquivos .pt e remove extensão
    models = sorted([f.stem for f in model_dir.glob("*.pt")])
    return models

def get_model_path(model_type: str, model_name: str = None) -> str:
    """
    Obtém caminho completo do modelo.
    
    Args:
        model_type (str): "segmentation" ou "classification"
        model_name (str): Nome do modelo sem .pt (usa default se None)
        
    Returns:
        str: Caminho completo do arquivo .pt
    """
    config = MODELS_CONFIG.get(model_type, {})
    model_dir = Path(config.get("dir", ""))
    
    if model_name is None:
        model_name = config.get("default_model", "fruta")
    
    return str(model_dir / f"{model_name}.pt")

# ============================================
# CONFIGURAÇÕES DO SERVIDOR WEB
# ============================================
WEB_CONFIG = {
    "host": "0.0.0.0",      # Acessível de qualquer lugar na rede
    "port": 8000,
    "reload": True,         # Recarrega automaticamente ao mudar código
    "workers": 1,           # 1 worker é suficiente para uso local
    "cors_origins": ["*"]   # Permite qualquer origem (ajuste para produção)
}

# ============================================
# CONFIGURAÇÕES DA INTERFACE DESKTOP
# ============================================
DESKTOP_CONFIG = {
    "window_title": "Sistema de Inspeção",
    "window_size": (1024, 768),
    "theme": "dark",        # dark, light, auto
    "auto_detect_network": True,
    "show_system_tray": True
}

# ============================================
# CONFIGURAÇÕES DE LOG
# ============================================
LOGGING_CONFIG = {
    "level": "INFO",        # DEBUG, INFO, WARNING, ERROR
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    "rotation": "10 MB",    # Rotaciona log a cada 10MB
    "retention": "30 days"  # Mantém logs por 30 dias
}

# ============================================
# CONFIGURAÇÕES DE SISTEMA
# ============================================
SYSTEM_CONFIG = {
    "mode": "auto",         # auto, web, desktop, both
    "auto_open_browser": True,
    "save_results": True,
    "results_dir": str(DATA_DIR / "results"),
    "max_history": 100      # Máximo de inspeções salvas
}

def save_config():
    """Salva configuração em JSON para fácil edição"""
    config_dict = {
        "camera": CAMERA_CONFIG,
        "models": MODELS_CONFIG,
        "web": WEB_CONFIG,
        "desktop": DESKTOP_CONFIG,
        "system": SYSTEM_CONFIG
    }
    
    config_file = BASE_DIR / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    print(f"Configuração salva em: {config_file}")

def load_config():
    """Carrega configuração de arquivo JSON"""
    config_file = BASE_DIR / "config.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# ============================================
# UTILITÁRIOS
# ============================================

# Teste rápido
if __name__ == "__main__":
    save_config()
    print("✅ Configuração inicial criada com sucesso!")
    print(f"📁 Models dir: {MODELS_DIR}")
    print(f"📁 Logs dir: {LOGS_DIR}")