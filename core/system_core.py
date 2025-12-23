"""
Núcleo principal do sistema.

Esta é a CLASSE MAIS IMPORTANTE de todo o projeto.
Ela coordena todas as partes: câmera, modelos, processamento.
Ela NÃO depende de interface web ou desktop - pode ser usada por ambas.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import numpy as np
import cv2

from core.camera import CameraManager
from core.ml.model_manager import ModelManager
from core.utils.logger import log
from config import SYSTEM_CONFIG, DATA_DIR

class SystemCore:
    """
    Núcleo central do sistema de inspeção.
    
    Funcionalidades:
    1. Gerencia câmeras com fallback
    2. Carrega e executa modelos ML
    3. Processa resultados
    4. Salva inspeções
    5. Notifica interfaces sobre eventos
    
    Design Pattern: Facade Pattern
    - Fornece interface simples para funcionalidades complexas
    - Interface web e desktop conversam APENAS com esta classe
    - Isola complexidade dos subsistemas
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa o núcleo do sistema.
        
        Args:
            config (Dict): Configuração do sistema
        """
        self.config = config or SYSTEM_CONFIG
        self.camera_manager = None
        self.segmentation_model = None
        self.classification_model = None
        self._callbacks = {}  # Para comunicação com interfaces
        self._inspection_history = []
        
        # Cria diretório de resultados
        self.results_dir = Path(self.config.get("results_dir", DATA_DIR / "results"))
        self.results_dir.mkdir(exist_ok=True)
        
        log.info("🚀 Inicializando SystemCore...")
        log.info(f"📁 Diretório de resultados: {self.results_dir}")
    
    def initialize(self) -> bool:
        """
        Inicializa todos os subsistemas.
        
        Returns:
            bool: True se tudo inicializou com sucesso
        """
        try:
            log.info("🔄 Inicializando subsistemas...")
            
            # 1. Inicializa câmera
            self._initialize_camera()
            
            # 2. Carrega modelos
            self._load_models()
            
            log.info("✅ SystemCore inicializado com sucesso")
            return True
            
        except Exception as e:
            log.error(f"❌ Falha ao inicializar SystemCore: {e}")
            return False
    
    def _initialize_camera(self):
        """Inicializa o sistema de câmera"""
        log.info("📷 Inicializando câmera...")
        self.camera_manager = CameraManager()
        
        if not self.camera_manager.initialize():
            raise RuntimeError("Falha ao inicializar câmera")
        
        # Registra callback para notificar interfaces sobre eventos da câmera
        # (implementação avançada - pode ser expandida)
    
    def _load_models(self):
        """Carrega modelos ML"""
        log.info("🤖 Carregando modelos ML...")
        
        # Modelo de segmentação
        self.segmentation_model = ModelManager.get_instance("segmentation")
        if not self.segmentation_model.load_model():
            log.warning("⚠️  Não foi possível carregar modelo de segmentação")
        
        # Modelo de classificação
        self.classification_model = ModelManager.get_instance("classification")
        if not self.classification_model.load_model():
            log.warning("⚠️  Não foi possível carregar modelo de classificação")
    
    def capture_image(self) -> Optional[Dict[str, Any]]:
        """
        Captura uma imagem usando o sistema de câmeras.
        
        Returns:
            Dict com imagem e metadados, ou None se falhar
        """
        try:
            log.info("📸 Capturando imagem...")
            
            # Notifica interfaces que captura começou
            self._notify("capture_started", {})
            
            # Captura imagem
            image = self.camera_manager.capture()
            
            if image is None:
                log.error("❌ Falha ao capturar imagem")
                self._notify("capture_failed", {"error": "Falha na captura"})
                return None
            
            # Prepara resultado
            result = {
                "image": image,
                "timestamp": datetime.now().isoformat(),
                "camera_info": self.camera_manager.get_active_camera_info(),
                "success": True
            }
            
            log.info(f"✅ Imagem capturada: {image.shape}")
            self._notify("capture_completed", result)
            
            return result
            
        except Exception as e:
            log.error(f"❌ Erro na captura: {e}")
            self._notify("capture_failed", {"error": str(e)})
            return None
    
    def perform_segmentation(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Executa inspeção de segmentação.
        
        Args:
            image: Imagem numpy array
            
        Returns:
            Dict com resultados da segmentação
        """
        try:
            log.info("🔍 Executando segmentação...")
            self._notify("segmentation_started", {})
            
            if self.segmentation_model is None or self.segmentation_model.model is None:
                raise RuntimeError("Modelo de segmentação não carregado")
            
            # Executa predição
            results = self.segmentation_model.predict(image)
            
            # Processa resultados
            defects = []
            for result in results:
                if result.boxes is not None:
                    for box, conf, cls in zip(result.boxes.xyxy, result.boxes.conf, result.boxes.cls):
                        defect = {
                            "bbox": box.tolist(),
                            "confidence": float(conf),
                            "class": int(cls),
                            "class_name": self.segmentation_model.model.names[int(cls)] if hasattr(self.segmentation_model.model, "names") else str(cls)
                        }
                        defects.append(defect)
            
            # Determina se há defeitos (considera confiança > threshold)
            confidence_threshold = self.segmentation_model.config.get("confidence_threshold", 0.5)
            has_defects = any(d["confidence"] > confidence_threshold for d in defects)
            
            result = {
                "defects": defects,
                "has_defects": has_defects,
                "total_defects": len(defects),
                "confidence_threshold": confidence_threshold,
                "success": True
            }
            
            log.info(f"✅ Segmentação completa: {len(defects)} defeitos encontrados")
            self._notify("segmentation_completed", result)
            
            return result
            
        except Exception as e:
            log.error(f"❌ Erro na segmentação: {e}")
            self._notify("segmentation_failed", {"error": str(e)})
            return {
                "defects": [],
                "has_defects": False,
                "error": str(e),
                "success": False
            }
    
    def perform_classification(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Executa inspeção de classificação.
        
        Args:
            image: Imagem numpy array
            
        Returns:
            Dict com resultados da classificação
        """
        try:
            log.info("🏷️  Executando classificação...")
            self._notify("classification_started", {})
            
            if self.classification_model is None or self.classification_model.model is None:
                raise RuntimeError("Modelo de classificação não carregado")
            
            # Executa predição
            results = self.classification_model.predict(image)
            
            # Processa resultados (classificação retorna diferente de detecção)
            defects_info = []
            
            for result in results:
                # Verifica se tem atributo probs (classificação)
                if hasattr(result, 'probs'):
                    probs = result.probs
                    top1_idx = probs.top1
                    top1_conf = probs.top1conf.item()
                    
                    class_name = "Desconhecido"
                    if hasattr(self.classification_model.model, 'names'):
                        class_name = self.classification_model.model.names[top1_idx]
                    
                    defect = {
                        "class": class_name,
                        "confidence": top1_conf,
                        "class_idx": int(top1_idx)
                    }
                    defects_info.append(defect)
            
            # Verifica confiança contra threshold
            confidence_threshold = self.classification_model.config.get("confidence_threshold", 0.7)
            first_defect = defects_info[0] if defects_info else {}
            
            if first_defect.get("confidence", 0) < confidence_threshold:
                # INDETERMINADO
                result = {
                    "defects_info": [{"class": "INDETERMINADO", "status": "rejected"}],
                    "defects_detected": None,  # None indica indeterminado
                    "confidence": first_defect.get("confidence", 0),
                    "confidence_threshold": confidence_threshold,
                    "status": "indeterminado",
                    "success": True
                }
                log.warning(f"⚠️  Classificação indeterminada: confiança {first_defect.get('confidence'):.3f} < {confidence_threshold}")
            else:
                # Classificação válida
                defects_detected = first_defect.get("class", "").upper() == "RUIM"
                
                result = {
                    "defects_info": defects_info,
                    "defects_detected": defects_detected,
                    "confidence": first_defect.get("confidence", 0),
                    "confidence_threshold": confidence_threshold,
                    "status": "accepted",
                    "success": True
                }
                
                status = "RUIM" if defects_detected else "BOM"
                log.info(f"✅ Classificação: {status} (confiança: {first_defect.get('confidence'):.3f})")
            
            self._notify("classification_completed", result)
            return result
            
        except Exception as e:
            log.error(f"❌ Erro na classificação: {e}")
            self._notify("classification_failed", {"error": str(e)})
            return {
                "defects_info": [],
                "defects_detected": None,
                "error": str(e),
                "success": False
            }
    
    def save_inspection(self, inspection_data: Dict[str, Any]) -> str:
        """
        Salva resultados da inspeção.
        
        Args:
            inspection_data: Dados da inspeção
            
        Returns:
            str: Caminho do arquivo salvo
        """
        if not self.config.get("save_results", True):
            return ""
        
        try:
            # Cria diretório com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            inspection_dir = self.results_dir / timestamp
            inspection_dir.mkdir(exist_ok=True)
            
            # Salva dados em JSON
            data_file = inspection_dir / "inspection_data.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(inspection_data, f, indent=2, ensure_ascii=False)
            
            # Salva imagem se existir
            if "image" in inspection_data:
                # Remove imagem do JSON (é grande e binária)
                image = inspection_data.pop("image")
                image_file = inspection_dir / "image.jpg"
                cv2.imwrite(str(image_file), image)
                inspection_data["image_file"] = str(image_file.relative_to(self.results_dir))
                
                # Recoloca imagem nos dados (como None para indicar que foi salva separadamente)
                inspection_data["image"] = None
            
            # Reescreve JSON sem a imagem
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(inspection_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"💾 Inspeção salva em: {inspection_dir}")
            
            # Adiciona ao histórico
            self._inspection_history.append({
                "timestamp": timestamp,
                "path": str(inspection_dir),
                "type": inspection_data.get("inspection_type", "unknown")
            })
            
            # Mantém histórico limitado
            max_history = self.config.get("max_history", 100)
            if len(self._inspection_history) > max_history:
                self._inspection_history = self._inspection_history[-max_history:]
            
            return str(inspection_dir)
            
        except Exception as e:
            log.error(f"❌ Erro ao salvar inspeção: {e}")
            return ""
    
    def register_callback(self, event: str, callback: Callable):
        """
        Registra uma função de callback para um evento.
        
        Interfaces (web/desktop) usam isso para receber notificações.
        
        Args:
            event (str): Nome do evento (ex: "capture_completed")
            callback (Callable): Função que será chamada
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        
        self._callbacks[event].append(callback)
        log.debug(f"📝 Callback registrado para evento: {event}")
    
    def _notify(self, event: str, data: Any):
        """
        Notifica todos os callbacks registrados para um evento.
        
        Args:
            event (str): Nome do evento
            data (Any): Dados a serem passados para callbacks
        """
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    log.error(f"❌ Erro em callback do evento {event}: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Retorna informações completas do sistema"""
        info = {
            "system": {
                "initialized": self.camera_manager is not None,
                "results_dir": str(self.results_dir),
                "inspection_history_count": len(self._inspection_history)
            },
            "camera": self.camera_manager.get_active_camera_info() if self.camera_manager else {},
            "models": {
                "segmentation": self.segmentation_model.get_info() if self.segmentation_model else {},
                "classification": self.classification_model.get_info() if self.classification_model else {}
            },
            "config": self.config
        }
        return info
    
    def cleanup(self):
        """Libera todos os recursos"""
        log.info("🧹 Limpando recursos do SystemCore...")
        
        if self.camera_manager:
            self.camera_manager.release()
        
        # Descarrega modelos
        ModelManager.unload_all()
        
        log.info("✅ SystemCore limpo")

# Teste do SystemCore
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🧪 TESTE DO SYSTEM CORE")
    print("="*50)
    
    # Cria core
    core = SystemCore()
    
    # Testa inicialização
    print("\n1. Inicializando SystemCore...")
    if core.initialize():
        print("✅ SystemCore inicializado")
        
        # Mostra informações
        info = core.get_system_info()
        print(f"\n2. Informações do sistema:")
        print(f"   Câmera ativa: {info['camera'].get('type', 'N/A')}")
        print(f"   Modelos carregados:")
        print(f"     - Segmentação: {info['models']['segmentation'].get('loaded', False)}")
        print(f"     - Classificação: {info['models']['classification'].get('loaded', False)}")
        
        # Testa callback
        print("\n3. Testando sistema de callbacks...")
        def test_callback(data):
            print(f"   📢 Callback chamado com: {list(data.keys())}")
        
        core.register_callback("test_event", test_callback)
        core._notify("test_event", {"message": "Teste de callback"})
        
        # Limpa
        print("\n4. Limpando recursos...")
        core.cleanup()
        
    else:
        print("❌ Falha ao inicializar SystemCore")
    
    print("\n" + "="*50)
    print("✅ TESTE COMPLETO")
    print("="*50)