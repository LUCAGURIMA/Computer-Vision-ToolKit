from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, 
    QDoubleSpinBox, QGroupBox, QScrollArea, QDialog, QDialogButtonBox,
    QGridLayout, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QSize, QThreadPool, QRunnable, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont
import cv2
import numpy as np
from pathlib import Path
from core.system_core import SystemCore
from ..managers.hybrid_inspection_manager import HybridInspectionManager
from core.utils.logger import log

class DetectionCropResultDialog(QDialog):
    """Dialog para visualizar resultado de classificação de um crop"""
    
    def __init__(self, crop: np.ndarray, detection_idx: int, detection_info: dict, 
                 classification_result: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Resultado - Detecção #{detection_idx}')
        self.setGeometry(100, 100, 800, 600)
        self.crop = crop
        self.detection_idx = detection_idx
        self.detection_info = detection_info
        self.classification_result = classification_result
        
        layout = QVBoxLayout()
        
        # Info da detecção
        info_group = QGroupBox('Informações da Detecção')
        info_layout = QHBoxLayout()
        
        bbox = detection_info.get('bbox', [])
        conf = detection_info.get('confidence', 0)
        class_name = detection_info.get('class_name', 'N/A')
        
        info_text = f"Classe: {class_name} | Confiança: {conf:.2%} | BBox: ({int(bbox[0])}, {int(bbox[1])}) -> ({int(bbox[2])}, {int(bbox[3])})"
        info_label = QLabel(info_text)
        info_label.setStyleSheet('padding: 8px; background-color: #3c3c3c; color: white; border-radius: 4px;')
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Visualizar crop
        image_group = QGroupBox('Preview do Crop')
        image_layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet('background-color: #1a1a1a;')
        self._display_crop()
        image_layout.addWidget(self.image_label)
        image_group.setLayout(image_layout)
        layout.addWidget(image_group, 1)
        
        # Resultado de classificação
        result_group = QGroupBox('Resultado de Classificação')
        result_layout = QVBoxLayout()
        
        if classification_result and classification_result.get('success'):
            if 'predicted_class' in classification_result:
                predicted_class = classification_result['predicted_class']
                conf = classification_result.get('confidence', 0)
                status = classification_result.get('status', 'accepted')
                
                # Cor baseada no status
                if status == 'indeterminado':
                    color = '#4a4a2b'  # Amarelo escuro
                else:
                    color = '#3c5c3c'  # Verde escuro
                
                result_text = f"Classe: {predicted_class} | Confiança: {conf:.2%}"
                result_label = QLabel(result_text)
                result_label.setStyleSheet(f'padding: 12px; font-weight: bold; font-size: 14px; background-color: {color}; color: white; border-radius: 4px;')
            else:
                result_text = str(classification_result)
                result_label = QLabel(result_text)
                result_label.setStyleSheet('padding: 8px; background-color: #3c3c3c; color: white;')
        else:
            error = classification_result.get('error', 'Erro desconhecido') if classification_result else 'Sem resultado'
            result_text = f"Erro: {error}"
            result_label = QLabel(result_text)
            result_label.setStyleSheet('padding: 8px; background-color: #5b2b2b; color: #FF6B6B;')
        
        result_layout.addWidget(result_label)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _display_crop(self):
        """Exibe o crop na label"""
        if self.crop is None:
            return
        
        image = self.crop.copy()
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        h, w = image_rgb.shape[:2]
        if len(image_rgb.shape) == 3:
            bytes_per_line = 3 * w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            bytes_per_line = w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        
        pixmap = QPixmap.fromImage(qimage)
        scaled_pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)


