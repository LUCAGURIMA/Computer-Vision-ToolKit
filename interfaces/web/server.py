"""
Servidor web FastAPI.

Esta é a interface web do sistema.
Ela:
1. Cria endpoints REST API
2. Serve arquivos estáticos (HTML, CSS, JS)
3. Comunica com o SystemCore
4. Gerencia WebSocket para atualizações em tempo real
"""

import json
from pathlib import Path
from typing import Dict, Any
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.system_core import SystemCore
from core.utils.logger import log
from config import WEB_CONFIG, BASE_DIR

class WebServer:
    """
    Servidor web FastAPI.
    
    Design Pattern: Adapter Pattern
    - Adapta o SystemCore para uma interface web
    - Traduz chamadas HTTP para chamadas do core
    """
    
    def __init__(self, core: SystemCore, host: str = None, port: int = None):
        """
        Inicializa o servidor web.
        
        Args:
            core: Instância do SystemCore
            host: Host para escutar
            port: Porta para escutar
        """
        self.core = core
        self.host = host or WEB_CONFIG["host"]
        self.port = port or WEB_CONFIG["port"]
        
        # Cria app FastAPI
        self.app = FastAPI(title="Sistema de Inspeção", version="1.0.0")
        
        # Configura CORS (permite acesso de qualquer origem)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=WEB_CONFIG["cors_origins"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Clientes WebSocket conectados
        self.websocket_clients = []
        
        # Configura rotas
        self._setup_routes()
        
        # Configura diretório estático
        self._setup_static_files()
        
        # Registra callbacks no core para notificações
        self._register_core_callbacks()
        
        log.info(f"🌐 WebServer criado: http://{self.host}:{self.port}")
    
    def _setup_static_files(self):
        """Configura servidor de arquivos estáticos"""
        static_dir = BASE_DIR / "interfaces" / "web" / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        
        self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
        log.info(f"📁 Diretório estático: {static_dir}")
        
        # Se não existir, cria página HTML básica
        index_file = static_dir / "index.html"
        if not index_file.exists():
            self._create_default_index(index_file)
    
    def _create_default_index(self, file_path: Path):
        """Cria página HTML padrão se não existir"""
        html_content = """
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Sistema de Inspeção</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }
                .status {
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 5px;
                    background: #e8f5e9;
                    border-left: 4px solid #4CAF50;
                }
                .btn {
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    font-size: 16px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin: 5px;
                    transition: background 0.3s;
                }
                .btn:hover {
                    background: #45a049;
                }
                .btn:disabled {
                    background: #cccccc;
                    cursor: not-allowed;
                }
                .result {
                    margin-top: 20px;
                    padding: 15px;
                    background: #f9f9f9;
                    border-radius: 5px;
                    min-height: 100px;
                }
                .log {
                    margin-top: 20px;
                    padding: 10px;
                    background: #333;
                    color: #fff;
                    border-radius: 5px;
                    font-family: monospace;
                    max-height: 200px;
                    overflow-y: auto;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Sistema de Inspeção Híbrido</h1>
                
                <div class="status" id="status">
                    Sistema web inicializado. Use os botões abaixo.
                </div>
                
                <div>
                    <button class="btn" onclick="captureImage()">📸 Capturar Imagem</button>
                    <button class="btn" onclick="segmentImage()">🔍 Segmentação</button>
                    <button class="btn" onclick="classifyImage()">🏷️ Classificação</button>
                </div>
                
                <div class="result" id="result">
                    Resultados aparecerão aqui...
                </div>
                
                <div class="log" id="log">
                    Log de eventos...
                </div>
            </div>
            
            <script>
                function logMessage(message) {
                    const logDiv = document.getElementById('log');
                    logDiv.innerHTML += '> ' + message + '\\n';
                    logDiv.scrollTop = logDiv.scrollHeight;
                }
                
                async function captureImage() {
                    logMessage('Capturando imagem...');
                    try {
                        const response = await fetch('/api/capture', { method: 'POST' });
                        const data = await response.json();
                        logMessage(`✅ Imagem capturada: ${data.image.shape}`);
                        document.getElementById('result').innerHTML = 
                            `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    } catch (error) {
                        logMessage(`❌ Erro: ${error}`);
                    }
                }
                
                async function segmentImage() {
                    logMessage('Executando segmentação...');
                    // Implementar
                    logMessage('Segmentação não implementada nesta demo');
                }
                
                async function classifyImage() {
                    logMessage('Executando classificação...');
                    try {
                        const response = await fetch('/api/classify', { method: 'POST' });
                        const data = await response.json();
                        logMessage(`✅ Classificação: ${data.status}`);
                        document.getElementById('result').innerHTML = 
                            `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    } catch (error) {
                        logMessage(`❌ Erro: ${error}`);
                    }
                }
                
                // Conecta ao WebSocket para atualizações em tempo real
                const ws = new WebSocket(`ws://${window.location.host}/ws`);
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    logMessage(`📢 ${data.event}: ${JSON.stringify(data.data)}`);
                };
                
                ws.onopen = function() {
                    logMessage('🔌 Conectado ao servidor (WebSocket)');
                };
                
                // Inicialização
                logMessage('🔄 Página carregada. Conectando ao sistema...');
                
                // Verifica status do sistema
                fetch('/api/status')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('status').innerHTML = 
                            `Sistema conectado. Câmera: ${data.camera.type}`;
                        logMessage('✅ Sistema pronto para uso');
                    })
                    .catch(err => {
                        logMessage(`❌ Erro ao conectar: ${err}`);
                    });
            </script>
        </body>
        </html>
        """
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        log.info(f"📄 Página HTML padrão criada: {file_path}")
    
    def _setup_routes(self):
        """Configura todas as rotas da API"""
        
        @self.app.get("/")
        async def home():
            """Página inicial"""
            return FileResponse(BASE_DIR / "interfaces" / "web" / "static" / "index.html")
        
        @self.app.get("/api/status")
        async def get_status():
            """Retorna status do sistema"""
            try:
                info = self.core.get_system_info()
                return JSONResponse(content={
                    "status": "online",
                    "system": info["system"],
                    "camera": info["camera"],
                    "models": {
                        "segmentation_loaded": info["models"]["segmentation"].get("loaded", False),
                        "classification_loaded": info["models"]["classification"].get("loaded", False)
                    },
                    "timestamp": asyncio.get_event_loop().time()
                })
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/capture")
        async def capture_image():
            """Captura uma imagem"""
            try:
                result = self.core.capture_image()
                if result and result.get("success"):
                    # Remove imagem binária da resposta JSON
                    response = result.copy()
                    if "image" in response:
                        response["image"] = f"Shape: {response['image'].shape}"
                    
                    return JSONResponse(content=response)
                else:
                    raise HTTPException(status_code=500, detail="Falha na captura")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/classify")
        async def classify_image():
            """Executa classificação"""
            try:
                # Primeiro captura imagem
                capture_result = self.core.capture_image()
                if not capture_result or not capture_result.get("success"):
                    raise HTTPException(status_code=500, detail="Falha na captura")
                
                # Executa classificação
                image = capture_result["image"]
                classification_result = self.core.perform_classification(image)
                
                # Prepara resposta
                response = {
                    "capture": {
                        "success": capture_result["success"],
                        "timestamp": capture_result["timestamp"],
                        "camera_info": capture_result["camera_info"]
                    },
                    "classification": classification_result,
                    "success": classification_result.get("success", False)
                }
                
                # Salva inspeção
                if classification_result.get("success"):
                    inspection_data = {
                        "inspection_type": "classification",
                        "timestamp": capture_result["timestamp"],
                        "image": image,
                        "results": classification_result
                    }
                    saved_path = self.core.save_inspection(inspection_data)
                    response["saved_path"] = saved_path
                
                return JSONResponse(content=response)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/segment")
        async def segment_image():
            """Executa segmentação"""
            try:
                # Captura imagem
                capture_result = self.core.capture_image()
                if not capture_result or not capture_result.get("success"):
                    raise HTTPException(status_code=500, detail="Falha na captura")
                
                # Executa segmentação
                image = capture_result["image"]
                segmentation_result = self.core.perform_segmentation(image)
                
                # Prepara resposta
                response = {
                    "capture": {
                        "success": capture_result["success"],
                        "timestamp": capture_result["timestamp"],
                        "camera_info": capture_result["camera_info"]
                    },
                    "segmentation": segmentation_result,
                    "success": segmentation_result.get("success", False)
                }
                
                # Salva inspeção
                if segmentation_result.get("success"):
                    inspection_data = {
                        "inspection_type": "segmentation",
                        "timestamp": capture_result["timestamp"],
                        "image": image,
                        "results": segmentation_result
                    }
                    saved_path = self.core.save_inspection(inspection_data)
                    response["saved_path"] = saved_path
                
                return JSONResponse(content=response)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Endpoint WebSocket para comunicação em tempo real"""
            await websocket.accept()
            self.websocket_clients.append(websocket)
            
            try:
                # Envia mensagem de boas-vindas
                await websocket.send_json({
                    "event": "connected",
                    "data": {"message": "Conectado ao sistema"}
                })
                
                # Mantém conexão aberta
                while True:
                    # Aguarda mensagens do cliente (se necessário)
                    data = await websocket.receive_text()
                    log.debug(f"📨 Mensagem WebSocket: {data}")
                    
                    # Poderia processar comandos aqui
                    # Por enquanto, só ecoa de volta
                    await websocket.send_json({
                        "event": "echo",
                        "data": {"received": data}
                    })
                    
            except WebSocketDisconnect:
                # Cliente desconectou
                self.websocket_clients.remove(websocket)
                log.info("🔌 Cliente WebSocket desconectado")
            except Exception as e:
                log.error(f"❌ Erro no WebSocket: {e}")
                if websocket in self.websocket_clients:
                    self.websocket_clients.remove(websocket)
    
    def _register_core_callbacks(self):
        """Registra callbacks no core para notificar clientes WebSocket"""
        
        async def notify_websockets(event: str, data: Dict[str, Any]):
            """Notifica todos os clientes WebSocket sobre um evento"""
            message = {
                "event": event,
                "data": data,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Remove dados binários grandes
            if "image" in data:
                data["image"] = f"Shape: {data['image'].shape}"
            
            # Envia para todos os clientes conectados
            for client in self.websocket_clients:
                try:
                    await client.send_json(message)
                except Exception as e:
                    log.error(f"❌ Erro ao enviar para WebSocket: {e}")
        
        # Registra eventos importantes
        self.core.register_callback("capture_completed", 
                                   lambda data: asyncio.create_task(notify_websockets("capture_completed", data)))
        self.core.register_callback("classification_completed",
                                   lambda data: asyncio.create_task(notify_websockets("classification_completed", data)))
        self.core.register_callback("segmentation_completed",
                                   lambda data: asyncio.create_task(notify_websockets("segmentation_completed", data)))
    
    def start(self):
        """Inicia o servidor web"""
        log.info(f"🚀 Iniciando servidor web em http://{self.host}:{self.port}")
        log.info(f"📁 Interface web: http://{self.host}:{self.port}/")
        log.info(f"📡 API REST: http://{self.host}:{self.port}/api/status")
        log.info(f"🔌 WebSocket: ws://{self.host}:{self.port}/ws")
        
        # Desabilita reload para evitar warnings - use aplicação instanciada
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            reload=False,  # Desabilita reload para evitar warnings
            log_level="warning"  # Reduz verbosidade
        )

# Função para iniciar apenas o servidor web
def start_web_server(core: SystemCore = None):
    """Função conveniente para iniciar servidor web"""
    if core is None:
        core = SystemCore()
        core.initialize()
    
    server = WebServer(core)
    server.start()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🧪 TESTE DO SERVIDOR WEB")
    print("="*50)
    
    # Cria core fake para teste
    class MockCore:
        def get_system_info(self):
            return {
                "system": {"initialized": True},
                "camera": {"type": "mock", "status": "ok"},
                "models": {
                    "segmentation": {"loaded": True},
                    "classification": {"loaded": True}
                }
            }
        
        def capture_image(self):
            return {
                "success": True,
                "timestamp": "2024-01-01T12:00:00",
                "camera_info": {"type": "mock"},
                "image": "fake_image"
            }
        
        def register_callback(self, event, callback):
            pass
    
    print("⚠️  Este é um teste básico. Para testar completo:")
    print("1. Execute: python launcher.py --mode=web")
    print("2. Acesse: http://localhost:8000")
    print("\n" + "="*50)