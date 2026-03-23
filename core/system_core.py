import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import numpy as np
import cv2
from core.camera import CameraManager
from core.utils.logger import log
from config import SYSTEM_CONFIG, DATA_DIR
from core.image_processing.image_pipeline import ImagePipeline
from core.services.capture_scheduler import CaptureScheduler

class SystemCore:

    def __init__(self, config: Optional[Dict[str, Any]]=None):
        self.config = config or SYSTEM_CONFIG
        self.camera_manager = None
        self.detection_model = None
        self.segmentation_model = None
        self.classification_model = None
        self._callbacks = {}
        self._inspection_history = []
        self.results_dir = Path(self.config.get('results_dir', DATA_DIR / 'results'))
        self.results_dir.mkdir(exist_ok=True)
        self._image_pipeline = ImagePipeline(self.config.get('image_pipeline', {}))
        self._capture_scheduler = None
        log.info('Inicializando SystemCore...')
        log.info(f'Diretorio de resultados: {self.results_dir}')

    def initialize(self) -> bool:
        try:
            log.info(' Inicializando subsistemas...')
            self._initialize_camera()
            self._load_models()
            log.info(' SystemCore inicializado com sucesso')
            return True
        except Exception as e:
            log.error(f' Falha ao inicializar SystemCore: {e}')
            return False

    def _initialize_camera(self):
        log.info(' Inicializando câmera...')
        self.camera_manager = CameraManager()
        if not self.camera_manager.initialize():
            raise RuntimeError('Falha ao inicializar câmera')

    def _load_models(self):
        log.info(' Carregando modelos ML...')
        try:
            from core.ml.model_manager import ModelManager
        except Exception as e:
            log.error(f' Não foi possível importar ModelManager: {e}')
            log.warning('  Sistema continuará sem modelos ML')
            return
        self.detection_model = ModelManager.get_instance('detection')
        if not self.detection_model.load_model():
            log.warning('  Não foi possível carregar modelo de detecção')
        self.segmentation_model = ModelManager.get_instance('segmentation')
        if not self.segmentation_model.load_model():
            log.warning('  Não foi possível carregar modelo de segmentação')
        self.classification_model = ModelManager.get_instance('classification')
        if not self.classification_model.load_model():
            log.warning('  Não foi possível carregar modelo de classificação')

    def update_model_configs(self, detection_threshold: float=None, segmentation_threshold: float=None, classification_threshold: float=None) -> bool:
        log.debug(f'update_model_configs chamado com det_thresh={detection_threshold}, seg_thresh={segmentation_threshold}, class_thresh={classification_threshold}')
        try:
            updated = False
            if detection_threshold is not None and self.detection_model:
                old_threshold = self.detection_model.config.get('confidence_threshold', 0.5)
                self.detection_model.config['confidence_threshold'] = detection_threshold
                log.info(f' Threshold de detecção atualizado: {old_threshold:.3f} → {detection_threshold:.3f}')
                updated = True
            if segmentation_threshold is not None and self.segmentation_model:
                old_threshold = self.segmentation_model.config.get('confidence_threshold', 0.5)
                self.segmentation_model.config['confidence_threshold'] = segmentation_threshold
                log.info(f' Threshold de segmentação atualizado: {old_threshold:.3f} → {segmentation_threshold:.3f}')
                updated = True
            if classification_threshold is not None and self.classification_model:
                old_threshold = self.classification_model.config.get('confidence_threshold', 0.7)
                self.classification_model.config['confidence_threshold'] = classification_threshold
                log.info(f' Threshold de classificação atualizado: {old_threshold:.3f} → {classification_threshold:.3f}')
                updated = True
            if updated:
                log.info(' Configurações dos modelos atualizadas')
                return True
            else:
                log.warning('  Nenhum modelo disponível para atualização')
                return False
        except Exception as e:
            log.error(f' Erro ao atualizar configurações dos modelos: {e}')
            return False

    def reload_models(self, force_reload: bool=False) -> bool:
        try:
            log.info(' Recarregando modelos ML...')
            success_count = 0
            if self.detection_model:
                if self.detection_model.load_model(force_reload=force_reload):
                    log.info(' Modelo de detecção recarregado')
                    success_count += 1
                else:
                    log.warning('  Falha ao recarregar modelo de detecção')
            if self.segmentation_model:
                if self.segmentation_model.load_model(force_reload=force_reload):
                    log.info(' Modelo de segmentação recarregado')
                    success_count += 1
                else:
                    log.warning('  Falha ao recarregar modelo de segmentação')
            if self.classification_model:
                if self.classification_model.load_model(force_reload=force_reload):
                    log.info(' Modelo de classificação recarregado')
                    success_count += 1
                else:
                    log.warning('  Falha ao recarregar modelo de classificação')
            if success_count > 0:
                log.info(f' {success_count} modelo(s) recarregado(s) com sucesso')
                return True
            else:
                log.warning('  Nenhum modelo foi recarregado')
                return False
        except Exception as e:
            log.error(f' Erro ao recarregar modelos: {e}')
            return False

    def capture_image(self) -> Optional[Dict[str, Any]]:
        try:
            log.info(' Capturando imagem...')
            self._notify('capture_started', {})
            image = self.camera_manager.capture()
            if image is None:
                log.error(' Falha ao capturar imagem')
                self._notify('capture_failed', {'error': 'Falha na captura'})
                return None
            result = {'image': image, 'timestamp': datetime.now().isoformat(), 'camera_info': self.camera_manager.get_active_camera_info(), 'success': True}
            log.info(f' Imagem capturada: {image.shape}')
            self._notify('capture_completed', result)
            return result
        except Exception as e:
            log.error(f' Erro na captura: {e}')
            self._notify('capture_failed', {'error': str(e)})
            return None

    def preprocess_image(self, image: np.ndarray, ops: List[Dict[str, Any]]) -> np.ndarray:
        return self._image_pipeline.apply(image, ops)

    def start_periodic_capture(self, interval_seconds: float, save_dir: str, preprocess_ops: Optional[List[Dict[str, Any]]]=None):
        if not self.camera_manager:
            self._initialize_camera()
        save_path = Path(save_dir)
        preprocess_fn = None
        if preprocess_ops:
            preprocess_fn = lambda img: self._image_pipeline.apply(img, preprocess_ops)
        self._capture_scheduler = CaptureScheduler(self.camera_manager, save_path, on_saved=lambda d: self._notify('periodic_capture_saved', d), preprocess_fn=preprocess_fn)
        self._capture_scheduler.start(interval_seconds)

    def stop_periodic_capture(self):
        if self._capture_scheduler:
            try:
                self._capture_scheduler.stop()
            finally:
                self._capture_scheduler = None

    def perform_segmentation(self, image: np.ndarray, model_name: str=None) -> Dict[str, Any]:
        try:
            log.info('Executando segmentação...')
            self._notify('segmentation_started', {})
            if model_name:
                self.segmentation_model.load_model(force_reload=True, model_name=model_name)
            if self.segmentation_model is None or self.segmentation_model.model is None:
                raise RuntimeError('Modelo de segmentação não carregado')
            conf = self.segmentation_model.config.get('confidence_threshold', 0.5)
            iou = self.segmentation_model.config.get('iou_threshold', 0.5)
            imgsz = self.segmentation_model.config.get('image_size', 640)
            results = self.segmentation_model.model.predict(source=image, conf=conf, iou=iou, imgsz=imgsz, verbose=False)
            defects = []
            for result in results:
                if result.boxes is not None:
                    for box, conf_score, cls in zip(result.boxes.xyxy, result.boxes.conf, result.boxes.cls):
                        defect = {'bbox': box.tolist(), 'confidence': float(conf_score), 'class': int(cls), 'class_name': self.segmentation_model.model.names[int(cls)] if hasattr(self.segmentation_model.model, 'names') else str(cls)}
                        defects.append(defect)
            confidence_threshold = self.segmentation_model.config.get('confidence_threshold', 0.5)
            has_defects = any((d['confidence'] > confidence_threshold for d in defects))
            result = {'defects': defects, 'has_defects': has_defects, 'total_defects': len(defects), 'confidence_threshold': confidence_threshold, 'success': True}
            log.info(f' Segmentação completa: {len(defects)} defeitos encontrados')
            self._notify('segmentation_completed', result)
            return result
        except Exception as e:
            log.error(f' Erro na segmentação: {e}')
            self._notify('segmentation_failed', {'error': str(e)})
            return {'defects': [], 'has_defects': False, 'error': str(e), 'success': False}

    def perform_detection(self, image: np.ndarray, model_name: str=None) -> Dict[str, Any]:
        """Executa detecção de objetos na imagem"""
        try:
            log.info('Executando detecção de objetos...')
            self._notify('detection_started', {})
            if model_name:
                self.detection_model.load_model(force_reload=True, model_name=model_name)
            if self.detection_model is None or self.detection_model.model is None:
                raise RuntimeError('Modelo de detecção não carregado')
            conf = self.detection_model.config.get('confidence_threshold', 0.5)
            iou = self.detection_model.config.get('iou_threshold', 0.5)
            imgsz = self.detection_model.config.get('image_size', 640)
            results = self.detection_model.model.predict(source=image, conf=conf, iou=iou, imgsz=imgsz, verbose=False)
            objects = []
            for result in results:
                if result.boxes is not None:
                    for box, conf_score, cls in zip(result.boxes.xyxy, result.boxes.conf, result.boxes.cls):
                        obj = {'bbox': box.tolist(), 'confidence': float(conf_score), 'class': int(cls), 'class_name': self.detection_model.model.names[int(cls)] if hasattr(self.detection_model.model, 'names') else str(cls)}
                        objects.append(obj)
            confidence_threshold = self.detection_model.config.get('confidence_threshold', 0.5)
            has_objects = any((o['confidence'] > confidence_threshold for o in objects))
            result = {'objects': objects, 'has_objects': has_objects, 'total_objects': len(objects), 'confidence_threshold': confidence_threshold, 'success': True}
            log.info(f' Detecção completa: {len(objects)} objetos encontrados')
            self._notify('detection_completed', result)
            return result
        except Exception as e:
            log.error(f' Erro na detecção: {e}')
            self._notify('detection_failed', {'error': str(e)})
            return {'objects': [], 'has_objects': False, 'error': str(e), 'success': False}

    def perform_classification(self, image: np.ndarray, model_name: str=None) -> Dict[str, Any]:
        try:
            log.info('Executando classificação...')
            self._notify('classification_started', {})
            if model_name:
                self.classification_model.load_model(force_reload=True, model_name=model_name)
            if self.classification_model is None or self.classification_model.model is None:
                raise RuntimeError('Modelo de classificação não carregado')
            conf = self.classification_model.config.get('confidence_threshold', 0.7)
            imgsz = self.classification_model.config.get('image_size', 640)
            results = self.classification_model.model.predict(source=image, imgsz=imgsz, verbose=False)
            defects_info = []
            for result in results:
                if hasattr(result, 'probs') and result.probs is not None:
                    probs = result.probs
                    top1_idx = probs.top1
                    top1_conf = probs.top1conf.item()
                    class_name = 'Desconhecido'
                    if hasattr(self.classification_model.model, 'names'):
                        class_name = self.classification_model.model.names[top1_idx]
                    defect = {'class': class_name, 'confidence': top1_conf, 'class_idx': int(top1_idx)}
                    defects_info.append(defect)
            confidence_threshold = self.classification_model.config.get('confidence_threshold', 0.7)
            first_defect = defects_info[0] if defects_info else {}
            if first_defect.get('confidence', 0) < confidence_threshold:
                result = {
                    'defects_info': [{'class': 'INDETERMINADO', 'confidence': first_defect.get('confidence', 0)}],
                    'predicted_class': 'INDETERMINADO',
                    'confidence': first_defect.get('confidence', 0),
                    'confidence_threshold': confidence_threshold,
                    'status': 'indeterminado',
                    'success': True
                }
                log.warning(f"  Classificação indeterminada: confiança {first_defect.get('confidence'):.3f} < {confidence_threshold}")
            else:
                predicted_class = first_defect.get('class', 'Desconhecida')
                result = {
                    'defects_info': defects_info,
                    'predicted_class': predicted_class,
                    'confidence': first_defect.get('confidence', 0),
                    'confidence_threshold': confidence_threshold,
                    'status': 'accepted',
                    'success': True
                }
                log.info(f" Classificação: {predicted_class} (confiança: {first_defect.get('confidence'):.3f})")
            self._notify('classification_completed', result)
            return result
        except Exception as e:
            log.error(f' Erro na classificação: {e}')
            self._notify('classification_failed', {'error': str(e)})
            return {'defects_info': [], 'defects_detected': None, 'error': str(e), 'success': False}

    def save_inspection(self, inspection_data: Dict[str, Any]) -> str:
        if not self.config.get('save_results', True):
            return ''
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            inspection_dir = self.results_dir / timestamp
            inspection_dir.mkdir(exist_ok=True)
            data_file = inspection_dir / 'inspection_data.json'
            if 'image' in inspection_data:
                try:
                    image = inspection_data.pop('image')
                    image_file = inspection_dir / 'image.jpg'
                    cv2.imwrite(str(image_file), image)
                    inspection_data['image_file'] = str(image_file.relative_to(self.results_dir))
                except Exception as e:
                    log.error(f' Falha ao salvar imagem da inspeção: {e}')
                    inspection_data.pop('image', None)
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(inspection_data, f, indent=2, ensure_ascii=False)
            log.info(f' Inspeção salva em: {inspection_dir}')
            self._inspection_history.append({'timestamp': timestamp, 'path': str(inspection_dir), 'type': inspection_data.get('inspection_type', 'unknown')})
            max_history = self.config.get('max_history', 100)
            if len(self._inspection_history) > max_history:
                self._inspection_history = self._inspection_history[-max_history:]
            return str(inspection_dir)
        except Exception as e:
            log.error(f' Erro ao salvar inspeção: {e}')
            return ''

    def register_callback(self, event: str, callback: Callable):
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
        log.debug(f' Callback registrado para evento: {event}')

    def _notify(self, event: str, data: Any):
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    log.error(f' Erro em callback do evento {event}: {e}')

    def get_system_info(self) -> Dict[str, Any]:
        info = {'system': {'initialized': self.camera_manager is not None, 'results_dir': str(self.results_dir), 'inspection_history_count': len(self._inspection_history)}, 'camera': self.camera_manager.get_active_camera_info() if self.camera_manager else {}, 'models': {'segmentation': self.segmentation_model.get_info() if self.segmentation_model else {}, 'classification': self.classification_model.get_info() if self.classification_model else {}}, 'config': self.config}
        return info

    def get_available_cameras(self) -> List[Dict[str, Any]]:
        if not self.camera_manager:
            return []
        return self.camera_manager.detect_all_cameras()

    def switch_camera(self, camera_index: int) -> bool:
        log.debug(f'switch_camera chamado com camera_index={camera_index}')
        if not self.camera_manager:
            log.debug('camera_manager não existe')
            return False
        if camera_index < 0 or camera_index >= len(self.camera_manager.cameras):
            log.debug(f'camera_index inválido: {camera_index}, total câmeras: {len(self.camera_manager.cameras)}')
            return False
        try:
            log.debug('Liberando câmera atual...')
            if self.camera_manager.active_camera:
                try:
                    self.camera_manager.active_camera.release()
                    log.debug('Câmera atual liberada')
                except Exception as e:
                    log.debug(f'Erro ao liberar câmera atual: {e}')
            target_camera = self.camera_manager.cameras[camera_index]
            log.debug(f'Tentando inicializar câmera {camera_index}: {target_camera.__class__.__name__}')
            if target_camera.initialize():
                self.camera_manager.active_camera = target_camera
                self.camera_manager._current_index = camera_index
                log.info(f' Alternado para câmera: {target_camera.__class__.__name__}')
                return True
            else:
                log.warning(f'  Câmera {camera_index} não pôde ser inicializada')
                return False
        except Exception as e:
            log.error(f' Erro ao alternar câmera: {e}')
            return False

    def cleanup(self):
        log.info('Limpando recursos do SystemCore...')
        if self.camera_manager:
            self.camera_manager.release()
        try:
            from core.ml.model_manager import ModelManager
            ModelManager.unload_all()
        except ImportError:
            log.debug('ModelManager não disponível para unload')
        log.info(' SystemCore limpo')
if __name__ == '__main__':
    print('\n' + '=' * 50)
    print(' TESTE DO SYSTEM CORE')
    print('=' * 50)
    core = SystemCore()
    print('\n1. Inicializando SystemCore...')
    if core.initialize():
        print(' SystemCore inicializado')
        info = core.get_system_info()
        print(f'\n2. Informações do sistema:')
        print(f"   Câmera ativa: {info['camera'].get('type', 'N/A')}")
        print(f'   Modelos carregados:')
        print(f"     - Segmentação: {info['models']['segmentation'].get('loaded', False)}")
        print(f"     - Classificação: {info['models']['classification'].get('loaded', False)}")
        print('\n3. Testando sistema de callbacks...')

        def test_callback(data):
            print(f'    Callback chamado com: {list(data.keys())}')
        core.register_callback('test_event', test_callback)
        core._notify('test_event', {'message': 'Teste de callback'})
        print('\n4. Limpando recursos...')
        core.cleanup()
    else:
        print(' Falha ao inicializar SystemCore')
    print('\n' + '=' * 50)
    print(' TESTE COMPLETO')
    print('=' * 50)