class DetectionCropPreviewDialog(QDialog):
    """Dialog para visualizar crop e executar classificação"""
    
    classification_requested = pyqtSignal(int, str, float)  # idx, model, threshold
    
    def __init__(self, crop: np.ndarray, detection_idx: int, detection_info: dict, 
                 available_models: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Classificação - Detecção #{detection_idx}')
        self.setGeometry(100, 100, 800, 600)
        self.crop = crop
        self.detection_idx = detection_idx
        self.detection_info = detection_info
        self.classification_result = None
        
        layout = QVBoxLayout()
        
        # Info da detecção
        info_group = QGroupBox('Informações da Detecção')
        info_layout = QHBoxLayout()
        
        bbox = detection_info.get('bbox', [])
        conf = detection_info.get('confidence', 0)
        class_name = detection_info.get('class_name', 'N/A')
        
        info_text = f"Classe: {class_name} | Confiança: {conf:.2%} | BBox: ({int(bbox[0])}, {int(bbox[1])}) -> ({int(bbox[2])}, {int(bbox[3])})"
        info_label = QLabel(info_text)
        info_label.setStyleSheet('padding: 8px; background-color: #3c3c3c; color: white; border-radius: 4px;')
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Visualizar crop
        image_group = QGroupBox('Preview do Crop')
        image_layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet('background-color: #1a1a1a;')
        self._display_crop()
        image_layout.addWidget(self.image_label)
        image_group.setLayout(image_layout)
        layout.addWidget(image_group, 1)
        
        # Seleção de modelo e threshold
        config_group = QGroupBox('Configuração de Classificação')
        config_layout = QHBoxLayout()
        
        config_layout.addWidget(QLabel('Modelo:'))
        self.model_combo = QComboBox()
        self.model_combo.addItems(available_models)
        config_layout.addWidget(self.model_combo)
        
        config_layout.addWidget(QLabel('Threshold:'))
        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.0, 1.0)
        self.threshold_spinbox.setValue(0.7)
        self.threshold_spinbox.setSingleStep(0.05)
        config_layout.addWidget(self.threshold_spinbox)
        
        config_layout.addStretch()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Resultado (será preenchido depois)
        self.result_group = QGroupBox('Resultado de Classificação')
        self.result_group.setVisible(False)
        result_layout = QVBoxLayout()
        self.result_label = QLabel('Aguardando classificação...')
        self.result_label.setStyleSheet('padding: 8px; font-weight: bold;')
        result_layout.addWidget(self.result_label)
        self.result_group.setLayout(result_layout)
        layout.addWidget(self.result_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.execute_btn = QPushButton(' Executar Classificação')
        self.execute_btn.clicked.connect(self._execute_classification)
        btn_layout.addWidget(self.execute_btn)
        
        btn_layout.addStretch()
        
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        close_btn = QPushButton('Cancelar')
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def _display_crop(self):
        """Exibe o crop na label"""
        if self.crop is None:
            return
        
        image = self.crop.copy()
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        h, w = image_rgb.shape[:2]
        if len(image_rgb.shape) == 3:
            bytes_per_line = 3 * w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            bytes_per_line = w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        
        pixmap = QPixmap.fromImage(qimage)
        scaled_pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def _execute_classification(self):
        """Emite sinal para executar classificação"""
        model = self.model_combo.currentText()
        threshold = self.threshold_spinbox.value()
        self.classification_requested.emit(self.detection_idx, model, threshold)

    def set_classification_result(self, result: dict):
        """Atualiza a janela com resultado de classificação"""
        self.classification_result = result
        self.result_group.setVisible(True)
        self.execute_btn.setEnabled(False)
        self.model_combo.setEnabled(False)
        self.threshold_spinbox.setEnabled(False)
        
        # Formatar resultado
        if result.get('success'):
            if 'predicted_class' in result:
                # Classe real predita pelo modelo
                predicted_class = result['predicted_class']
                conf = result.get('confidence', 0)
                result_text = f"Classe: {predicted_class} | Confiança: {conf:.2%}"
            else:
                result_text = str(result)
        else:
            result_text = f"Erro: {result.get('error', 'Desconhecido')}"
        
        self.result_label.setText(result_text)
        self.result_label.setStyleSheet('padding: 8px; font-weight: bold; background-color: #2b5b2b; color: #90EE90;')


class ClassificationWorker(QRunnable):
    """Worker para executar classificação em thread separada"""
    
    classification_done = pyqtSignal(int, dict)
    
    def __init__(self, hybrid_manager, detection_idx, clf_model, clf_threshold):
        super().__init__()
        self.hybrid_manager = hybrid_manager
        self.detection_idx = detection_idx
        self.clf_model = clf_model
        self.clf_threshold = clf_threshold
    
    def run(self):
        """Executa classificação"""
        result = self.hybrid_manager.perform_classification_for_detection(
            detection_idx=self.detection_idx,
            classification_model=self.clf_model,
            clf_threshold=self.clf_threshold
        )


class HybridInspectionTab(QWidget):
    """Aba principal da inspeção híbrida com fluxo sequencial e classificação paralela"""
    
    def __init__(self, core: SystemCore, available_models: dict, parent=None):
        super().__init__(parent)
        self.core = core
        self.available_models = available_models
        self.hybrid_manager = HybridInspectionManager(core)
        self.current_image = None
        self.crop_dialogs: dict = {}
        self.thread_pool = QThreadPool()
        self.classification_threads = {}
        self.classifications_completed = 0
        self.result_dialogs_opened = False
        
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Inicializa a interface com novo layout"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ===== PAINEL SUPERIOR COM CONTROLES =====
        top_group = QGroupBox('Controles')
        top_layout = QHBoxLayout()
        
        # Modo: Detecção ou Segmentação
        top_layout.addWidget(QLabel('Modo:'))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['Segmentação', 'Detecção'])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.mode_combo.setMaximumWidth(120)
        top_layout.addWidget(self.mode_combo)
        
        top_layout.addSpacing(20)
        
        # Segmentação / Detecção
        self.mode_label = QLabel('📊 Segmentação:')
        top_layout.addWidget(self.mode_label)
        
        self.seg_model_combo = QComboBox()
        seg_models = self.available_models.get('segmentation', [])
        self.seg_model_combo.addItems(seg_models)
        self.seg_model_combo.setMaximumWidth(120)
        top_layout.addWidget(self.seg_model_combo)
        
        self.det_model_combo = QComboBox()
        det_models = self.available_models.get('detection', [])
        self.det_model_combo.addItems(det_models)
        self.det_model_combo.setMaximumWidth(120)
        self.det_model_combo.setVisible(False)
        top_layout.addWidget(self.det_model_combo)
        
        top_layout.addWidget(QLabel('Threshold:'))
        self.det_seg_threshold_spin = QDoubleSpinBox()
        self.det_seg_threshold_spin.setRange(0.0, 1.0)
        self.det_seg_threshold_spin.setValue(0.5)
        self.det_seg_threshold_spin.setSingleStep(0.05)
        self.det_seg_threshold_spin.setMaximumWidth(70)
        top_layout.addWidget(self.det_seg_threshold_spin)
        
        top_layout.addSpacing(20)
        
        # Classificação
        top_layout.addWidget(QLabel('🔍 Classificação:'))
        self.clf_model_combo = QComboBox()
        clf_models = self.available_models.get('classification', [])
        self.clf_model_combo.addItems(clf_models)
        self.clf_model_combo.setMaximumWidth(120)
        top_layout.addWidget(self.clf_model_combo)
        
        top_layout.addWidget(QLabel('Threshold:'))
        self.clf_threshold_spin = QDoubleSpinBox()
        self.clf_threshold_spin.setRange(0.0, 1.0)
        self.clf_threshold_spin.setValue(0.7)
        self.clf_threshold_spin.setSingleStep(0.05)
        self.clf_threshold_spin.setMaximumWidth(70)
        top_layout.addWidget(self.clf_threshold_spin)
        
        top_layout.addStretch()
        
        # Botão principal único
        self.execute_btn = QPushButton(' ▶ EXECUTAR INSPEÇÃO')
        self.execute_btn.setMaximumWidth(180)
        self.execute_btn.setMinimumHeight(40)
        self.execute_btn.setStyleSheet(
            'QPushButton { background-color: #0d47a1; font-weight: bold; color: white; }'
            'QPushButton:hover { background-color: #1565c0; }'
            'QPushButton:pressed { background-color: #0d47a1; }'
        )
        self.execute_btn.clicked.connect(self._execute_hybrid_inspection)
        top_layout.addWidget(self.execute_btn)
        
        top_group.setLayout(top_layout)
        top_group.setMaximumHeight(70)
        main_layout.addWidget(top_group)
        
        # ===== PROGRESS BAR =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(25)
        self.progress_bar.setStyleSheet(
            'QProgressBar { background-color: #2b2b2b; border: 1px solid #555; border-radius: 3px; }'
            'QProgressBar::chunk { background-color: #0d47a1; }'
        )
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # ===== LABEL DE STATUS =====
        self.status_label = QLabel('Pronto. Clique em "EXECUTAR INSPEÇÃO" para começar.')
        self.status_label.setStyleSheet('font-weight: bold; padding: 8px; background-color: #3c3c3c; color: #90EE90;')
        main_layout.addWidget(self.status_label)
        
        # ===== VISUALIZAÇÃO CENTRAL =====
        vis_group = QGroupBox('Visualização')
        vis_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('QScrollArea { background-color: #1a1a1a; border: 1px solid #555; }')
        
        self.image_label = QLabel('Imagem aparecerá aqui')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet('background-color: #1a1a1a; padding: 20px;')
        self.image_label.setMinimumHeight(300)
        
        scroll.setWidget(self.image_label)
        vis_layout.addWidget(scroll)
        
        vis_group.setLayout(vis_layout)
        main_layout.addWidget(vis_group, 1)
        
        # ===== AÇÕES =====
        actions_group = QGroupBox('Ações')
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(10, 10, 10, 10)
        actions_layout.setSpacing(8)
        
        self.vp_btn = QPushButton('✓ Verdadeiro Positivo')
        self.vp_btn.clicked.connect(lambda: self._save_categoria('verdadeiro_positivo'))
        self.vp_btn.setEnabled(False)
        self.vp_btn.setMinimumHeight(45)
        actions_layout.addWidget(self.vp_btn)
        
        self.vn_btn = QPushButton('✓ Verdadeiro Negativo')
        self.vn_btn.clicked.connect(lambda: self._save_categoria('verdadeiro_negativo'))
        self.vn_btn.setEnabled(False)
        self.vn_btn.setMinimumHeight(45)
        actions_layout.addWidget(self.vn_btn)
        
        self.fp_btn = QPushButton('✗ Falso Positivo')
        self.fp_btn.clicked.connect(lambda: self._save_categoria('falso_positivo'))
        self.fp_btn.setEnabled(False)
        self.fp_btn.setMinimumHeight(45)
        actions_layout.addWidget(self.fp_btn)
        
        self.fn_btn = QPushButton('✗ Falso Negativo')
        self.fn_btn.clicked.connect(lambda: self._save_categoria('falso_negativo'))
        self.fn_btn.setEnabled(False)
        self.fn_btn.setMinimumHeight(45)
        actions_layout.addWidget(self.fn_btn)
        
        actions_layout.addStretch()
        
        self.export_btn = QPushButton('📁 Exportar')
        self.export_btn.clicked.connect(self._export_results)
        self.export_btn.setEnabled(False)
        self.export_btn.setMinimumHeight(45)
        actions_layout.addWidget(self.export_btn)
        
        self.clear_btn = QPushButton('🔄 Limpar')
        self.clear_btn.clicked.connect(self._clear_results)
        self.clear_btn.setMinimumHeight(45)
        actions_layout.addWidget(self.clear_btn)
        
        actions_group.setLayout(actions_layout)
        actions_group.setMinimumHeight(100)
        main_layout.addWidget(actions_group)
        
        self.setLayout(main_layout)

    def _connect_signals(self):
        """Conecta sinais do manager"""
        self.hybrid_manager.segmentation_completed.connect(self._on_segmentation_completed)
        self.hybrid_manager.detection_completed.connect(self._on_detection_completed)
        self.hybrid_manager.classification_completed.connect(self._on_classification_completed)
        self.hybrid_manager.error_occurred.connect(self._on_error)

    def _on_mode_changed(self):
        """Alterna entre modo Detecção e Segmentação"""
        mode = self.mode_combo.currentText()
        is_detection = 'Detecção' in mode
        
        if is_detection:
            self.mode_label.setText('🔍 Detecção:')
            self.seg_model_combo.setVisible(False)
            self.det_model_combo.setVisible(True)
        else:
            self.mode_label.setText('📊 Segmentação:')
            self.det_model_combo.setVisible(False)
            self.seg_model_combo.setVisible(True)

    def _execute_hybrid_inspection(self):
        """Executa fluxo completo: captura → detecção/segmentação → classificação (paralela)"""
        try:
            # Reset estado para nova execução
            self._reset_execution_state()
            
            # Desabilitar botão durante execução
            self.execute_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Passo 1: Captura
            self.status_label.setText('📸 Capturando imagem...')
            self.status_label.setStyleSheet('font-weight: bold; padding: 8px; background-color: #2b5b2b; color: #90EE90;')
            result = self.core.capture_image()
            
            if not result or not result.get('success'):
                raise Exception('Falha ao capturar imagem')
            
            self.current_image = result['image']
            self.progress_bar.setValue(25)
            log.info('✓ Imagem capturada com sucesso')
            
            # Passo 2: Detecção or Segmentação
            mode = self.mode_combo.currentText()
            is_detection = 'Detecção' in mode
            
            if is_detection:
                self.status_label.setText('🔍 Executando detecção...')
                model_det = self.det_model_combo.currentText()
                threshold_det = self.det_seg_threshold_spin.value()
                
                det_result = self.hybrid_manager.perform_detection(
                    self.current_image,
                    detection_model=model_det,
                    det_threshold=threshold_det
                )
                
                if not det_result or not det_result.get('success'):
                    raise Exception('Falha na detecção')
                
                self.progress_bar.setValue(50)
                log.info(f'✓ Detecção completa: {det_result.get("total_objects", 0)} objetos')
                
                # Exibir resultado detecção
                annotated = self.hybrid_manager.get_annotated_image()
                if annotated is not None:
                    self._display_image(annotated)
                
                n_detections = det_result.get('total_objects', 0)
            else:
                self.status_label.setText('🔍 Executando segmentação...')
                model_seg = self.seg_model_combo.currentText()
                threshold_seg = self.det_seg_threshold_spin.value()
                
                seg_result = self.hybrid_manager.perform_segmentation(
                    self.current_image,
                    segmentation_model=model_seg,
                    seg_threshold=threshold_seg
                )
                
                if not seg_result or not seg_result.get('success'):
                    raise Exception('Falha na segmentação')
                
                self.progress_bar.setValue(50)
                log.info(f'✓ Segmentação completa: {seg_result.get("total_objects", 0)} detecções')
                
                # Exibir resultado segmentação
                annotated = self.hybrid_manager.get_segmentation_annotated_image()
                if annotated is not None:
                    self._display_image(annotated)
                
                n_detections = seg_result.get('total_objects', 0)
            
            if n_detections == 0:
                self.status_label.setText('✅ Nenhuma detecção encontrada (BOM)')
                self.status_label.setStyleSheet('font-weight: bold; padding: 8px; background-color: #2b5b2b; color: #90EE90;')
                self.progress_bar.setValue(100)
                self._enable_action_buttons()
                self.execute_btn.setEnabled(True)
                log.info('✓ Inspeção completa: sem detecções')
                return
            
            # Passo 3: Classificação em Paralelo
            self.status_label.setText(f'📊 Classificando {n_detections} detecção(ões) em paralelo...')
            self.progress_bar.setMaximum(n_detections)
            self.progress_bar.setValue(0)
            self.classifications_completed = 0
            
            model_clf = self.clf_model_combo.currentText()
            threshold_clf = self.clf_threshold_spin.value()
            
            log.info(f'Iniciando classificação com modelo={model_clf}, threshold={threshold_clf}')
            
            # Executar todas as classificações em paralelo
            for idx in range(n_detections):
                worker = ClassificationWorker(
                    self.hybrid_manager,
                    idx,
                    model_clf,
                    threshold_clf
                )
                self.thread_pool.start(worker)
            
        except Exception as e:
            log.error(f'Erro em inspeção híbrida: {e}', exc_info=True)
            self.status_label.setText(f'❌ Erro: {str(e)}')
            self.status_label.setStyleSheet('font-weight: bold; padding: 8px; background-color: #5b2b2b; color: #FF6B6B;')
            self.execute_btn.setEnabled(True)

    def _reset_execution_state(self):
        """Reseta estado para executar nova inspeção"""
        self.crop_dialogs.clear()
        self.classifications_completed = 0
        self.result_dialogs_opened = False
        self.image_label.setPixmap(QPixmap())

    def _display_image(self, image: np.ndarray):
        """Exibe imagem na label"""
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        h, w = image_rgb.shape[:2]
        if len(image_rgb.shape) == 3:
            bytes_per_line = 3 * w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            bytes_per_line = w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        
        pixmap = QPixmap.fromImage(qimage)
        scaled_pixmap = pixmap.scaledToWidth(600, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    @pyqtSlot(dict)
    def _on_segmentation_completed(self, results: dict):
        """Callback quando segmentação completa"""
        pass  # Controlado por _execute_hybrid_inspection

    def _on_detection_completed(self, results: dict):
        """Callback quando detecção completa"""
        pass  # Controlado por _execute_hybrid_inspection

    @pyqtSlot(int, dict)
    def _on_classification_completed(self, detection_idx: int, result: dict):
        """Callback quando classificação de um crop completa"""
        self.classifications_completed += 1
        self.progress_bar.setValue(self.classifications_completed)
        
        det_results = self.hybrid_manager.detection_results
        if not det_results:
            log.error('❌ detection_results is None in _on_classification_completed')
            return
        
        n_detections = det_results.get('total_objects', 0)
        log.info(f'[CALLBACK] Classificação {detection_idx} completa ({self.classifications_completed}/{n_detections})')
        
        if self.classifications_completed == n_detections:
            # Todas as classificações completadas
            log.info(f'[CALLBACK] ✓✓✓ Todas as {n_detections} classificações completadas!')
            self.status_label.setText('✅ Inspeção Híbrida Completa!')
            self.status_label.setStyleSheet('font-weight: bold; padding: 8px; background-color: #2b5b2b; color: #90EE90;')
            self.progress_bar.setValue(100)
            
            # Abrir dialogs com resultados dos crops
            log.info('[CALLBACK] >>> AGENDANDO ABERTURA DE DIALOGS (300ms)')
            QTimer.singleShot(300, self._show_crop_result_dialogs)
            
            self._enable_action_buttons()
            self.execute_btn.setEnabled(True)

    def _show_crop_result_dialogs(self):
        """Abre dialogs mostrando o resultado de classificação para cada crop"""
        log.info('>>> _show_crop_result_dialogs() chamada')
        
        if self.result_dialogs_opened:
            log.info('Dialogs já foram abertos, retornando')
            return
        
        self.result_dialogs_opened = True
        
        try:
            log.info(f'Manager object: {self.hybrid_manager}')
            
            det_results = self.hybrid_manager.detection_results
            log.info(f'detection_results: {det_results}')
            
            if not det_results:
                log.error('❌ detection_results is None!')
                self.result_dialogs_opened = False
                return
            
            n_detections = det_results.get('total_objects', 0)
            log.info(f'>>> n_detections: {n_detections}')
            
            if n_detections == 0:
                log.info('Nenhuma detecção, sem popups para abrir')
                return
            
            # Verificar crops
            crops = self.hybrid_manager.get_crops()
            log.info(f'>>> Total de crops: {len(crops)}')
            
            # Verificar classification results
            clf_results = self.hybrid_manager.classification_results
            log.info(f'>>> Classification results keys: {list(clf_results.keys())}')
            
            # Calcular posições em cascata para não sobrepor janelas
            x_offset = 50
            y_offset = 50
            dialogs_opened = 0
            
            for idx in range(n_detections):
                log.info(f'\n--- Abrindo dialog para detecção {idx} ---')
                
                crop_info = self.hybrid_manager.get_crop_with_info(idx)
                log.info(f'crop_info: {crop_info is not None}')
                
                classification_result = self.hybrid_manager.get_classification_result_for_crop(idx)
                log.info(f'classification_result: {classification_result}')
                
                if crop_info is None:
                    log.error(f'❌ crop_info is None for idx {idx}')
                    continue
                
                if classification_result is None:
                    log.error(f'❌ classification_result is None for idx {idx}')
                    continue
                
                log.info(f'✓ Abrindo dialog para detecção {idx}')
                
                dialog = DetectionCropResultDialog(
                    crop=crop_info['crop'],
                    detection_idx=idx,
                    detection_info=crop_info,
                    classification_result=classification_result,
                    parent=self
                )
                
                # Posicionar dialogs em cascata
                dialog.move(x_offset * idx, y_offset * idx)
                
                self.crop_dialogs[idx] = dialog
                dialog.show()
                dialogs_opened += 1
                log.info(f'Dialog {idx} exibido')
            
            log.info(f'\n✓✓✓ {dialogs_opened} crop dialogs abertos com sucesso')
            
        except Exception as e:
            log.error(f'❌ Erro ao abrir crop dialogs: {e}', exc_info=True)
            self.result_dialogs_opened = False

    def _enable_action_buttons(self):
        """Habilita botões de ação"""
        self.vp_btn.setEnabled(True)
        self.vn_btn.setEnabled(True)
        self.fp_btn.setEnabled(True)
        self.fn_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

    def _save_categoria(self, categoria: str):
        """Salva resultados em categoria"""
        try:
            result_path = self.hybrid_manager.save_results()
            if result_path:
                categoria_dir = Path('data') / 'classification' / 'c_best' / categoria
                categoria_dir.mkdir(parents=True, exist_ok=True)
                
                import shutil
                shutil.move(str(result_path), str(categoria_dir / result_path.name))
                
                QMessageBox.information(
                    self, 'Sucesso',
                    f'Resultados salvos em: {categoria}'
                )
                self._clear_results()
        except Exception as e:
            log.error(f'Erro ao salvar: {e}')
            QMessageBox.critical(self, 'Erro', f'Erro: {str(e)}')

    def _export_results(self):
        """Exporta resultados"""
        try:
            result_path = self.hybrid_manager.save_results()
            if result_path:
                QMessageBox.information(
                    self, 'Sucesso',
                    f'Resultados exportados para:\n{result_path}'
                )
        except Exception as e:
            log.error(f'Erro ao exportar: {e}')
            QMessageBox.critical(self, 'Erro', f'Erro: {str(e)}')

    def _clear_results(self):
        """Limpa resultados"""
        self.hybrid_manager.clear_results()
        self.current_image = None
        self.crop_dialogs.clear()
        self.classifications_completed = 0
        self.result_dialogs_opened = False
        
        self.image_label.setText('Imagem aparecerá aqui')
        self.image_label.setPixmap(QPixmap())
        self.status_label.setText('Pronto. Clique em "EXECUTAR INSPEÇÃO" para começar.')
        self.status_label.setStyleSheet('font-weight: bold; padding: 8px; background-color: #3c3c3c; color: #90EE90;')
        
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        
        self.execute_btn.setEnabled(True)
        self.vp_btn.setEnabled(False)
        self.vn_btn.setEnabled(False)
        self.fp_btn.setEnabled(False)
        self.fn_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

    @pyqtSlot(str)
    def _on_error(self, error_msg: str):
        """Callback quando erro ocorre"""
        log.error(f'Erro na inspeção híbrida: {error_msg}')
        self.status_label.setText(f'❌ Erro: {error_msg}')
        self.status_label.setStyleSheet('font-weight: bold; padding: 8px; background-color: #5b2b2b; color: #FF6B6B;')
        self.execute_btn.setEnabled(True)

