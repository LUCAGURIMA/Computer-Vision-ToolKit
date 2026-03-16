"""Result Processor Qt - Gerencia processamento e formatação de resultados de inspeção."""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

import cv2
import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QApplication

from core.utils.logger import log


class ResultProcessorQt(QObject):
    """Processor para resultados de inspeção com integração Qt.
    
    Responsável por:
    - Formatação de resultados em texto legível
    - Salvamento de resultados e categorização
    - Exportação de imagens e histórico
    - Limpeza de dados
    """
    
    # Sinais
    result_saved = pyqtSignal(str)  # emite caminho salvo
    result_cleared = pyqtSignal()   # resultado limpo
    result_exported = pyqtSignal(str)  # emite tipo de exportação
    result_copied = pyqtSignal()  # resultado copiado
    error_occurred = pyqtSignal(str)  # emite mensagem de erro
    
    def __init__(self, core):
        """Inicializa o processador de resultados.
        
        Args:
            core: SystemCore instance
        """
        super().__init__()
        self.core = core
    
    # ========== Formatação de Resultados ==========
    
    def format_result_text(self, results: dict, inspection_type: str) -> str:
        """Formata resultado para exibição legível.
        
        Args:
            results: Dicionário com resultados da inspeção
            inspection_type: Tipo de inspeção ('classification' ou 'segmentation')
        
        Returns:
            String formatada do resultado
        """
        try:
            if inspection_type == 'classification':
                return self._format_classification_result(results)
            else:
                return self._format_segmentation_result(results)
        except Exception as e:
            log.error(f'Erro ao formatar resultado: {e}')
            return f' ERRO na formatação: {e}'
    
    def _format_classification_result(self, results: dict) -> str:
        """Formata resultado de classificação."""
        status = results.get('status', 'unknown')
        defects_info = results.get('defects_info', [])
        
        if status == 'indeterminado':
            text = ' CLASSIFICAÇÃO INDETERMINADA\n\n'
            text += 'Confiança abaixo do limite.\n'
            text += 'Recomenda-se nova captura.'
        elif results.get('defects_detected'):
            text = ' FRUTA RUIM\n\n'
            if defects_info:
                defect = defects_info[0]
                text += f"Classe: {defect.get('class', 'N/A')}\n"
                text += f"Confiança: {defect.get('confidence', 0):.1%}"
        else:
            text = ' FRUTA BOA\n\n'
            if defects_info:
                defect = defects_info[0]
                text += f"Classe: {defect.get('class', 'N/A')}\n"
                text += f"Confiança: {defect.get('confidence', 0):.1%}"
        
        return text
    
    def _format_segmentation_result(self, results: dict) -> str:
        """Formata resultado de segmentação."""
        total = results.get('total_defects', 0)
        has_defects = results.get('has_defects', False)
        
        if has_defects:
            text = f'  {total} DEFEITO(S) ENCONTRADO(S)\n\n'
            defects = results.get('defects', [])
            for defect in defects[:5]:
                text += f"• {defect.get('class_name', 'N/A')}: {defect.get('confidence', 0):.1%}\n"
        else:
            text = ' NENHUM DEFEITO ENCONTRADO'
        
        return text
    
    # ========== Salvamento de Resultados ==========
    
    def save_inspection_results(
        self,
        inspection_image: np.ndarray,
        results: dict,
        inspection_type: str,
        model_name: str,
        annotated_image: Optional[np.ndarray] = None,
        parent=None
    ) -> Optional[str]:
        """Salva resultados de inspeção.
        
        Args:
            inspection_image: Imagem original da inspeção
            results: Dicionário com resultados
            inspection_type: Tipo de inspeção ('classification' ou 'segmentation')
            model_name: Nome do modelo usado
            annotated_image: Imagem com anotações (opcional)
            parent: Widget pai para diálogos
        
        Returns:
            Caminho salvo ou None se falhou
        """
        if inspection_image is None or results is None:
            msg = 'Sem Dados: Não há resultados para salvar!'
            log.warning(msg)
            if parent:
                QMessageBox.warning(parent, 'Sem Dados', msg)
            return None
        
        try:
            log.info(f'Iniciando salvamento de resultados: {inspection_type}')
            
            # Preparar estrutura de diretórios
            map_types = {'Segmentação': 'segmentation', 'Classificação': 'classification'}
            inspection_type_key = map_types.get(inspection_type, inspection_type.lower())
            
            model_key = model_name.replace(' ', '_') if model_name else 'unknown_model'
            
            dest_base = Path.cwd() / 'data' / inspection_type_key / model_key / 'results'
            dest_base.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for core
            inspection_data = {
                'inspection_type': inspection_type_key,
                'timestamp': datetime.now().isoformat(),
                'image': inspection_image,
                'results': results
            }
            
            # Salvar via core
            old_results_dir = getattr(self.core, 'results_dir', None)
            saved_path = None
            
            try:
                self.core.results_dir = dest_base
                saved_path = self.core.save_inspection(inspection_data)
                log.info(f'Inspeção salva em: {saved_path}')
                
                # Salvar imagem anotada se disponível
                if saved_path and annotated_image is not None:
                    try:
                        annotated_path = Path(saved_path) / 'annotated.jpg'
                        cv2.imwrite(str(annotated_path), annotated_image)
                        log.info(f'Imagem anotada salva: {annotated_path}')
                    except Exception as e:
                        log.error(f'Erro ao salvar annotated.jpg: {e}')
            finally:
                if old_results_dir is not None:
                    self.core.results_dir = old_results_dir
            
            if saved_path:
                log.info(f'Resultados salvos com sucesso: {saved_path}')
                self.result_saved.emit(str(saved_path))
                if parent:
                    msg = f'Resultados salvos em:\n{saved_path}'
                    log.info(msg)
                return str(saved_path)
            else:
                msg = 'Não foi possível salvar resultados'
                log.error(msg)
                if parent:
                    QMessageBox.warning(parent, 'Erro', msg)
                return None
        
        except Exception as e:
            error_msg = f'{type(e).__name__}: {str(e)}'
            log.exception(f'ERRO ao salvar: {error_msg}')
            if parent:
                QMessageBox.critical(parent, 'Erro ao Salvar Resultados', f'Falha ao salvar:\n\n{error_msg}')
            self.error_occurred.emit(error_msg)
            return None
    
    # ========== Categorização ==========
    
    def save_categoria(
        self,
        categoria: str,
        inspection_image: np.ndarray,
        results: dict,
        inspection_type: str,
        model_name: str,
        annotated_image: Optional[np.ndarray] = None,
        parent=None
    ) -> Optional[str]:
        """Salva resultado em categoria (VP, VN, FP, FN).
        
        Args:
            categoria: Categoria ('verdadeiro_positivo', 'falso_positivo', etc)
            inspection_image: Imagem original
            results: Resultados da inspeção
            inspection_type: Tipo de inspeção
            model_name: Nome do modelo
            annotated_image: Imagem anotada (opcional)
            parent: Widget pai para diálogos
        
        Returns:
            Caminho salvo ou None
        """
        if inspection_image is None or results is None:
            msg = 'Realize uma inspeção antes de categorizar!'
            log.warning(msg)
            if parent:
                QMessageBox.warning(parent, 'Sem Dados', msg)
            return None
        
        try:
            log.info(f'Salvando categoria: {categoria}')
            
            # Preparar estrutura
            map_types = {'Segmentação': 'segmentation', 'Classificação': 'classification'}
            inspection_type_key = map_types.get(inspection_type, inspection_type.lower())
            model_key = model_name.replace(' ', '_') if model_name else 'unknown_model'
            
            base = Path.cwd() / 'data' / inspection_type_key / model_key / categoria
            base.mkdir(parents=True, exist_ok=True)
            
            # Criar pasta com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            folder = base / timestamp
            folder.mkdir(exist_ok=True)
            
            # Salvar imagens
            orig_file = folder / 'original.jpg'
            cv2.imwrite(str(orig_file), inspection_image)
            log.info(f'Imagem original salva: {orig_file}')
            
            if annotated_image is not None:
                annot_file = folder / 'annotated.jpg'
                cv2.imwrite(str(annot_file), annotated_image)
                log.info(f'Imagem anotada salva: {annot_file}')
            
            # Salvar dados
            data = {
                'inspection_type': inspection_type,
                'results': results,
                'timestamp': timestamp
            }
            with open(folder / 'inspection_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            log.info(f'Categoria salva: {folder}')
            self.result_saved.emit(str(folder))
            
            if parent:
                msg = f'Imagens e dados salvos em:\n{folder}'
                QMessageBox.information(parent, 'Sucesso', msg)
            
            return str(folder)
        
        except Exception as e:
            error_msg = f'Falha ao salvar categoria {categoria}: {e}'
            log.exception(error_msg)
            if parent:
                QMessageBox.critical(parent, 'Erro', error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    # ========== Exportação ==========
    
    def export_inspection_image(
        self,
        annotated_image: Optional[np.ndarray],
        parent=None
    ) -> Optional[str]:
        """Exporta imagem anotada da inspeção.
        
        Args:
            annotated_image: Imagem com anotações
            parent: Widget pai para diálogos
        
        Returns:
            Caminho do arquivo exportado ou None
        """
        if annotated_image is None:
            msg = 'Não há imagem para exportar!'
            log.warning(msg)
            if parent:
                QMessageBox.warning(parent, 'Sem Dados', msg)
            return None
        
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                'Salvar Imagem da Inspeção',
                '',
                'Imagem PNG (*.png);;Imagem JPEG (*.jpg);;Todas as imagens (*.png *.jpg *.bmp)'
            )
            if not file_path:
                return None
            
            cv2.imwrite(file_path, annotated_image)
            log.info(f'Imagem exportada: {file_path}')
            self.result_exported.emit('image')
            
            if parent:
                msg = f'Imagem salva em:\n{file_path}'
                QMessageBox.information(parent, 'Sucesso', msg)
            
            return file_path
        
        except Exception as e:
            error_msg = f'Falha ao exportar imagem: {e}'
            log.exception(error_msg)
            if parent:
                QMessageBox.critical(parent, 'Erro', error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def export_history_csv(
        self,
        table_widget,
        parent=None
    ) -> Optional[str]:
        """Exporta histórico como CSV.
        
        Args:
            table_widget: QTableWidget com dados de histórico
            parent: Widget pai para diálogos
        
        Returns:
            Caminho do arquivo exportado ou None
        """
        try:
            if table_widget.rowCount() == 0:
                msg = 'Nenhum resultado para exportar'
                log.warning(msg)
                if parent:
                    QMessageBox.warning(parent, 'Aviso', msg)
                return None
            
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                'Salvar histórico como CSV',
                str(Path.cwd() / 'historico.csv'),
                'CSV Files (*.csv)'
            )
            if not file_path:
                return None
            
            # Extrair dados da tabela
            headers = []
            for col in range(table_widget.columnCount()):
                header_item = table_widget.horizontalHeaderItem(col)
                if header_item:
                    headers.append(header_item.text())
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                for row in range(table_widget.rowCount()):
                    row_data = []
                    for col in range(table_widget.columnCount()):
                        item = table_widget.item(row, col)
                        if item:
                            row_data.append(item.text())
                        else:
                            row_data.append('')
                    writer.writerow(row_data)
            
            log.info(f'Histórico exportado: {file_path}')
            self.result_exported.emit('csv')
            
            if parent:
                msg = f'Histórico exportado para:\n{file_path}'
                QMessageBox.information(parent, 'Sucesso', msg)
            
            return file_path
        
        except Exception as e:
            error_msg = f'Falha ao exportar histórico: {e}'
            log.exception(error_msg)
            if parent:
                QMessageBox.critical(parent, 'Erro', error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    # ========== Cópia para Clipboard ==========
    
    def copy_inspection_results(
        self,
        results: dict,
        inspection_type: str,
        parent=None
    ) -> bool:
        """Copia resultados para a área de transferência.
        
        Args:
            results: Dicionário com resultados
            inspection_type: Tipo de inspeção
            parent: Widget pai para diálogos
        
        Returns:
            True se sucesso, False se falhou
        """
        if results is None:
            msg = 'Não há resultados para copiar!'
            log.warning(msg)
            if parent:
                QMessageBox.warning(parent, 'Sem Dados', msg)
            return False
        
        try:
            result_text = '=== RESULTADO DA INSPEÇÃO ===\n'
            result_text += f'Tipo: {inspection_type}\n'
            result_text += f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            result_text += '\nDados:\n'
            
            for key, value in results.items():
                result_text += f'  {key}: {value}\n'
            
            clipboard = QApplication.clipboard()
            clipboard.setText(result_text)
            
            log.info('Resultados copiados para clipboard')
            self.result_copied.emit()
            
            if parent:
                QMessageBox.information(parent, 'Sucesso', 'Resultados copiados para a área de transferência!')
            
            return True
        
        except Exception as e:
            error_msg = f'Falha ao copiar: {e}'
            log.exception(error_msg)
            if parent:
                QMessageBox.critical(parent, 'Erro', error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    # ========== Limpeza ==========
    
    def clear_all_results(self):
        """Limpa todos os dados de resultado em memória."""
        try:
            log.info('Limpando todos os resultados')
            self.result_cleared.emit()
            return True
        except Exception as e:
            log.error(f'Erro ao limpar resultados: {e}')
            self.error_occurred.emit(str(e))
            return False
