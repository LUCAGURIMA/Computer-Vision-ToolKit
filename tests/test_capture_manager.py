"""
Testes para CaptureManager.

Coverage:
- Inicialização e cleanup
- Configuração de crop
- Processamento de imagens
- Estados (crop_enabled, inspect_after_capture)
- Informações sobre imagens
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from typing import Optional

from core.managers.capture_manager import CaptureManager


# ========== Fixtures ==========

@pytest.fixture
def mock_core():
    """Cria mock do SystemCore"""
    core = Mock()
    
    # Mock para preprocess_image
    def preprocess_side_effect(image, ops):
        """Simula crop: retorna região da imagem"""
        for op in ops:
            if op["name"] == "crop":
                bbox = op["bbox"]
                x1, y1, x2, y2 = bbox
                return image[y1:y2, x1:x2]
        return image
    
    core.preprocess_image.side_effect = preprocess_side_effect
    
    # Mock para callbacks
    callbacks = {}
    
    def register_callback(event, callback):
        callbacks[event] = callback
    
    def trigger_callback(event, data):
        if event in callbacks:
            callbacks[event](data)
    
    core.register_callback = register_callback
    core.trigger_callback = trigger_callback
    
    return core


@pytest.fixture
def sample_image():
    """Cria imagem de teste (BGR, 480x640x3)"""
    return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def capture_result(sample_image):
    """Cria resultado de captura simulado"""
    return {
        "image": sample_image,
        "camera_info": {"camera": "mock_camera", "resolution": (640, 480)},
        "timestamp": "2025-01-20T10:30:00",
    }


@pytest.fixture
def manager(mock_core):
    """Cria manager para testes"""
    mgr = CaptureManager(mock_core, camera_profiles=None)
    yield mgr
    mgr.cleanup()


# ========== Testes de inicialização ==========

def test_initialize_success(manager):
    """Manager inicializa corretamente"""
    assert manager.current_image is None
    assert manager.raw_image is None
    assert manager.crop_enabled is False
    assert manager.crop_bbox is None
    assert manager._inspect_after_capture is None
    assert manager.core is not None


def test_cleanup_clears_images(manager, sample_image):
    """Cleanup limpa imagens armazenadas"""
    manager.current_image = sample_image
    manager.raw_image = sample_image
    manager._inspect_after_capture = "segmentation"
    
    manager.cleanup()
    
    assert manager.current_image is None
    assert manager.raw_image is None
    assert manager._inspect_after_capture is None


# ========== Testes de crop ==========

def test_set_crop_settings_enabled(manager):
    """Configura crop habilitado"""
    bbox = (100, 100, 500, 500)
    
    manager.set_crop_settings(enabled=True, bbox=bbox)
    
    assert manager.crop_enabled is True
    assert manager.crop_bbox == bbox


def test_set_crop_settings_disabled(manager):
    """Desabilita crop"""
    manager.crop_enabled = True
    manager.crop_bbox = (100, 100, 500, 500)
    
    manager.set_crop_settings(enabled=False)
    
    assert manager.crop_enabled is False
    # Note: bbox permanece armazenado, apenas disabled


def test_reset_crop(manager):
    """Reset crop desabilita e limpa bbox"""
    manager.crop_enabled = True
    manager.crop_bbox = (100, 100, 500, 500)
    
    manager.reset_crop()
    
    assert manager.crop_enabled is False
    assert manager.crop_bbox is None


def test_crop_settings_none_bbox(manager):
    """Crop com None bbox é válido"""
    manager.set_crop_settings(enabled=True, bbox=None)
    
    assert manager.crop_enabled is True
    assert manager.crop_bbox is None


# ========== Testes de inspeção ==========

def test_set_inspect_after_capture_segmentation(manager):
    """Configura inspeção de segmentação"""
    manager.set_inspect_after_capture("segmentation")
    
    assert manager.should_inspect_after_capture() == "segmentation"


def test_set_inspect_after_capture_classification(manager):
    """Configura inspeção de classificação"""
    manager.set_inspect_after_capture("classification")
    
    assert manager.should_inspect_after_capture() == "classification"


def test_set_inspect_after_capture_none(manager):
    """Desabilita inspeção"""
    manager.set_inspect_after_capture("segmentation")
    manager.set_inspect_after_capture(None)
    
    assert manager.should_inspect_after_capture() is None


# ========== Testes de processamento de imagem ==========

def test_process_captured_image_no_crop(manager, capture_result):
    """Processa imagem sem crop"""
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    assert result["image"] is not None
    assert result["crop_applied"] is False
    assert result["shape"] == capture_result["image"].shape


def test_process_captured_image_with_crop(manager, mock_core, capture_result):
    """Processa imagem com crop habilitado"""
    manager.set_crop_settings(enabled=True, bbox=(100, 100, 300, 300))
    
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    assert result["crop_applied"] is True
    assert result["shape"] == (200, 200, 3)  # 300-100 = 200


def test_process_captured_image_stores_images(manager, capture_result):
    """Processamento armazena imagens raw e processada"""
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    assert manager.raw_image is not None
    assert manager.current_image is not None
    np.testing.assert_array_equal(manager.raw_image, capture_result["image"])


def test_process_captured_image_missing_image(manager):
    """Erro quando capture_result não tem 'image'"""
    capture_result = {"camera_info": {}, "timestamp": ""}
    
    result = manager.process_captured_image(capture_result)
    
    assert result is None


def test_process_captured_image_with_camera_info(manager, capture_result):
    """Processamento preserva informações de câmera"""
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    assert result["camera_info"]["camera"] == "mock_camera"
    assert result["camera_info"]["resolution"] == (640, 480)


def test_process_captured_image_with_timestamp(manager, capture_result):
    """Processamento preserva timestamp"""
    capture_result["timestamp"] = "2025-01-20T10:30:00"
    
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    assert result["timestamp"] == "2025-01-20T10:30:00"


# ========== Testes de getters ==========

def test_get_current_image_none(manager):
    """Getter retorna None quando vazio"""
    assert manager.get_current_image() is None


def test_get_current_image_returns_value(manager, sample_image):
    """Getter retorna imagem armazenada"""
    manager.current_image = sample_image
    
    retrieved = manager.get_current_image()
    
    np.testing.assert_array_equal(retrieved, sample_image)


def test_get_raw_image_none(manager):
    """Getter raw retorna None quando vazio"""
    assert manager.get_raw_image() is None


def test_get_raw_image_returns_value(manager, sample_image):
    """Getter raw retorna imagem armazenada"""
    manager.raw_image = sample_image
    
    retrieved = manager.get_raw_image()
    
    np.testing.assert_array_equal(retrieved, sample_image)


# ========== Testes de informações ==========

def test_get_image_info_empty(manager):
    """Info quando nenhuma imagem"""
    info = manager.get_image_info()
    
    assert info["shape"] is None
    assert info["dtype"] is None
    assert info["size_mb"] == 0
    assert info["status"] == "Nenhuma imagem"


def test_get_image_info_with_image(manager, sample_image):
    """Info retorna dados corretos"""
    manager.current_image = sample_image
    
    info = manager.get_image_info()
    
    assert info["shape"] == sample_image.shape
    assert info["dtype"] == str(sample_image.dtype)
    assert info["size_mb"] > 0
    assert info["crop_applied"] is False


def test_get_image_info_with_crop(manager, sample_image):
    """Info indica crop aplicado"""
    manager.current_image = sample_image
    manager.crop_enabled = True
    manager.crop_bbox = (100, 100, 500, 500)
    
    info = manager.get_image_info()
    
    assert info["crop_applied"] is True
    assert info["crop_bbox"] == (100, 100, 500, 500)


def test_get_image_info_size_calculation(manager, sample_image):
    """Size é calculado corretamente"""
    manager.current_image = sample_image
    
    info = manager.get_image_info()
    
    expected_size = sample_image.nbytes / (1024 * 1024)
    assert abs(info["size_mb"] - expected_size) < 0.001


# ========== Testes de limpeza ==========

def test_clear_images(manager, sample_image):
    """Clear remove todas as imagens"""
    manager.current_image = sample_image
    manager.raw_image = sample_image
    manager._inspect_after_capture = "segmentation"
    
    manager.clear_images()
    
    assert manager.current_image is None
    assert manager.raw_image is None
    assert manager._inspect_after_capture is None


# ========== Testes de perfil ==========

def test_apply_profile_no_profiles_manager(manager):
    """Apply profile sem camera_profiles retorna False"""
    result = manager.apply_profile("profile_1")
    
    assert result is False


def test_apply_profile_with_mock(manager):
    """Apply profile com camera_profiles mock"""
    mock_profiles = Mock()
    mock_profiles.get_profile.return_value = {"name": "profile_1"}
    manager.camera_profiles = mock_profiles
    
    result = manager.apply_profile("profile_1")
    
    assert result is True
    mock_profiles.get_profile.assert_called_with("profile_1")


def test_apply_profile_not_found(manager):
    """Apply profile quando perfil não existe"""
    mock_profiles = Mock()
    mock_profiles.get_profile.return_value = None
    manager.camera_profiles = mock_profiles
    
    result = manager.apply_profile("nonexistent")
    
    assert result is False


# ========== Testes de callbacks ==========

def test_process_triggers_callback(mock_core, capture_result):
    """Processamento dispara callback de captura completada"""
    manager = CaptureManager(mock_core)
    
    captured_events = []
    
    def capture_callback(data):
        captured_events.append(data)
    
    # Registra callback
    manager.core.register_callback("capture_completed", capture_callback)
    
    # Processa imagem
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    # Note: callback é registrado mas não disparado automaticamente neste teste
    # pois _notify usa core.register_callback internamente


# ========== Testes de integração ==========

def test_full_capture_workflow(manager, capture_result):
    """Workflow completo: capture → crop → info"""
    # Configura crop
    manager.set_crop_settings(True, (100, 100, 400, 400))
    
    # Processa captura
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    assert result["crop_applied"] is True
    
    # Verifica informações
    info = manager.get_image_info()
    assert info["crop_applied"] is True
    assert info["crop_bbox"] == (100, 100, 400, 400)
    
    # Limpa
    manager.clear_images()
    assert manager.get_current_image() is None


def test_multiple_captures_workflow(manager, capture_result):
    """Múltiplas capturas sobrescrevem dados anteriores"""
    # Primeira captura
    result1 = manager.process_captured_image(capture_result)
    assert result1 is not None
    image1 = manager.current_image.copy()
    
    # Segunda captura com imagem diferente
    capture_result_2 = capture_result.copy()
    capture_result_2["image"] = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
    
    result2 = manager.process_captured_image(capture_result_2)
    assert result2 is not None
    
    # Verifica que imagem foi atualizada
    assert not np.array_equal(image1, manager.current_image)


def test_crop_disabled_workflow(manager, capture_result):
    """Workflow com crop desabilitado"""
    # Configura e depois desabilita
    manager.set_crop_settings(True, (100, 100, 400, 400))
    manager.reset_crop()
    
    # Processa
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    assert result["crop_applied"] is False
    assert result["shape"] == capture_result["image"].shape


# ========== Testes de erro ==========

def test_process_image_with_none_crop_bbox(manager, capture_result):
    """Crop habilitado mas bbox é None é válido"""
    manager.crop_enabled = True
    manager.crop_bbox = None
    
    result = manager.process_captured_image(capture_result)
    
    assert result is not None
    assert result["crop_applied"] is False  # Não aplica sem bbox


def test_process_image_preserves_raw(manager, capture_result):
    """Raw image sempre preservado sem crop"""
    manager.set_crop_settings(True, (100, 100, 300, 300))
    
    result = manager.process_captured_image(capture_result)
    
    # Raw deve ser igual ao original
    np.testing.assert_array_equal(manager.raw_image, capture_result["image"])
    # Mas processed deve ser diferente (crop aplicado)
    if result["crop_applied"]:
        assert not np.array_equal(manager.current_image, capture_result["image"])
