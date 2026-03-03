from typing import Optional, Dict, Any
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
import json
from pathlib import Path
from datetime import datetime

class InspectionManager(QObject):
    inspection_started = pyqtSignal()
    inspection_completed = pyqtSignal(dict, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, core):
        super().__init__()
        self.core = core
        self.current_results: Optional[Dict] = None
        self.inspection_image: Optional[np.ndarray] = None
        self.last_inspection_type: Optional[str] = None
        self.last_model_name: Optional[str] = None

    def perform_inspection(self, image: np.ndarray, inspection_type: str, model_name: str, params: Optional[Dict[str, Any]]=None) -> Optional[Dict]:
        try:
            if image is None:
                raise ValueError('Imagem é None')
            self.inspection_started.emit()
            self.inspection_image = image
            self.last_inspection_type = inspection_type
            self.last_model_name = model_name
            results = self.core.run_model(image=image, model_name=model_name, inspection_type=inspection_type, confidence=params.get('confidence', 0.5) if params else 0.5)
            self.current_results = results
            self.inspection_completed.emit(results, inspection_type)
            return results
        except Exception as e:
            self.error_occurred.emit(str(e))
            return None

    def get_current_results(self) -> Optional[Dict]:
        return self.current_results

    def format_results_text(self, results: Dict, inspection_type: str) -> str:
        if not results:
            return 'Sem resultados'
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f'Tipo: {inspection_type.upper()}')
        lines.append(f"Modelo: {results.get('model_name', 'N/A')}")
        lines.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"{'=' * 60}")
        if inspection_type == 'segmentation':
            lines.append(f"Classe: {results.get('class', 'N/A')}")
            lines.append(f"Confiança: {results.get('confidence', 0):.2%}")
            lines.append(f"Área segmentada: {results.get('area', 'N/A')}")
        elif inspection_type == 'classification':
            lines.append(f"Classe Predita: {results.get('predicted_class', 'N/A')}")
            lines.append(f"Confiança: {results.get('confidence', 0):.2%}")
            if 'class_confidences' in results:
                lines.append('\nConfiança por classe:')
                for cls, conf in results['class_confidences'].items():
                    lines.append(f'  - {cls}: {conf:.2%}')
        lines.append(f"{'=' * 60}")
        return '\n'.join(lines)

    def get_results_image(self) -> Optional[np.ndarray]:
        if self.current_results is None:
            return self.inspection_image
        if 'annotated_image' in self.current_results:
            return self.current_results['annotated_image']
        return self.inspection_image

    def save_results(self, image: Optional[np.ndarray]=None, output_dir: Optional[Path]=None) -> Optional[Path]:
        try:
            if self.current_results is None:
                raise ValueError('Sem resultados para salvar')
            if image is None:
                image = self.inspection_image
            if output_dir is None:
                output_dir = Path('data/results')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_dir = output_dir / timestamp
            result_dir.mkdir(parents=True, exist_ok=True)
            data = {'timestamp': timestamp, 'inspection_type': self.last_inspection_type, 'model_name': self.last_model_name, 'results': self.current_results}
            with open(result_dir / 'inspection_data.json', 'w') as f:
                json.dump(data, f, indent=2, default=str)
            if image is not None:
                import cv2
                cv2.imwrite(str(result_dir / 'inspection_image.png'), image)
            return result_dir
        except Exception as e:
            self.error_occurred.emit(f'Falha ao salvar resultados: {e}')
            return None

    def clear_results(self):
        self.current_results = None
        self.inspection_image = None
        self.last_inspection_type = None
        self.last_model_name = None