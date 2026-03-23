from typing import Optional, Dict, Any, List
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
import json
from pathlib import Path
from datetime import datetime
import cv2

class HybridInspectionManager(QObject):
    """
    Manager para inspeção híbrida (Detecção/Segmentação + Classificação)
    Fluxo:
    1. Captura imagem
    2. Executa detecção OU segmentação (seleção do modo)
    3. Para cada detecção, cria crop
    4. Executa classificação em cada crop
    5. Armazena resultados combinados
    """
    
    detection_started = pyqtSignal()
    detection_completed = pyqtSignal(dict)
    segmentation_started = pyqtSignal()
    segmentation_completed = pyqtSignal(dict)
    classification_started = pyqtSignal(int)  # índice da detecção
    classification_completed = pyqtSignal(int, dict)  # índice da detecção, resultados
    all_classifications_completed = pyqtSignal(dict)  # resultados finais completos
    error_occurred = pyqtSignal(str)

    def __init__(self, core):
        super().__init__()
        self.core = core
        self.original_image: Optional[np.ndarray] = None
        self.detection_results: Optional[Dict] = None  # Resultados de detecção ou segmentação
        self.annotated_image: Optional[np.ndarray] = None  # Imagem anotada
        self.crops: List[np.ndarray] = []  # crops para cada detecção
        self.crops_with_bboxes: List[Dict] = []  # {crop, bbox, original_bbox}
        self.classification_results: Dict[int, Dict] = {}  # {índice: resultados}
        self.last_mode: Optional[str] = None  # 'detection' ou 'segmentation'
        self.last_model_detection: Optional[str] = None
        self.last_model_clf: Optional[str] = None
        self.last_threshold_detection: float = 0.5
        self.last_threshold_clf: float = 0.7

    def perform_segmentation(
        self, 
        image: np.ndarray, 
        segmentation_model: str,
        seg_threshold: float
    ) -> Optional[Dict]:
        """Executa segmentação na imagem completa"""
        return self._perform_detection_or_segmentation(
            image=image,
            mode='segmentation',
            model_name=segmentation_model,
            threshold=seg_threshold
        )

    def perform_detection(
        self,
        image: np.ndarray,
        detection_model: str,
        det_threshold: float
    ) -> Optional[Dict]:
        """Executa detecção de objetos na imagem completa"""
        return self._perform_detection_or_segmentation(
            image=image,
            mode='detection',
            model_name=detection_model,
            threshold=det_threshold
        )

    def _perform_detection_or_segmentation(
        self,
        image: np.ndarray,
        mode: str,
        model_name: str,
        threshold: float
    ) -> Optional[Dict]:
        """Executa detecção ou segmentação de forma genérica"""
        try:
            self.original_image = image.copy()
            self.last_mode = mode
            self.last_threshold_detection = threshold
            
            if mode == 'segmentation':
                self.last_model_detection = model_name
                self.segmentation_started.emit()
                # Atualizar threshold no core
                self.core.segmentation_model.config['confidence_threshold'] = threshold
                if model_name:
                    self.core.segmentation_model.load_model(force_reload=True, model_name=model_name)
                # Executar segmentação
                self.detection_results = self.core.perform_segmentation(
                    image=image,
                    model_name=model_name
                )
                # Mapear 'defects' para 'objects' internamente
                if self.detection_results and 'defects' in self.detection_results:
                    self.detection_results['objects'] = self.detection_results.pop('defects')
                    self.detection_results['has_objects'] = self.detection_results.pop('has_defects', False)
                    self.detection_results['total_objects'] = self.detection_results.pop('total_defects', 0)
            else:  # detection
                self.last_model_detection = model_name
                self.detection_started.emit()
                # Atualizar threshold no core
                self.core.detection_model.config['confidence_threshold'] = threshold
                if model_name:
                    self.core.detection_model.load_model(force_reload=True, model_name=model_name)
                # Executar detecção
                self.detection_results = self.core.perform_detection(
                    image=image,
                    model_name=model_name
                )
            
            # Preparar crops para cada detecção
            self._prepare_crops()
            
            # Adicionar contagem de detecções ao resultado
            if self.detection_results:
                self.detection_results['total_objects'] = len(self.crops)
            
            # Desenhar bboxes na imagem original
            self.annotated_image = self._draw_detection_results()
            
            if mode == 'segmentation':
                self.segmentation_completed.emit(self.detection_results)
            else:
                self.detection_completed.emit(self.detection_results)
            return self.detection_results
            
        except Exception as e:
            self.error_occurred.emit(f"Erro na {mode}: {str(e)}")
            return None

    def perform_classification_for_detection(
        self,
        detection_idx: int,
        classification_model: str,
        clf_threshold: float
    ) -> Optional[Dict]:
        """Executa classificação em um crop específico"""
        try:
            if detection_idx >= len(self.crops):
                raise ValueError(f"Índice de detecção inválido: {detection_idx}")
            
            self.last_model_clf = classification_model
            self.last_threshold_clf = clf_threshold
            self.classification_started.emit(detection_idx)
            
            crop = self.crops[detection_idx]
            
            # Atualizar threshold no core
            self.core.classification_model.config['confidence_threshold'] = clf_threshold
            if classification_model:
                self.core.classification_model.load_model(force_reload=True, model_name=classification_model)
            
            # Executar classificação no crop
            result = self.core.perform_classification(
                image=crop,
                model_name=classification_model
            )
            
            # Armazenar resultado
            self.classification_results[detection_idx] = result
            
            self.classification_completed.emit(detection_idx, result)
            
            # Se todas as detecções foram classificadas, emitir sinal de conclusão
            if len(self.classification_results) == len(self.crops):
                self.all_classifications_completed.emit(self._get_combined_results())
            
            return result
            
        except Exception as e:
            self.error_occurred.emit(f"Erro na classificação: {str(e)}")
            return None

    def _prepare_crops(self):
        """Cria crops para cada detecção encontrada"""
        self.crops = []
        self.crops_with_bboxes = []
        
        if not self.detection_results or 'objects' not in self.detection_results:
            return
        
        for idx, obj in enumerate(self.detection_results['objects']):
            bbox = obj['bbox']  # [x1, y1, x2, y2]
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            
            # Garantir que as coordenadas estão dentro da imagem
            h, w = self.original_image.shape[:2]
            x1 = max(0, min(x1, w))
            x2 = max(0, min(x2, w))
            y1 = max(0, min(y1, h))
            y2 = max(0, min(y2, h))
            
            if x2 > x1 and y2 > y1:
                crop = self.original_image[y1:y2, x1:x2].copy()
                self.crops.append(crop)
                self.crops_with_bboxes.append({
                    'crop': crop,
                    'bbox': bbox,
                    'original_bbox': [x1, y1, x2, y2],
                    'confidence': obj.get('confidence', 0),
                    'class_name': obj.get('class_name', 'Unknown')
                })

    def _draw_detection_results(self) -> np.ndarray:
        """Desenha bboxes na imagem original"""
        image = self.original_image.copy()
        
        if not self.detection_results or 'objects' not in self.detection_results:
            return image
        
        colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0)]
        
        for idx, obj in enumerate(self.detection_results['objects']):
            bbox = obj['bbox']
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            
            color = colors[idx % len(colors)]
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            label = f"{idx}: {obj.get('class_name', 'N/A')} ({obj.get('confidence', 0):.2f})"
            cv2.putText(image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return image

    def get_crops(self) -> List[np.ndarray]:
        """Retorna lista de crops"""
        return self.crops

    def get_crop_with_info(self, idx: int) -> Optional[Dict]:
        """Retorna crop específico com informações"""
        if idx < len(self.crops_with_bboxes):
            return self.crops_with_bboxes[idx].copy()
        return None

    def get_annotated_image(self) -> Optional[np.ndarray]:
        """Retorna imagem com bboxes da detecção ou segmentação"""
        return self.annotated_image
    
    def get_segmentation_annotated_image(self) -> Optional[np.ndarray]:
        """Retorna imagem com bboxes da segmentação (compatibilidade com código antigo)"""
        return self.annotated_image

    def get_classification_result_for_crop(self, idx: int) -> Optional[Dict]:
        """Retorna resultado de classificação para um crop"""
        return self.classification_results.get(idx)

    def _get_combined_results(self) -> Dict[str, Any]:
        """Combina todos os resultados (detecção/segmentação + classificação)"""
        combined = {
            'timestamp': datetime.now().isoformat(),
            'mode': self.last_mode,
            'model': self.last_model_detection,
            'threshold': self.last_threshold_detection,
            'classification_model': self.last_model_clf,
            'classification_threshold': self.last_threshold_clf,
            'total_detections': len(self.crops),
            'detection_results': self.detection_results,
            'classifications': {}
        }
        
        for idx, clf_result in self.classification_results.items():
            combined['classifications'][idx] = {
                'detection_info': self.crops_with_bboxes[idx] if idx < len(self.crops_with_bboxes) else {},
                'classification_result': clf_result
            }
        
        return combined

    def get_all_results(self) -> Dict[str, Any]:
        """Retorna todos os resultados combinados"""
        return self._get_combined_results()

    def save_results(self, output_dir: Optional[Path] = None) -> Optional[Path]:
        """Salva resultados da inspeção híbrida"""
        try:
            if output_dir is None:
                output_dir = Path('data/results/hybrid')
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_dir = output_dir / timestamp
            result_dir.mkdir(parents=True, exist_ok=True)
            
            # Salvar dados
            data = self._get_combined_results()
            with open(result_dir / 'hybrid_inspection_data.json', 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Salvar imagem original
            if self.original_image is not None:
                cv2.imwrite(str(result_dir / 'original_image.jpg'), self.original_image)
            
            # Salvar imagem anotada (com bboxes)
            if self.annotated_image is not None:
                cv2.imwrite(str(result_dir / f'{self.last_mode}_annotated.jpg'), self.annotated_image)
            
            # Salvar crops
            crops_dir = result_dir / 'crops'
            crops_dir.mkdir(exist_ok=True)
            for idx, crop in enumerate(self.crops):
                cv2.imwrite(str(crops_dir / f'crop_{idx:02d}.jpg'), crop)
            
            return result_dir
            
        except Exception as e:
            self.error_occurred.emit(f'Falha ao salvar resultados: {e}')
            return None

    def clear_results(self):
        """Limpa todos os resultados"""
        self.original_image = None
        self.segmentation_results = None
        self.segmentation_annotated_image = None
        self.crops = []
        self.crops_with_bboxes = []
        self.classification_results = {}
