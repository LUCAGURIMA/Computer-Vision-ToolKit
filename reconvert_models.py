#!/usr/bin/env python
"""
Script para reconverter modelos YOLO antigos para o formato 8.0.0
"""
import torch

# Monkeypatch para torch.load (PyTorch 2.6+)
_original_torch_load = torch.load
def _patched_torch_load(f, *args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(f, *args, **kwargs)
torch.load = _patched_torch_load

from ultralytics import YOLO
from pathlib import Path

models = {
    'models/segmentation_best.pt': 'segmentation',
    'models/classification_best.pt': 'classification',
}

for model_path, model_type in models.items():
    if not Path(model_path).exists():
        print(f"❌ {model_path} não encontrado")
        continue
    
    try:
        print(f"🔄 Reconvertendo {model_type}...")
        model = YOLO(model_path)
        print(f"  Carregado: {model.task if hasattr(model, 'task') else 'desconhecido'}")
        
        # Salva no novo formato
        model.save(model_path)
        print(f"✅ {model_type} reconvertido com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao reconverter {model_type}: {e}")

print("\n✅ Processo concluído!")
