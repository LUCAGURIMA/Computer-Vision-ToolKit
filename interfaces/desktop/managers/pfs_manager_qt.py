"""PFS Profile Manager Qt - Gerencia perfis Basler .pfs com interface Qt."""

from pathlib import Path
from typing import Dict, Any, Optional, List

from PyQt5.QtWidgets import (
    QMessageBox, QFileDialog, QInputDialog, QTableWidgetItem, QPushButton
)
from PyQt5.QtCore import pyqtSignal, QObject

from core.camera.basler_profile_manager import BaslerProfileManager
from core.utils.logger import log


class PFSManagerQt(QObject):
    """Manager para perfis PFS com integração Qt."""
    
    # Sinais
    profile_loaded = pyqtSignal(str)  # emite nome do perfil
    profile_saved = pyqtSignal(str)   # emite nome do perfil
    profile_deleted = pyqtSignal(str) # emite nome do perfil
    profile_applied = pyqtSignal(str) # emite nome do perfil
    profiles_list_changed = pyqtSignal(list)  # emite lista de perfis
    parameter_modified = pyqtSignal(str, str, str)  # perfil, param, valor
    error_occurred = pyqtSignal(str)  # emite mensagem de erro
    
    def __init__(self, parent=None):
        """
        Inicializar PFSManagerQt.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.pfs_mgr = BaslerProfileManager()
        self.current_profile = None
        self.parent_window = parent
    
    # ======================== Carregamento e Salvamento ========================
    
    def load_pfs_file(self, parent_window=None) -> bool:
        """
        Abrir diálogo para carregar arquivo .pfs.
        
        Args:
            parent_window: Janela parent para diálogos
            
        Returns:
            bool: True se carregado com sucesso
        """
        pw = parent_window or self.parent_window
        if not pw:
            log.warning('Parent window não definida para load_pfs_file')
            return False
        
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                pw, 'Selecionar arquivo .pfs', '', 'Arquivos .pfs (*.pfs)'
            )
            if not file_path:
                return False
            
            profile_name = Path(file_path).stem
            success = self.pfs_mgr.load_pfs_profile(Path(file_path), profile_name)
            
            if success:
                self.current_profile = profile_name
                self.profile_loaded.emit(profile_name)
                QMessageBox.information(
                    pw, 'Sucesso', 
                    f"Arquivo .pfs carregado como perfil '{profile_name}'!"
                )
                log.info(f'Arquivo .pfs carregado: {file_path}')
                return True
            else:
                self.error_occurred.emit('Não foi possível carregar o arquivo .pfs')
                QMessageBox.critical(pw, 'Erro', 'Não foi possível carregar o arquivo .pfs')
                return False
                
        except Exception as e:
            err_msg = f'Erro ao carregar arquivo .pfs: {e}'
            self.error_occurred.emit(err_msg)
            QMessageBox.critical(pw, 'Erro', err_msg)
            log.error(err_msg)
            return False
    
    def save_pfs_file(self, profile_name: str = None, parent_window=None) -> bool:
        """
        Abrir diálogo para salvar arquivo .pfs.
        
        Args:
            profile_name: Nome do perfil a salvar (usa current_profile se None)
            parent_window: Janela parent para diálogos
            
        Returns:
            bool: True se salvo com sucesso
        """
        pw = parent_window or self.parent_window
        if not pw:
            log.warning('Parent window não definida para save_pfs_file')
            return False
        
        try:
            profile = profile_name or self.current_profile
            if not profile:
                QMessageBox.warning(pw, 'Aviso', 'Selecione um perfil para salvar')
                return False
            
            file_path, _ = QFileDialog.getSaveFileName(
                pw, 'Salvar arquivo .pfs', f'{profile}.pfs', 'Arquivos .pfs (*.pfs)'
            )
            if not file_path:
                return False
            
            success = self.pfs_mgr.save_pfs_profile(profile, Path(file_path))
            
            if success:
                self.profile_saved.emit(profile)
                QMessageBox.information(pw, 'Sucesso', f'Perfil salvo como .pfs: {file_path}')
                log.info(f'Perfil salvo como .pfs: {file_path}')
                return True
            else:
                self.error_occurred.emit('Não foi possível salvar o arquivo .pfs')
                QMessageBox.critical(pw, 'Erro', 'Não foi possível salvar o arquivo .pfs')
                return False
                
        except Exception as e:
            err_msg = f'Erro ao salvar arquivo .pfs: {e}'
            self.error_occurred.emit(err_msg)
            QMessageBox.critical(pw, 'Erro', err_msg)
            log.error(err_msg)
            return False
    
    # ======================== Listagem e Refreshing ========================
    
    def list_profiles(self) -> List[str]:
        """
        Listar todos os perfis PFS disponíveis.
        
        Returns:
            List[str]: Lista de nomes de perfis
        """
        try:
            profiles = self.pfs_mgr.list_pfs_profiles()
            self.profiles_list_changed.emit(profiles)
            return profiles
        except Exception as e:
            log.error(f'Erro ao listar perfis: {e}')
            self.error_occurred.emit(f'Erro ao listar perfis: {e}')
            return []
    
    def refresh_list(self) -> List[str]:
        """Alias para list_profiles()."""
        return self.list_profiles()
    
    # ======================== Carregamento de Dados ========================
    
    def get_profile_data(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """
        Carregar dados de um perfil.
        
        Args:
            profile_name: Nome do perfil
            
        Returns:
            Dict ou None se não encontrado
        """
        try:
            profile_data = self.pfs_mgr.load_profile(profile_name)
            if profile_data:
                self.current_profile = profile_name
                self.profile_loaded.emit(profile_name)
            return profile_data
        except Exception as e:
            log.error(f'Erro ao carregar perfil {profile_name}: {e}')
            self.error_occurred.emit(f'Erro ao carregar perfil: {e}')
            return None
    
    def get_profile_parameters(self, profile_name: str = None) -> Dict[str, Any]:
        """
        Obter parâmetros de um perfil (excludentes de metadata).
        
        Args:
            profile_name: Nome do perfil (usa current_profile se None)
            
        Returns:
            Dict com parâmetros
        """
        profile = profile_name or self.current_profile
        if not profile:
            return {}
        
        profile_data = self.get_profile_data(profile)
        if not profile_data:
            return {}
        
        params = profile_data.get('parameters', {})
        # Filtrar parâmetros de metadata
        camera_params = {
            k: v for k, v in params.items() 
            if k not in ['format', 'metadata', 'file_info', 'converted_at']
        }
        return camera_params
    
    def get_profile_info(self, profile_name: str = None) -> str:
        """
        Formatar informações de um perfil para exibição.
        
        Args:
            profile_name: Nome do perfil (usa current_profile se None)
            
        Returns:
            str: Texto formatado com informações
        """
        profile = profile_name or self.current_profile
        if not profile:
            return ""
        
        profile_data = self.get_profile_data(profile)
        if not profile_data:
            return ""
        
        try:
            info_text = ' Informações do Perfil\n\n'
            info_text += f"Nome: {profile_data.get('name', 'N/A')}\n"
            info_text += f"Tipo: {profile_data.get('camera_type', 'N/A')}\n"
            info_text += f"Criado em: {profile_data.get('created_at', 'N/A')}\n"
            info_text += f"Última modificação: {profile_data.get('timestamp', 'N/A')}\n\n"
            
            params = profile_data.get('parameters', {})
            if params.get('format') == 'pfs':
                info_text += ' Formato: Arquivo .pfs convertido\n'
                if 'converted_at' in params:
                    info_text += f" Convertido em: {params['converted_at']}\n"
                metadata = params.get('metadata', {})
                if 'device' in metadata:
                    info_text += f" Dispositivo: {metadata['device']}\n"
                if 'genapi_version' in metadata:
                    info_text += f" GenAPI: {metadata['genapi_version']}\n"
            
            # Contar parâmetros de câmera
            camera_params = sum(
                1 for k in params.keys() 
                if k not in ['format', 'metadata', 'file_info', 'converted_at']
            )
            info_text += f' Parâmetros: {camera_params}\n'
            
            return info_text
            
        except Exception as e:
            log.error(f'Erro ao formatar informações do perfil: {e}')
            return ""
    
    # ======================== Modificação e Exclusão ========================
    
    def modify_parameter(self, profile_name: str, param_name: str, new_value: str) -> bool:
        """
        Modificar um parâmetro de perfil.
        
        Args:
            profile_name: Nome do perfil
            param_name: Nome do parâmetro
            new_value: Novo valor
            
        Returns:
            bool: True se modificado com sucesso
        """
        try:
            success = self.pfs_mgr.modify_pfs_parameter(profile_name, param_name, new_value)
            if success:
                self.parameter_modified.emit(profile_name, param_name, new_value)
                log.info(f'Parâmetro modificado: {param_name} = {new_value}')
            return success
        except Exception as e:
            log.error(f'Erro ao modificar parâmetro: {e}')
            self.error_occurred.emit(f'Erro ao modificar parâmetro: {e}')
            return False
    
    def edit_parameter_dialog(self, profile_name: str, param_name: str, 
                             current_value: str, parent_window=None) -> bool:
        """
        Abrir diálogo para editar parâmetro.
        
        Args:
            profile_name: Nome do perfil
            param_name: Nome do parâmetro
            current_value: Valor atual
            parent_window: Janela parent
            
        Returns:
            bool: True se modificado
        """
        pw = parent_window or self.parent_window
        if not pw:
            log.warning('Parent window não definida para edit_parameter_dialog')
            return False
        
        try:
            new_value, ok = QInputDialog.getText(
                pw, 'Editar Parâmetro', 
                f"Novo valor para '{param_name}':", 
                text=current_value
            )
            
            if ok and new_value != current_value:
                success = self.modify_parameter(profile_name, param_name, new_value)
                if success:
                    QMessageBox.information(
                        pw, 'Sucesso', f"Parâmetro '{param_name}' modificado!"
                    )
                else:
                    QMessageBox.critical(
                        pw, 'Erro', 'Não foi possível modificar o parâmetro'
                    )
                return success
            return False
            
        except Exception as e:
            err_msg = f'Erro ao editar parâmetro: {e}'
            self.error_occurred.emit(err_msg)
            QMessageBox.critical(pw, 'Erro', err_msg)
            log.error(err_msg)
            return False
    
    def delete_profile(self, profile_name: str = None, parent_window=None) -> bool:
        """
        Excluir um perfil com confirmação.
        
        Args:
            profile_name: Nome do perfil (usa current_profile se None)
            parent_window: Janela parent para diálogos
            
        Returns:
            bool: True se excluído com sucesso
        """
        pw = parent_window or self.parent_window
        if not pw:
            log.warning('Parent window não definida para delete_profile')
            return False
        
        try:
            profile = profile_name or self.current_profile
            if not profile:
                QMessageBox.warning(pw, 'Aviso', 'Selecione um perfil para excluir')
                return False
            
            reply = QMessageBox.question(
                pw, 'Confirmar Exclusão', 
                f"Tem certeza que deseja excluir o perfil '{profile}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                profile_path = self.pfs_mgr.profiles_dir / f'{profile}.json'
                if profile_path.exists():
                    profile_path.unlink()
                
                # Reset current profile se for o que foi deletado
                if self.current_profile == profile:
                    self.current_profile = None
                
                self.profile_deleted.emit(profile)
                QMessageBox.information(pw, 'Sucesso', f"Perfil '{profile}' excluído!")
                log.info(f'Perfil .pfs excluído: {profile}')
                return True
            
            return False
            
        except Exception as e:
            err_msg = f'Erro ao excluir perfil: {e}'
            self.error_occurred.emit(err_msg)
            QMessageBox.critical(pw, 'Erro', err_msg)
            log.error(err_msg)
            return False
    
    # ======================== Integração com UI ========================
    
    def populate_params_table(self, profile_name: str = None) -> Dict[str, Any]:
        """
        Retorna parâmetros formatados para popular tabela.
        
        Args:
            profile_name: Nome do perfil (usa current_profile se None)
            
        Returns:
            Dict com parâmetros (já filtrados de metadata)
        """
        params = self.get_profile_parameters(profile_name)
        return params
    
    def setup_table_with_params(self, table_widget, profile_name: str = None) -> None:
        """
        Popular tabela UI com parâmetros de um perfil.
        
        Args:
            table_widget: QTableWidget para popular
            profile_name: Nome do perfil (usa current_profile se None)
        """
        try:
            params = self.get_profile_parameters(profile_name)
            table_widget.setRowCount(len(params))
            
            for row, (param_name, param_value) in enumerate(params.items()):
                # Coluna 0: Nome do parâmetro
                table_widget.setItem(row, 0, QTableWidgetItem(param_name))
                
                # Coluna 1: Valor
                value_item = QTableWidgetItem(str(param_value))
                table_widget.setItem(row, 1, value_item)
                
                # Coluna 2: Botão de edição
                profile = profile_name or self.current_profile
                edit_btn = QPushButton(' Editar')
                edit_btn.clicked.connect(
                    lambda checked, p=profile, pn=param_name, v=str(param_value): 
                    self.edit_parameter_dialog(p, pn, v)
                )
                table_widget.setCellWidget(row, 2, edit_btn)
            
            table_widget.resizeColumnsToContents()
            
        except Exception as e:
            log.error(f'Erro ao popular tabela de parâmetros: {e}')
            self.error_occurred.emit(f'Erro ao popular tabela: {e}')
    
    def setup_info_text(self, text_widget, profile_name: str = None) -> None:
        """
        Popular widget de texto com informações do perfil.
        
        Args:
            text_widget: QTextEdit para popular
            profile_name: Nome do perfil (usa current_profile se None)
        """
        try:
            info_text = self.get_profile_info(profile_name)
            text_widget.setPlainText(info_text)
        except Exception as e:
            log.error(f'Erro ao popular informações do perfil: {e}')
            self.error_occurred.emit(f'Erro ao popular informações: {e}')
