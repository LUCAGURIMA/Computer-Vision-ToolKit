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

    def __init__(self, core: SystemCore, host: str=None, port: int=None):
        self.core = core
        self.host = host or WEB_CONFIG['host']
        self.port = port or WEB_CONFIG['port']
        self.app = FastAPI(title='Sistema de Inspeção', version='1.0.0')
        self.app.add_middleware(CORSMiddleware, allow_origins=WEB_CONFIG['cors_origins'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
        self.websocket_clients = []
        self._setup_routes()
        self._setup_static_files()
        self._register_core_callbacks()
        log.info(f'WebServer criado: http://{self.host}:{self.port}')

    def _setup_static_files(self):
        static_dir = BASE_DIR / 'interfaces' / 'web' / 'static'
        static_dir.mkdir(parents=True, exist_ok=True)
        self.app.mount('/static', StaticFiles(directory=static_dir), name='static')
        log.info(f'Diretório estático: {static_dir}')
        index_file = static_dir / 'index.html'
        if not index_file.exists():
            self._create_default_index(index_file)

    def _create_default_index(self, file_path: Path):
        html_content = '\n\n        <!DOCTYPE html>\n\n        <html lang="pt-BR">\n\n        <head>\n\n            <meta charset="UTF-8">\n\n            <meta name="viewport" content="width=device-width, initial-scale=1.0">\n\n            <title>Sistema de Inspeção</title>\n\n            <style>\n\n                body {\n\n                    font-family: Arial, sans-serif;\n\n                    max-width: 800px;\n\n                    margin: 0 auto;\n\n                    padding: 20px;\n\n                    background: #f5f5f5;\n\n                }\n\n                .container {\n\n                    background: white;\n\n                    padding: 30px;\n\n                    border-radius: 10px;\n\n                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);\n\n                }\n\n                h1 {\n\n                    color: #333;\n\n                    border-bottom: 2px solid #4CAF50;\n\n                    padding-bottom: 10px;\n\n                }\n\n                .status {\n\n                    padding: 15px;\n\n                    margin: 15px 0;\n\n                    border-radius: 5px;\n\n                    background: #e8f5e9;\n\n                    border-left: 4px solid #4CAF50;\n\n                }\n\n                .btn {\n\n                    background: #4CAF50;\n\n                    color: white;\n\n                    border: none;\n\n                    padding: 12px 24px;\n\n                    font-size: 16px;\n\n                    border-radius: 5px;\n\n                    cursor: pointer;\n\n                    margin: 5px;\n\n                    transition: background 0.3s;\n\n                }\n\n                .btn:hover {\n\n                    background: #45a049;\n\n                }\n\n                .btn:disabled {\n\n                    background: #cccccc;\n\n                    cursor: not-allowed;\n\n                }\n\n                .result {\n\n                    margin-top: 20px;\n\n                    padding: 15px;\n\n                    background: #f9f9f9;\n\n                    border-radius: 5px;\n\n                    min-height: 100px;\n\n                }\n\n                .log {\n\n                    margin-top: 20px;\n\n                    padding: 10px;\n\n                    background: #333;\n\n                    color: #fff;\n\n                    border-radius: 5px;\n\n                    font-family: monospace;\n\n                    max-height: 200px;\n\n                    overflow-y: auto;\n\n                }\n\n            </style>\n\n        </head>\n\n        <body>\n\n            <div class="container">\n\n                <h1> Sistema de Inspeção Híbrido</h1>\n\n                \n\n                <div class="status" id="status">\n\n                    Sistema web inicializado. Use os botões abaixo.\n\n                </div>\n\n                \n\n                <div>\n\n                    <button class="btn" onclick="captureImage()">Capturar Imagem</button>\n\n                    <button class="btn" onclick="segmentImage()">Segmentação</button>\n\n                    <button class="btn" onclick="classifyImage()">Classificação</button>\n\n                </div>\n\n                \n\n                <div class="result" id="result">\n\n                    Resultados aparecerão aqui...\n\n                </div>\n\n                \n\n                <div class="log" id="log">\n\n                    Log de eventos...\n\n                </div>\n\n            </div>\n\n            \n\n            <script>\n\n                function logMessage(message) {\n\n                    const logDiv = document.getElementById(\'log\');\n\n                    logDiv.innerHTML += \'> \' + message + \'\\n\';\n\n                    logDiv.scrollTop = logDiv.scrollHeight;\n\n                }\n\n                \n\n                async function captureImage() {\n\n                    logMessage(\'Capturando imagem...\');\n\n                    try {\n\n                        const response = await fetch(\'/api/capture\', { method: \'POST\' });\n\n                        const data = await response.json();\n\n                        logMessage(` Imagem capturada: ${data.image.shape}`);\n\n                        document.getElementById(\'result\').innerHTML = \n\n                            `<pre>${JSON.stringify(data, null, 2)}</pre>`;\n\n                    } catch (error) {\n\n                        logMessage(` Erro: ${error}`);\n\n                    }\n\n                }\n\n                \n\n                async function segmentImage() {\n\n                    logMessage(\'Executando segmentação...\');\n\n                    // Implementar\n\n                    logMessage(\'Segmentação não implementada nesta demo\');\n\n                }\n\n                \n\n                async function classifyImage() {\n\n                    logMessage(\'Executando classificação...\');\n\n                    try {\n\n                        const response = await fetch(\'/api/classify\', { method: \'POST\' });\n\n                        const data = await response.json();\n\n                        logMessage(` Classificação: ${data.status}`);\n\n                        document.getElementById(\'result\').innerHTML = \n\n                            `<pre>${JSON.stringify(data, null, 2)}</pre>`;\n\n                    } catch (error) {\n\n                        logMessage(` Erro: ${error}`);\n\n                    }\n\n                }\n\n                \n\n                // Conecta ao WebSocket para atualizações em tempo real\n\n                const ws = new WebSocket(`ws://${window.location.host}/ws`);\n\n                \n\n                ws.onmessage = function(event) {\n\n                    const data = JSON.parse(event.data);\n\n                    logMessage(`${data.event}: ${JSON.stringify(data.data)}`);\n\n                };\n\n                \n\n                ws.onopen = function() {\n\n                    logMessage(\'Conectado ao servidor (WebSocket)\');\n\n                };\n\n                \n\n                // Inicialização\n\n                logMessage(\' Página carregada. Conectando ao sistema...\');\n\n                \n\n                // Verifica status do sistema\n\n                fetch(\'/api/status\')\n\n                    .then(r => r.json())\n\n                    .then(data => {\n\n                        document.getElementById(\'status\').innerHTML = \n\n                            `Sistema conectado. Câmera: ${data.camera.type}`;\n\n                        logMessage(\' Sistema pronto para uso\');\n\n                    })\n\n                    .catch(err => {\n\n                        logMessage(` Erro ao conectar: ${err}`);\n\n                    });\n\n            </script>\n\n        </body>\n\n        </html>\n\n        '
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log.info(f' Página HTML padrão criada: {file_path}')

    def _setup_routes(self):

        @self.app.get('/')
        async def home():
            return FileResponse(BASE_DIR / 'interfaces' / 'web' / 'static' / 'index.html')

        @self.app.get('/api/status')
        async def get_status():
            try:
                info = self.core.get_system_info()
                return JSONResponse(content={'status': 'online', 'system': info['system'], 'camera': info['camera'], 'models': {'segmentation_loaded': info['models']['segmentation'].get('loaded', False), 'classification_loaded': info['models']['classification'].get('loaded', False)}, 'timestamp': asyncio.get_event_loop().time()})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post('/api/capture')
        async def capture_image():
            try:
                result = self.core.capture_image()
                if result and result.get('success'):
                    response = result.copy()
                    if 'image' in response:
                        response['image'] = f"Shape: {response['image'].shape}"
                    return JSONResponse(content=response)
                else:
                    raise HTTPException(status_code=500, detail='Falha na captura')
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post('/api/classify')
        async def classify_image():
            try:
                capture_result = self.core.capture_image()
                if not capture_result or not capture_result.get('success'):
                    raise HTTPException(status_code=500, detail='Falha na captura')
                image = capture_result['image']
                classification_result = self.core.perform_classification(image)
                response = {'capture': {'success': capture_result['success'], 'timestamp': capture_result['timestamp'], 'camera_info': capture_result['camera_info']}, 'classification': classification_result, 'success': classification_result.get('success', False)}
                if classification_result.get('success'):
                    inspection_data = {'inspection_type': 'classification', 'timestamp': capture_result['timestamp'], 'image': image, 'results': classification_result}
                    saved_path = self.core.save_inspection(inspection_data)
                    response['saved_path'] = saved_path
                return JSONResponse(content=response)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post('/api/segment')
        async def segment_image():
            try:
                capture_result = self.core.capture_image()
                if not capture_result or not capture_result.get('success'):
                    raise HTTPException(status_code=500, detail='Falha na captura')
                image = capture_result['image']
                segmentation_result = self.core.perform_segmentation(image)
                response = {'capture': {'success': capture_result['success'], 'timestamp': capture_result['timestamp'], 'camera_info': capture_result['camera_info']}, 'segmentation': segmentation_result, 'success': segmentation_result.get('success', False)}
                if segmentation_result.get('success'):
                    inspection_data = {'inspection_type': 'segmentation', 'timestamp': capture_result['timestamp'], 'image': image, 'results': segmentation_result}
                    saved_path = self.core.save_inspection(inspection_data)
                    response['saved_path'] = saved_path
                return JSONResponse(content=response)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.websocket('/ws')
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_clients.append(websocket)
            try:
                await websocket.send_json({'event': 'connected', 'data': {'message': 'Conectado ao sistema'}})
                while True:
                    data = await websocket.receive_text()
                    log.debug(f' Mensagem WebSocket: {data}')
                    await websocket.send_json({'event': 'echo', 'data': {'received': data}})
            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
                log.info(' Cliente WebSocket desconectado')
            except Exception as e:
                log.error(f' Erro no WebSocket: {e}')
                if websocket in self.websocket_clients:
                    self.websocket_clients.remove(websocket)

    def _register_core_callbacks(self):

        async def notify_websockets(event: str, data: Dict[str, Any]):
            message = {'event': event, 'data': data, 'timestamp': asyncio.get_event_loop().time()}
            if 'image' in data:
                data['image'] = f"Shape: {data['image'].shape}"
            for client in self.websocket_clients:
                try:
                    await client.send_json(message)
                except Exception as e:
                    log.error(f' Erro ao enviar para WebSocket: {e}')
        self.core.register_callback('capture_completed', lambda data: asyncio.create_task(notify_websockets('capture_completed', data)))
        self.core.register_callback('classification_completed', lambda data: asyncio.create_task(notify_websockets('classification_completed', data)))
        self.core.register_callback('segmentation_completed', lambda data: asyncio.create_task(notify_websockets('segmentation_completed', data)))

    def start(self):
        log.info(f'Iniciando servidor web em http://{self.host}:{self.port}')
        log.info(f'Interface web: http://{self.host}:{self.port}/')
        log.info(f'API REST: http://{self.host}:{self.port}/api/status')
        log.info(f'WebSocket: ws://{self.host}:{self.port}/ws')
        uvicorn.run(self.app, host=self.host, port=self.port, reload=False, log_level='warning')

def start_web_server(core: SystemCore=None):
    if core is None:
        core = SystemCore()
        core.initialize()
    server = WebServer(core)
    server.start()
if __name__ == '__main__':
    print('\n' + '=' * 50)
    print(' TESTE DO SERVIDOR WEB')
    print('=' * 50)

    class MockCore:

        def get_system_info(self):
            return {'system': {'initialized': True}, 'camera': {'type': 'mock', 'status': 'ok'}, 'models': {'segmentation': {'loaded': True}, 'classification': {'loaded': True}}}

        def capture_image(self):
            return {'success': True, 'timestamp': '2024-01-01T12:00:00', 'camera_info': {'type': 'mock'}, 'image': 'fake_image'}

        def register_callback(self, event, callback):
            pass
    print('  Este é um teste básico. Para testar completo:')
    print('1. Execute: python launcher.py --mode=web')
    print('2. Acesse: http://localhost:8000')
    print('\n' + '=' * 50)