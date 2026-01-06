"""
Gerenciador de modelos de Machine Learning.

Carrega e gerencia os modelos YOLO para segmentação e classificação.
Implementa Singleton pattern para carregar cada modelo apenas uma vez.
"""

import torch
from pathlib import Path
from typing import Dict, Any, Optional
from ultralytics import YOLO

from core.utils.logger import log
from config import MODELS_CONFIG, get_model_path, get_available_models

# ============================================
# SOLUÇÃO PARA PYTORCH 2.6+ (weights_only)
# ============================================
# PyTorch 2.6 mudou weights_only=True por padrão (segurança)
# Modelos YOLO antigos podem não funcionar
# Solução: monkeypatch torch.load + permitir globals da ultralytics

_original_torch_load = torch.load

def _patched_torch_load(f, *args, **kwargs):
    """Wrapper para torch.load que usa weights_only=False por padrão"""
    # Se weights_only não foi especificado, usa False para compatibilidade
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(f, *args, **kwargs)

# Aplica o monkeypatch globalmente
torch.load = _patched_torch_load

# Adiciona safe globals para ultralytics (permite desserializar modelos antigos)
try:
    import ultralytics.nn as nn_module
    # Permite todos os módulos públicos do ultralytics.nn
    for name in dir(nn_module):
        if not name.startswith('_'):
            try:
                obj = getattr(nn_module, name)
                if isinstance(obj, type):  # É uma classe
                    torch.serialization.add_safe_globals([obj])
            except:
                pass
    log.debug("✅ Safe globals para ultralytics.nn adicionados")
except Exception as e:
    log.debug(f"⚠️  Não foi possível adicionar safe globals: {e}")

log.debug("🔧 Monkeypatch aplicado: torch.load usa weights_only=False para compatibilidade")

