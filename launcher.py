import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import os
import argparse
import signal
import threading
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    missing_deps = []
    try:
        import ultralytics
    except ImportError:
        missing_deps.append('ultralytics')
    try:
        import cv2
    except ImportError:
        missing_deps.append('opencv-python')
    try:
        import torch
    except ImportError:
        missing_deps.append('torch')
    if missing_deps:
        print(f" Dependências faltando: {', '.join(missing_deps)}")
        print('\nInstale com:')
        print('  pip install ' + ' '.join(missing_deps))
        print('\nOu execute: python install_deps.py')
        return False
    return True

def parse_arguments():
    parser = argparse.ArgumentParser(description='Sistema de Inspeção por Visão Computacional', formatter_class=argparse.RawDescriptionHelpFormatter, epilog='\n\nExemplos:\n\n  %(prog)s                    # Executa em modo desktop\n\n  %(prog)s --debug            # Modo debug (mais logs)\n\n        ')
    parser.add_argument('--debug', action='store_true', help='Modo debug (logs detalhados)')
    parser.add_argument('--config', type=str, default='config.json', help='Caminho do arquivo de configuração')
    return parser.parse_args()

def setup_logging(debug=False):
    import logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('system.log'), logging.StreamHandler()])
    logging.getLogger('ultralytics').setLevel(logging.WARNING)
    return logging.getLogger(__name__)


def run_desktop_app(core):
    try:
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            print(' PyQt5 não encontrado.')
            print('   Instale com: pip install PyQt5')
            return False
        from interfaces.desktop.app import start_desktop_app
        return start_desktop_app(core)
    except ImportError as e:
        print(f' Erro ao importar módulo desktop: {e}')
        return False
    except Exception as e:
        print(f' Erro na aplicação desktop: {e}')
        return False

def signal_handler(signum, frame):
    print('\n Recebido sinal de interrupção. Desligando...')
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    print('\n' + '=' * 60)
    print(' SISTEMA DE INSPEÇÃO POR VISÃO COMPUTACIONAL')
    print('=' * 60)
    args = parse_arguments()
    logger = setup_logging(args.debug)
    if not check_dependencies():
        return 1
    for dir_name in ['models', 'logs', 'data', 'assets']:
        Path(dir_name).mkdir(exist_ok=True)
    try:
        from core.system_core import SystemCore
        print('\n Inicializando núcleo do sistema...')
        core = SystemCore()
        if not core.initialize():
            print(' Falha ao inicializar o sistema.')
            print('   Verifique se a câmera está conectada e os modelos existem.')
            return 1
        info = core.get_system_info()
        camera_type = info.get('camera', {}).get('type', 'N/A')
        print(f' Sistema inicializado. Câmera: {camera_type}')
        print('\n  Iniciando interface desktop...')
        return run_desktop_app(core)
    except ImportError as e:
        print(f' Erro de importação ao inicializar sistema: {e}')
        print('   Verifique se todas as dependências estão instaladas.')
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f' Erro crítico ao inicializar sistema: {e}')
        import traceback
        traceback.print_exc()
        return 1
if __name__ == '__main__':
    sys.exit(main())