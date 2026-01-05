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
from core.image_processing.image_pipeline import ImagePipeline
from core.services.capture_scheduler import CaptureScheduler

class SystemCore:
    """
    Núcleo central do sistema de inspeção.
    
    Funcionalidades:
    1. Gerencia câmeras com fallback automático
    2. Carrega e executa modelos de ML (YOLOv8)
    3. Processa resultados de segmentação e classificação
    4. Salva inspeções em disco com histórico
    5. Notifica interfaces web/desktop sobre eventos via callbacks
    
    Design Pattern: Facade Pattern
    - Fornece interface simples para funcionalidades complexas
    - Interface web e desktop conversam APENAS com esta classe
    - Isola complexidade dos subsistemas (câmera, modelos, etc)
    
    Exemplo de uso:
        core = SystemCore()
        core.initialize()
        image_data = core.capture_image()
        seg_results = core.perform_segmentation(image_data["image"])
        core.cleanup()
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa o núcleo do sistema com configurações padrão ou customizadas.
        
        Cria o diretório de resultados, inicializa variáveis de controle e
        prepara o sistema para o método initialize() ser chamado.
        
        Args:
            config (Dict, opcional): 
                - Configuração customizada do sistema
                - Se None, usa SYSTEM_CONFIG do arquivo settings.py
                - Exemplos de chaves: "save_results", "results_dir", "max_history"
                
        Exemplo:
            # Usando config padrão
            core = SystemCore()
            
            # Usando config customizada
            custom_config = {
                "save_results": True,
                "results_dir": "/custom/path",
                "max_history": 50
            }
            core = SystemCore(config=custom_config)
        """
        # Usa config fornecida ou carrega a padrão do settings.py
        self.config = config or SYSTEM_CONFIG
        
        # Inicializa componentes como None (serão instanciados em initialize())
        self.camera_manager = None  # Será CameraManager instance
        self.segmentation_model = None  # Será ModelManager instance para segmentação
        self.classification_model = None  # Será ModelManager instance para classificação
        
        # Sistema de callbacks: interfaces podem se registrar para receber eventos
        # Estrutura: {"event_name": [callback1, callback2, ...]}
        self._callbacks = {}
        
        # Histórico de inspeções para rastreamento
        self._inspection_history = []
        
        # Cria e configura diretório onde resultados serão salvos
        self.results_dir = Path(self.config.get("results_dir", DATA_DIR / "results"))
        self.results_dir.mkdir(exist_ok=True)
        # Componentes auxiliares
        self._image_pipeline = ImagePipeline(self.config.get("image_pipeline", {}))
        self._capture_scheduler = None  # Será CaptureScheduler quando iniciado
        
        log.info("🚀 Inicializando SystemCore...")
        log.info(f"📁 Diretório de resultados: {self.results_dir}")
    
    def initialize(self) -> bool:
        """
        Inicializa TODOS os subsistemas do aplicativo.
        
        Deve ser chamado ANTES de usar qualquer funcionalidade de captura ou
        processamento. Inicializa câmera e carrega modelos de ML em memória.
        
        Returns:
            bool: 
                - True se tudo inicializou com sucesso
                - False se houve erro em algum subsistema
        
        Raises:
            Não lança exceção, retorna False em caso de erro (seguro para interfaces)
        
        Exemplo:
            core = SystemCore()
            if core.initialize():
                print("Pronto para usar!")
                image = core.capture_image()
            else:
                print("Erro na inicialização")
        """
        try:
            log.info("🔄 Inicializando subsistemas...")
            
            # 1. Inicializa câmera (com fallback automático)
            self._initialize_camera()
            
            # 2. Carrega modelos de ML (pode levar alguns segundos)
            self._load_models()
            
            log.info("✅ SystemCore inicializado com sucesso")
            return True
            
        except Exception as e:
            log.error(f"❌ Falha ao inicializar SystemCore: {e}")
            return False
    
    def _initialize_camera(self):
        """
        Inicializa o sistema de câmera com fallback automático.
        
        Tenta conectar à câmera primária (Basler). Se falhar, tenta fallbacks
        (webcam, câmera simulada) até conseguir uma conexão bem-sucedida.
        
        Levanta uma exceção se NENHUMA câmera conseguir inicializar.
        
        Raises:
            RuntimeError: Se não conseguir inicializar nenhuma câmera
        
        Exemplo:
            self._initialize_camera()
            # Tenta: Basler -> Webcam -> Mock
        """
        log.info("📷 Inicializando câmera...")
        # Cria gerenciador de câmera que liida com múltiplas cameras
        self.camera_manager = CameraManager()
        
        # Initialize tenta conectar em ordem de fallback
        if not self.camera_manager.initialize():
            raise RuntimeError("Falha ao inicializar câmera")
        
        # Registra callback para notificar interfaces sobre eventos da câmera
        # (implementação avançada - pode ser expandida)
    
    def _load_models(self):
        """
        Carrega os modelos de Machine Learning do disco para memória.
        
        Carrega dois modelos separados:
        1. Segmentação (YOLOv8-seg): detecta e segmenta defeitos na imagem
        2. Classificação (YOLOv8-cls): classifica produto como BOM ou RUIM
        
        Se um modelo falhar ao carregar, log um aviso mas continua
        (assim o sistema não trava se um modelo estiver faltando).
        
        Exemplo:
            self._load_models()
            # Carrega models/segmentation_best.pt
            # Carrega models/classification_best.pt
        """
        log.info("🤖 Carregando modelos ML...")
        
        # Carrega modelo de segmentação (detecta defeitos)
        self.segmentation_model = ModelManager.get_instance("segmentation")
        if not self.segmentation_model.load_model():
            # Aviso em vez de erro - sistema continua sem este modelo
            log.warning("⚠️  Não foi possível carregar modelo de segmentação")
        
        # Carrega modelo de classificação (classifica qualidade)
        self.classification_model = ModelManager.get_instance("classification")
        if not self.classification_model.load_model():
            log.warning("⚠️  Não foi possível carregar modelo de classificação")
    
    def capture_image(self) -> Optional[Dict[str, Any]]:
        """
        Captura uma imagem ao vivo usando o sistema de câmeras.
        
        Notifica interfaces (web/desktop) sobre cada etapa:
        - capture_started: quando inicia a captura
        - capture_completed: sucesso com metadados
        - capture_failed: erro na captura
        
        Returns:
            Dict com estrutura:
                {
                    "image": numpy.ndarray (H, W, 3),  # Imagem em BGR
                    "timestamp": "2026-01-05T14:30:45",  # ISO format
                    "camera_info": {"type": "basler", ...},  # Info da câmera ativa
                    "success": True  # Sempre True se retornar dict
                }
            ou None se falhar
        
        Exemplo:
            result = core.capture_image()
            if result:
                image = result["image"]  # numpy array
                timestamp = result["timestamp"]
                print(f"Capturada em {timestamp}")
                print(f"Resolução: {image.shape}")  # (height, width, 3)
        """
        try:
            log.info("📸 Capturando imagem...")
            
            # Notifica interfaces que captura começou
            self._notify("capture_started", {})
            
            # Captura imagem da câmera ativa
            image = self.camera_manager.capture()
            
            # Valida se captura foi bem-sucedida
            if image is None:
                log.error("❌ Falha ao capturar imagem")
                self._notify("capture_failed", {"error": "Falha na captura"})
                return None
            
            # Prepara resultado com metadados completos
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

    def preprocess_image(self, image: np.ndarray, ops: List[Dict[str, Any]]) -> np.ndarray:
        """
        Aplica pré-processamento configurável à imagem.

        Args:
            image (np.ndarray): imagem original em BGR
            ops (List[Dict]): lista de operações (ver ImagePipeline.apply)

        Returns:
            np.ndarray: imagem processada

        Exemplo:
            ops = [{"name": "crop", "bbox": [100,50,400,300]}, {"name": "resize", "size": [256,256]}]
            out = core.preprocess_image(image, ops)
        """
        return self._image_pipeline.apply(image, ops)

    def start_periodic_capture(self, interval_seconds: float, save_dir: str, preprocess_ops: Optional[List[Dict[str, Any]]] = None):
        """
        Inicia captura periódica em background.

        Args:
            interval_seconds (float): intervalo entre capturas em segundos
            save_dir (str): diretório onde salvar imagens

        Observações:
            - Garante que a câmera esteja inicializada
            - Emite evento "periodic_capture_saved" quando um arquivo for salvo
        """
        # Garante câmera inicializada
        if not self.camera_manager:
            self._initialize_camera()

        save_path = Path(save_dir)

        # Cria função de pré-processamento a partir das ops, se fornecidas
        preprocess_fn = None
        if preprocess_ops:
            preprocess_fn = lambda img: self._image_pipeline.apply(img, preprocess_ops)

        # cria e inicia scheduler com preprocess_fn opcional
        self._capture_scheduler = CaptureScheduler(
            self.camera_manager,
            save_path,
            on_saved=lambda d: self._notify("periodic_capture_saved", d),
            preprocess_fn=preprocess_fn,
        )
        self._capture_scheduler.start(interval_seconds)

    def stop_periodic_capture(self):
        """
        Para a captura periódica se estiver em execução.
        """
        if self._capture_scheduler:
            try:
                self._capture_scheduler.stop()
            finally:
                self._capture_scheduler = None
    
    def perform_segmentation(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Executa inspeção de SEGMENTAÇÃO (detecção de defeitos).
        
        Executa o modelo YOLOv8 de segmentação que localiza e marca
        defeitos na imagem. Útil para análise visual detalhada.
        
        Args:
            image (np.ndarray):
                - Imagem em formato numpy array (H, W, 3) BGR do OpenCV
                - Dimensões: altura, largura, canais (Blue, Green, Red)
                - Tipo: uint8 (valores 0-255)
                - Por que: YOLOv8 espera este formato específico
                
        Exemplo:
            image = core.capture_image()["image"]  # (1080, 1920, 3)
            results = core.perform_segmentation(image)
            print(f"Defeitos encontrados: {results['total_defects']}")
            print(f"Há defeitos críticos: {results['has_defects']}")
            for defect in results['defects']:
                print(f"  Classe: {defect['class_name']}")
                print(f"  Confiança: {defect['confidence']:.2%}")
                print(f"  BBox: {defect['bbox']}")  # [x1, y1, x2, y2]
        
        Returns:
            Dict com estrutura:
                {
                    "defects": [
                        {
                            "bbox": [x1, y1, x2, y2],  # coordenadas pixel
                            "confidence": 0.95,  # 0.0-1.0
                            "class": 0,  # índice da classe
                            "class_name": "Trinca"  # nome legível
                        },
                        ...
                    ],
                    "has_defects": True,  # Se algum tem conf > threshold
                    "total_defects": 3,  # Quantidade total encontrada
                    "confidence_threshold": 0.5,  # Threshold usado
                    "success": True
                }
            ou com erro:
                {
                    "defects": [],
                    "has_defects": False,
                    "error": "mensagem de erro",
                    "success": False
                }
        """
        try:
            log.info("Executando segmentação...")
            # Notifica interface que começou
            self._notify("segmentation_started", {})
            
            # Valida se modelo está carregado
            if self.segmentation_model is None or self.segmentation_model.model is None:
                raise RuntimeError("Modelo de segmentação não carregado")
            
            # Executa predição (YOLOv8 retorna detecções)
            results = self.segmentation_model.predict(image)
            
            # Processa resultados brutos do modelo
            defects = []
            for result in results:
                if result.boxes is not None:
                    # Extrai cada detecção
                    for box, conf, cls in zip(result.boxes.xyxy, result.boxes.conf, result.boxes.cls):
                        defect = {
                            "bbox": box.tolist(),  # [x1, y1, x2, y2]
                            "confidence": float(conf),  # 0.95
                            "class": int(cls),  # 0, 1, 2...
                            "class_name": self.segmentation_model.model.names[int(cls)] if hasattr(self.segmentation_model.model, "names") else str(cls)
                        }
                        defects.append(defect)
            
            # Determina se há defeitos críticos (confiança > threshold)
            confidence_threshold = self.segmentation_model.config.get("confidence_threshold", 0.5)
            has_defects = any(d["confidence"] > confidence_threshold for d in defects)
            
            # Monta resultado final
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
        Executa inspeção de CLASSIFICAÇÃO (BOM ou RUIM).
        
        Executa o modelo YOLOv8 de classificação que determina se o
        produto é BOM ou RUIM. Retorna status "indeterminado" se confiança
        for abaixo do threshold (rejeitado).
        
        Args:
            image (np.ndarray):
                - Imagem em formato numpy array (H, W, 3) BGR do OpenCV
                - Dimensões: altura, largura, canais (Blue, Green, Red)
                - Tipo: uint8 (valores 0-255)
                - Por que: YOLOv8 espera este formato específico
        
        Exemplo:
            image = core.capture_image()["image"]
            result = core.perform_classification(image)
            
            if result['status'] == 'accepted':
                if result['defects_detected']:
                    print("Produto RUIM - rejeitado")
                else:
                    print("Produto BOM - aprovado")
            else:
                print(f"Indeterminado - confiança abaixo do threshold")
                print(f"Confiança: {result['confidence']:.2%}")
        
        Returns:
            Dict com estrutura:
                # Quando confiança < threshold (INDETERMINADO)
                {
                    "defects_info": [{"class": "INDETERMINADO", "status": "rejected"}],
                    "defects_detected": None,  # None = indeterminado
                    "confidence": 0.45,  # Abaixo do threshold (0.7)
                    "confidence_threshold": 0.7,
                    "status": "indeterminado",
                    "success": True
                }
                
                # Quando confiança > threshold (ACEITO)
                {
                    "defects_info": [
                        {
                            "class": "BOM",  # ou "RUIM"
                            "confidence": 0.95,
                            "class_idx": 0  # índice da classe
                        }
                    ],
                    "defects_detected": False,  # True se RUIM, False se BOM
                    "confidence": 0.95,
                    "confidence_threshold": 0.7,
                    "status": "accepted",
                    "success": True
                }
                
                # Em caso de erro
                {
                    "defects_info": [],
                    "defects_detected": None,
                    "error": "mensagem de erro",
                    "success": False
                }
        """
        try:
            log.info("Executando classificação...")
            # Notifica interface que começou
            self._notify("classification_started", {})
            
            # Valida se modelo está carregado
            if self.classification_model is None or self.classification_model.model is None:
                raise RuntimeError("Modelo de classificação não carregado")
            
            # Executa predição (YOLOv8 classificação retorna probabilidades)
            results = self.classification_model.predict(image)
            
            # Processa resultados de classificação (diferente de detecção)
            defects_info = []
            
            for result in results:
                # Classificação retorna atributo 'probs' em vez de 'boxes'
                if hasattr(result, 'probs'):
                    probs = result.probs
                    top1_idx = probs.top1  # Índice da classe com maior probabilidade
                    top1_conf = probs.top1conf.item()  # Confiança da classe vencedora
                    
                    # Obtém nome legível da classe
                    class_name = "Desconhecido"
                    if hasattr(self.classification_model.model, 'names'):
                        class_name = self.classification_model.model.names[top1_idx]
                    
                    defect = {
                        "class": class_name,  # "BOM" ou "RUIM"
                        "confidence": top1_conf,  # 0.95
                        "class_idx": int(top1_idx)  # 0 ou 1
                    }
                    defects_info.append(defect)
            
            # Verifica confiança contra threshold
            confidence_threshold = self.classification_model.config.get("confidence_threshold", 0.7)
            first_defect = defects_info[0] if defects_info else {}
            
            if first_defect.get("confidence", 0) < confidence_threshold:
                # INDETERMINADO: confiança abaixo do threshold
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
                # ACEITO: confiança suficiente
                # Determina se produto é RUIM (defeituoso)
                defects_detected = first_defect.get("class", "").upper() == "RUIM"
                
                result = {
                    "defects_info": defects_info,
                    "defects_detected": defects_detected,  # True = RUIM, False = BOM
                    "confidence": first_defect.get("confidence", 0),
                    "confidence_threshold": confidence_threshold,
                    "status": "accepted",
                    "success": True
                }
                
                # Log com status legível
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
        Salva resultados da inspeção em disco de forma organizada.
        
        Cria um diretório com timestamp, salva dados em JSON e imagem em JPEG.
        Mantém histórico dos últimos N resultados (controlado por max_history).
        
        Args:
            inspection_data (Dict):
                - Dados da inspeção a salvar
                - Pode conter "image" (numpy array - será removido e salvo separado)
                - Pode conter qualquer outro dado: "defects", "classification", etc
                - Por que: precisa conter contexto completo da inspeção
                
        Exemplo:
            inspection_data = {
                "image": numpy_array_image,  # Será removido e salvo como JPEG
                "inspection_type": "segmentation",
                "defects": [...],
                "timestamp": "2026-01-05T14:30:45",
                "camera": "basler"
            }
            saved_path = core.save_inspection(inspection_data)
            # Cria: data/results/20260105_143045/
            #       ├── inspection_data.json  (metadados)
            #       └── image.jpg (imagem capturada)
        
        Returns:
            str: Caminho do diretório criado (vazio "" se desabilitado ou erro)
        
        Lógica de salvamento:
            1. Verifica se save_results está ativado na config
            2. Cria diretório com timestamp: YYYYMMDD_HHMMSS
            3. Remove imagem dos dados (muito grande)
            4. Salva imagem como JPEG em separado
            5. Salva dados em JSON
            6. Atualiza histórico de inspeções
        """
        # Se salvamento está desabilitado na config, retorna vazio
        if not self.config.get("save_results", True):
            return ""
        
        try:
            # Cria diretório com timestamp (organiza por data/hora)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            inspection_dir = self.results_dir / timestamp
            inspection_dir.mkdir(exist_ok=True)
            
            data_file = inspection_dir / "inspection_data.json"

            # Se houver imagem binária (numpy array), salve-a primeiro e remova do dict
            if "image" in inspection_data:
                try:
                    image = inspection_data.pop("image")
                    image_file = inspection_dir / "image.jpg"
                    cv2.imwrite(str(image_file), image)
                    inspection_data["image_file"] = str(image_file.relative_to(self.results_dir))
                except Exception as e:
                    log.error(f"❌ Falha ao salvar imagem da inspeção: {e}")
                    # garante que chave image não gere problemas
                    inspection_data.pop("image", None)

            # Salva dados (sem a imagem binária) em JSON
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(inspection_data, f, indent=2, ensure_ascii=False)
            
            log.info(f" Inspeção salva em: {inspection_dir}")
            
            # Adiciona ao histórico para rastreamento
            self._inspection_history.append({
                "timestamp": timestamp,
                "path": str(inspection_dir),
                "type": inspection_data.get("inspection_type", "unknown")
            })
            
            # Mantém histórico limitado (evita crescimento infinito)
            max_history = self.config.get("max_history", 100)
            if len(self._inspection_history) > max_history:
                # Remove as mais antigas
                self._inspection_history = self._inspection_history[-max_history:]
            
            return str(inspection_dir)
            
        except Exception as e:
            log.error(f"❌ Erro ao salvar inspeção: {e}")
            return ""
    
    def register_callback(self, event: str, callback: Callable):
        """
        Registra uma função callback para ser notificada sobre um evento.
        
        Permite que interfaces (web/desktop) se registrem para receber
        notificações em tempo real quando certos eventos ocorrem.
        Sistema tipo pub/sub (publicador/subscritor).
        
        Args:
            event (str):
                - Nome do evento para registrar
                - Exemplos: "capture_started", "capture_completed", "segmentation_completed"
                - Por que: permite desacoplamento entre core e interfaces
                
            callback (Callable):
                - Função que será chamada quando evento ocorrer
                - Assinatura: callback(data: Dict) -> None
                - data contém informações específicas do evento
                - Por que: permite que interfaces reajam a eventos do core
        
        Exemplo:
            # Registra callback para quando captura terminar
            def on_capture_done(data):
                print(f"Capturado! {data['timestamp']}")
                print(f"Resolução: {data['image'].shape}")
            
            core.register_callback("capture_completed", on_capture_done)
            
            # Agora quando core.capture_image() for chamado e terminar,
            # on_capture_done será chamado automaticamente
            
            # Eventos disponíveis:
            # - capture_started: (sem dados)
            # - capture_completed: {"image", "timestamp", "camera_info", "success"}
            # - capture_failed: {"error": "mensagem"}
            # - segmentation_started: (sem dados)
            # - segmentation_completed: {"defects", "has_defects", ...}
            # - segmentation_failed: {"error"}
            # - classification_started: (sem dados)
            # - classification_completed: {"defects_info", "defects_detected", ...}
            # - classification_failed: {"error"}
        """
        # Cria lista de callbacks para evento se não existir
        if event not in self._callbacks:
            self._callbacks[event] = []
        
        # Adiciona callback à lista
        self._callbacks[event].append(callback)
        log.debug(f" Callback registrado para evento: {event}")
    
    def _notify(self, event: str, data: Any):
        """
        Notifica todos os callbacks registrados para um evento específico.
        
        Método PRIVADO (começa com _) usado internamente pelo SystemCore
        para disparar notificações aos subscribers.
        
        Args:
            event (str):
                - Nome do evento que ocorreu
                - Por que: precisa saber qual evento disparou
                
            data (Any):
                - Dados a serem passados aos callbacks
                - Geralmente um Dict com informações do evento
                - Por que: callbacks precisam dos detalhes do que aconteceu
        
        Exemplo (uso interno):
            self._notify("capture_completed", {
                "image": img,
                "timestamp": "2026-01-05T14:30:45",
                "camera_info": {...},
                "success": True
            })
        
        Segurança:
            - Se um callback lançar exceção, o erro é logado mas não
              interrompe callbacks restantes (falha gracioso)
        """
        # Verifica se há callbacks registrados para este evento
        if event in self._callbacks:
            # Chama cada callback registrado
            for callback in self._callbacks[event]:
                try:
                    # Chama callback com os dados
                    callback(data)
                except Exception as e:
                    # Não deixa callback com erro derrubar o sistema
                    log.error(f"❌ Erro em callback do evento {event}: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Retorna informações completas do sistema para diagnóstico.
        
        Coleta dados de todas as partes do sistema (câmera, modelos, etc)
        em um único dicionário, útil para status/debug/interface.
        
        Returns:
            Dict com estrutura:
                {
                    "system": {
                        "initialized": True,  # Se tudo inicializou
                        "results_dir": "/path/to/data/results",
                        "inspection_history_count": 5  # Quantas inspeções salvas
                    },
                    "camera": {
                        "type": "basler",  # Tipo da câmera ativa
                        "ip": "192.168.1.100",
                        "status": "connected",
                        ... (outras info da câmera)
                    },
                    "models": {
                        "segmentation": {
                            "loaded": True,
                            "model_path": "/path/to/model.pt",
                            ... (outras info do modelo)
                        },
                        "classification": {
                            "loaded": True,
                            "model_path": "/path/to/model.pt",
                            ... (outras info do modelo)
                        }
                    },
                    "config": {
                        "save_results": True,
                        "max_history": 100,
                        ... (todas as configs)
                    }
                }
        
        Exemplo:
            info = core.get_system_info()
            print(f"Câmera ativa: {info['camera']['type']}")
            print(f"Modelos carregados: {info['models']['segmentation']['loaded']}")
            print(f"Total inspeções: {info['system']['inspection_history_count']}")
        """
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
        """
        Libera todos os recursos ocupados pelo sistema.
        
        DEVE SER CHAMADO AO ENCERRAR O APLICATIVO para evitar
        memory leaks e deixar câmeras e GPU em estado limpo.
        
        Ações:
        1. Libera câmera (fecha conexão)
        2. Descarrega modelos da GPU (libera VRAM)
        3. Log de conclusão
        
        Exemplo:
            try:
                core = SystemCore()
                core.initialize()
                # ... usar o core ...
            finally:
                core.cleanup()  # Sempre chamar, mesmo em erro
            
            # Melhor ainda, usar context manager (não implementado aqui)
            # with SystemCore() as core:
            #     core.initialize()
            #     # ... usar ...
            # # cleanup automático ao sair do with
        """
        log.info("Limpando recursos do SystemCore...")
        
        # Libera câmera
        if self.camera_manager:
            self.camera_manager.release()
        
        # Descarrega modelos (libera GPU/VRAM)
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