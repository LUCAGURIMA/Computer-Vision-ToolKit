import sys
from pathlib import Path
from loguru import logger
from datetime import datetime
from config import LOGS_DIR, LOGGING_CONFIG

class SystemLogger:

    def __init__(self):
        self._configure_logger()

    def _configure_logger(self):
        logger.remove()
        logger.add(sys.stdout, level=LOGGING_CONFIG['level'], format=LOGGING_CONFIG['format'], colorize=True)
        log_file = LOGS_DIR / f"system_{datetime.now().strftime('%Y%m%d')}.log"
        logger.add(str(log_file), level='DEBUG', format=LOGGING_CONFIG['format'], rotation=LOGGING_CONFIG['rotation'], retention=LOGGING_CONFIG['retention'], compression='zip')
        error_file = LOGS_DIR / 'errors.log'
        logger.add(str(error_file), level='ERROR', format=LOGGING_CONFIG['format'], rotation='50 MB', retention='1 year')
        logger.info('Sistema de logging configurado com sucesso')
        logger.info(f'Logs principais: {log_file}')
        logger.info(f'Logs de erro: {error_file}')

    def get_logger(self):
        return logger

    def info(self, message: str):
        logger.info(message)

    def error(self, message: str):
        logger.error(message)

    def warning(self, message: str):
        logger.warning(message)

    def debug(self, message: str):
        logger.debug(message)

    def critical(self, message: str):
        logger.critical(message)
system_logger = SystemLogger()
log = system_logger.get_logger()
if __name__ == '__main__':
    log.info('Esta é uma mensagem informativa')
    log.warning('Cuidado! Algo pode estar errado')
    log.error('Erro crítico ocorreu!')
    log.debug('Debug: valor x = 42')