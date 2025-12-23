"""
LAUNCHER PRINCIPAL - Ponto de entrada do sistema híbrido.

Este arquivo decide como iniciar o sistema:
- Modo Desktop (GUI)
- Modo Web (servidor)
- Modo Híbrido (ambos)
- Modo Auto (detecta automaticamente)

Uso:
    python launcher.py                    # Modo automático
    python launcher.py --mode desktop     # Apenas desktop
    python launcher.py --mode web         # Apenas web
    python launcher.py --mode both        # Ambos
    python launcher.py --help             # Ajuda
"""

import sys
import os
import argparse
import signal
import threading
import time
from pathlib import Path
import webbrowser

# Adiciona o diretório atual ao path para imports
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Verifica se as dependências mínimas estão instaladas"""
    missing_deps = []
    
    try:
        import fastapi
    except ImportError:
        missing_deps.append("fastapi")
    
    try:
        import ultralytics
    except ImportError:
        missing_deps.append("ultralytics")
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import torch
    except ImportError:
        missing_deps.append("torch")
    
    if missing_deps:
        print(f"❌ Dependências faltando: {', '.join(missing_deps)}")
        print("\nInstale com:")
        print("  pip install " + " ".join(missing_deps))
        print("\nOu execute: python install_deps.py")
        return False
    
    return True

def parse_arguments():
    """Parse os argumentos de linha de comando"""
    parser = argparse.ArgumentParser(
        description="Sistema Híbrido de Inspeção por Visão Computacional",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s                    # Modo automático (recomendado)
  %(prog)s --mode desktop     # Interface gráfica apenas
  %(prog)s --mode web         # Servidor web apenas
  %(prog)s --mode both        # Ambos (desktop + web)
  %(prog)s --port 8080        # Servidor web na porta 8080
  %(prog)s --no-browser       # Não abrir navegador automaticamente
  %(prog)s --debug            # Modo debug (mais logs)
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["auto", "desktop", "web", "both", "cli"],
        default="auto",
        help="Modo de execução (padrão: auto)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Porta para servidor web (padrão: 8000)"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host para servidor web (padrão: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Não abrir navegador automaticamente"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Modo debug (logs detalhados)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Caminho do arquivo de configuração"
    )
    
    return parser.parse_args()

def setup_logging(debug=False):
    """Configura o sistema de logging"""
    import logging
    
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Configura logging básico
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("system.log"),
            logging.StreamHandler()
        ]
    )
    
    # Reduz verbosidade de algumas bibliotecas
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

def run_web_server(core, host, port, open_browser=True):
    """Inicia o servidor web em uma thread separada"""
    
    def start_server():
        try:
            from interfaces.web.server import start_web_server
            start_web_server(core)
        except ImportError as e:
            print(f"❌ Erro ao importar módulo web: {e}")
            print("  Certifique-se de que fastapi e uvicorn estão instalados")
            print("  pip install fastapi uvicorn")
            return False
        except Exception as e:
            print(f"❌ Erro no servidor web: {e}")
            return False
    
    # Inicia servidor em thread separada
    web_thread = threading.Thread(target=start_server, daemon=True)
    web_thread.start()
    
    # Aguarda um pouco para o servidor iniciar
    time.sleep(2)
    
    # Abre navegador se solicitado
    if open_browser:
        try:
            url = f"http://localhost:{port}"
            print(f"🌐 Abrindo navegador em: {url}")
            webbrowser.open(url)
        except:
            print(f"📡 Servidor web em: http://{host}:{port}")
    
    return web_thread

def run_desktop_app(core):
    """Inicia a aplicação desktop"""
    try:
        # Verifica se PyQt5 está disponível
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            print("❌ PyQt5 não encontrado.")
            print("   Instale com: pip install PyQt5")
            print("   Ou execute no modo web: python launcher.py --mode web")
            return False
        
        from interfaces.desktop.app import start_desktop_app
        
        # Inicia aplicação Qt
        app = QApplication(sys.argv)
        start_desktop_app(core)
        
        # Executa loop principal
        return app.exec_()
        
    except ImportError as e:
        print(f"❌ Erro ao importar módulo desktop: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro na aplicação desktop: {e}")
        return False

def detect_best_mode():
    """Detecta o melhor modo de execução baseado no ambiente"""
    
    # Verifica se estamos em terminal com GUI disponível
    has_display = False
    
    if sys.platform == "win32":
        # Windows sempre tem display (a menos que seja servidor)
        has_display = True
    elif "DISPLAY" in os.environ:
        # Linux/Unix com X11
        has_display = True
    elif sys.platform == "darwin":
        # macOS
        has_display = True
    
    # Verifica se tem interface gráfica disponível
    if has_display:
        try:
            from PyQt5.QtWidgets import QApplication
            # Cria QApplication temporário para teste
            app = QApplication.instance()
            if not app:
                app = QApplication([])
            app.quit()
            return "both"  # Tem GUI, pode usar ambos
        except:
            return "web"  # Não tem PyQt5, usa apenas web
    
    return "web"  # Sem display, apenas web

def signal_handler(signum, frame):
    """Manipula sinais de interrupção (Ctrl+C)"""
    print("\n🛑 Recebido sinal de interrupção. Desligando...")
    sys.exit(0)

def main():
    """Função principal"""
    
    # Registra handler para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print("\n" + "="*60)
    print("🚀 SISTEMA HÍBRIDO DE INSPEÇÃO POR VISÃO COMPUTACIONAL")
    print("="*60)
    
    # Parse argumentos
    args = parse_arguments()
    
    # Configura logging
    logger = setup_logging(args.debug)
    
    # Verifica dependências
    if not check_dependencies():
        return 1
    
    # Cria diretórios necessários
    for dir_name in ["models", "logs", "data", "assets"]:
        Path(dir_name).mkdir(exist_ok=True)
    
    # Determina modo de execução
    mode = args.mode
    if mode == "auto":
        mode = detect_best_mode()
        print(f"🔍 Modo automático selecionado: {mode}")
    
    print(f"🎮 Modo de execução: {mode}")
    print(f"📡 Host: {args.host}, Porta: {args.port}")
    
    # Inicializa o core do sistema
    try:
        from core.system_core import SystemCore
        
        print("\n🔄 Inicializando núcleo do sistema...")
        core = SystemCore()
        
        if not core.initialize():
            print("❌ Falha ao inicializar o sistema.")
            print("   Verifique se a câmera está conectada e os modelos existem.")
            return 1
        
        # Obtém informações do sistema
        info = core.get_system_info()
        camera_type = info.get("camera", {}).get("type", "N/A")
        print(f"✅ Sistema inicializado. Câmera: {camera_type}")
        
    except Exception as e:
        print(f"❌ Erro crítico ao inicializar sistema: {e}")
        return 1
    
    # Executa no modo selecionado
    try:
        if mode == "web":
            print("\n🌐 Iniciando apenas servidor web...")
            run_web_server(core, args.host, args.port, not args.no_browser)
            
            # Mantém o programa rodando
            print("\n📡 Servidor web rodando. Pressione Ctrl+C para sair.")
            # signal.pause() não funciona no Windows, usar time.sleep em loop
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            
        elif mode == "desktop":
            print("\n🖥️  Iniciando apenas interface desktop...")
            return run_desktop_app(core)
            
        elif mode == "both":
            print("\n🔄 Iniciando modo híbrido (desktop + web)...")
            
            # Inicia servidor web em background
            web_thread = run_web_server(core, args.host, args.port, not args.no_browser)
            
            # Inicia desktop (bloqueante)
            print("\n🖥️  Iniciando interface desktop...")
            return run_desktop_app(core)
            
        elif mode == "cli":
            print("\n💻 Modo linha de comando ativado.")
            print("Comandos disponíveis:")
            print("  capture    - Captura uma imagem")
            print("  classify   - Executa classificação")
            print("  segment    - Executa segmentação")
            print("  exit       - Sair")
            print()
            
            # Loop de comandos simples
            while True:
                try:
                    cmd = input("> ").strip().lower()
                    
                    if cmd == "exit" or cmd == "quit":
                        break
                    elif cmd == "capture":
                        result = core.capture_image()
                        if result:
                            print(f"✅ Imagem capturada: {result.get('image', {}).shape}")
                    elif cmd == "classify":
                        result = core.capture_image()
                        if result:
                            classification = core.perform_classification(result["image"])
                            print(f"Classificação: {classification}")
                    elif cmd == "segment":
                        result = core.capture_image()
                        if result:
                            segmentation = core.perform_segmentation(result["image"])
                            print(f"Segmentação: {segmentation}")
                    elif cmd == "help":
                        print("Comandos: capture, classify, segment, exit")
                    else:
                        print(f"Comando desconhecido: {cmd}")
                        
                except KeyboardInterrupt:
                    print("\nSaindo...")
                    break
                except Exception as e:
                    print(f"Erro: {e}")
        
        else:
            print(f"❌ Modo desconhecido: {mode}")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        return 1
    finally:
        # Limpeza
        print("\n🧹 Limpando recursos...")
        try:
            core.cleanup()
        except:
            pass
    
    print("\n👋 Sistema encerrado.")
    return 0

if __name__ == "__main__":
    sys.exit(main())