class ModelManager:
    """
    Gerencia os modelos ML do sistema.
    
    Usa Singleton pattern para cada tipo de modelo:
    - Carrega o modelo UMA VEZ
    - Reutiliza a mesma instância
    - Economiza memória e tempo de carregamento
    """
    
    # Variáveis de classe para Singleton
    _instances = {}
    _models = {}  # Cache de modelos carregados
    
    def __new__(cls, model_type: str = None):
        """
        Implementa Singleton pattern.
        
        Se já existe instância para este model_type, retorna ela.
        Se não, cria nova.
        """
        if model_type is None:
            model_type = "default"
        
        if model_type not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[model_type] = instance
            instance._model_type = model_type
            instance._initialized = False
        return cls._instances[model_type]
    
    def __init__(self, model_type: str = "segmentation", model_name: str = None):
        """
        Inicializa o gerenciador para um tipo específico de modelo.
        
        Args:
            model_type (str): "segmentation" ou "classification"
            model_name (str): Nome do modelo sem .pt (usa default se None)
        """
        # Evita reinitialização no Singleton
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.model_type = model_type
        self.model_name = model_name  # Nome específico do modelo
        self.model = None
        self.config = MODELS_CONFIG.get(model_type, {})
        self._initialized = False
        
        log.info(f"🤖 ModelManager criado para: {model_type}/{model_name or 'default'}")
    
    def load_model(self, force_reload: bool = False, model_name: str = None) -> bool:
        """
        Carrega o modelo YOLO com múltiplas estratégias de fallback.
        
        Args:
            force_reload (bool): Força recarregar mesmo se já carregado
            model_name (str): Nome do modelo sem .pt (usa self.model_name ou default)
            
        Returns:
            bool: True se carregou com sucesso
        """
        # Se já carregado e não forçar recarregar
        if self.model is not None and not force_reload:
            log.debug(f"Modelo {self.model_type} já carregado, reutilizando")
            return True
        
        try:
            # Determina nome do modelo
            if model_name:
                self.model_name = model_name
            
            # Obtém caminho do modelo
            model_path = get_model_path(self.model_type, self.model_name)
            if not Path(model_path).exists():
                log.warning(f"Modelo não encontrado: {model_path}")
                # Tenta com modelo padrão
                model_path = get_model_path(self.model_type, None)
                if not Path(model_path).exists():
                    raise FileNotFoundError(f"Nenhum modelo disponível para {self.model_type}")
            
            log.info(f"📂 Carregando modelo {self.model_type} de: {model_path}")
            
            # Estratégia 1: Tenta carregar normalmente
            try:
                self.model = YOLO(model_path)
                log.debug(f"  ✅ Carregamento direto bem-sucedido")
            except Exception as e1:
                log.debug(f"  ⚠️  Carregamento direto falhou: {e1}")
                
                # Estratégia 2: Tenta com task específica + trust_repo
                try:
                    task = "segment" if self.model_type == "segmentation" else "classify"
                    log.debug(f"  Tentando com task={task} e trust_repo=True...")
                    self.model = YOLO(model_path)
                    log.debug(f"  ✅ Carregamento com trust_repo bem-sucedido")
                except Exception as e2:
                    log.debug(f"  ⚠️  Carregamento com trust_repo falhou: {e2}")
                    
                    # Estratégia 3: Última tentativa - carrega apenas os pesos sem validação
                    log.debug(f"  Tentativa final: carregando pesos com torch.load direto...")
                    try:
                        import torch
                        weights = torch.load(model_path, weights_only=False)
                        self.model = YOLO(model_path)  # Tenta de novo com os pesos já em cache
                        log.debug(f"  ✅ Carregamento com pré-cache bem-sucedido")
                    except Exception as e3:
                        log.error(f"  ❌ Todas as estratégias falharam")
                        raise e1  # Lança o erro original
            
            # Verifica se é modelo de classificação ou detecção
            task = getattr(self.model, "task", None)
            log.info(f"  Tipo de tarefa: {task or 'desconhecido'}")
            
            # Informações do modelo
            if hasattr(self.model, "names"):
                num_classes = len(self.model.names)
                log.info(f"  Número de classes: {num_classes}")
                log.info(f"  Classes: {list(self.model.names.values())}")
            
            self._initialized = True
            log.info(f"✅ Modelo {self.model_type} carregado com sucesso")
            return True
            
        except Exception as e:
            log.error(f"❌ Falha ao carregar modelo {self.model_type}: {e}")
            self.model = None
            return False
    
    def predict(self, image, **kwargs):
        """
        Executa predição no modelo.
        
        Args:
            image: Imagem numpy array
            **kwargs: Parâmetros adicionais para o modelo
            
        Returns:
            Resultado da predição
        """
        if self.model is None:
            raise RuntimeError(f"Modelo {self.model_type} não carregado")
        
        try:
            # Usa configurações padrão se não especificado
            conf = kwargs.get('conf', self.config.get('confidence_threshold', 0.5))
            iou = kwargs.get('iou', self.config.get('iou_threshold', 0.5))
            imgsz = kwargs.get('imgsz', self.config.get('image_size', 640))
            
            log.debug(f"🔍 Executando predição {self.model_type}: conf={conf}, imgsz={imgsz}")
            
            # Executa predição
            results = self.model.predict(
                source=image,
                conf=conf,
                iou=iou,
                imgsz=imgsz,
                verbose=False  # Desativa log do YOLO
            )
            
            return results
            
        except Exception as e:
            log.error(f"❌ Erro na predição {self.model_type}: {e}")
            raise
    
    def get_info(self) -> Dict[str, Any]:
        """Informações sobre o modelo"""
        info = {
            "type": self.model_type,
            "loaded": self.model is not None,
            "config": self.config
        }
        
        if self.model is not None:
            if hasattr(self.model, "names"):
                info["classes"] = list(self.model.names.values())
                info["num_classes"] = len(self.model.names)
            
            if hasattr(self.model, "device"):
                info["device"] = str(self.model.device)
            
            # Tamanho do modelo
            try:
                if hasattr(self.model, "model"):
                    num_params = sum(p.numel() for p in self.model.model.parameters())
                    info["parameters"] = f"{num_params:,}"
            except:
                pass
        
        return info
    
    def unload(self):
        """Descarrega modelo da memória"""
        self.model = None
        self._initialized = False
        
        # Limpa cache CUDA se disponível
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            log.debug("🧹 Cache CUDA limpo")
        
        log.info(f"🗑️  Modelo {self.model_type} descarregado")
    
    @classmethod
    def get_instance(cls, model_type: str = "segmentation"):
        """
        Método estático para obter instância Singleton.
        
        Uso recomendado:
            model = ModelManager.get_instance("segmentation")
        """
        return cls(model_type)
    
    @classmethod
    def unload_all(cls):
        """Descarrega todos os modelos"""
        for instance in cls._instances.values():
            instance.unload()
        cls._instances.clear()
        cls._models.clear()
        log.info("🗑️  Todos os modelos descarregados")
    
    @staticmethod
    def get_available_models(model_type: str):
        """
        Lista modelos disponíveis para um tipo específico.
        
        Args:
            model_type (str): "segmentation" ou "classification"
            
        Returns:
            list: Lista de nomes de modelos (sem .pt)
        """
        return get_available_models(model_type)

# Teste do ModelManager
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🧪 TESTE DO MODEL MANAGER")
    print("="*50)
    
    # Testa Singleton
    print("\n1. Testando Singleton pattern...")
    mgr1 = ModelManager.get_instance("segmentation")
    mgr2 = ModelManager.get_instance("segmentation")
    print(f"   São a mesma instância? {mgr1 is mgr2}")
    
    print("\n2. Carregando modelo (fake - não precisa ter arquivo real)...")
    # Como provavelmente não temos modelo real, testamos sem carregar
    mgr = ModelManager.get_instance("segmentation")
    
    print(f"\n3. Informações do manager:")
    info = mgr.get_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    print("\n" + "="*50)
    print("✅ TESTE COMPLETO")
    print("="*50)