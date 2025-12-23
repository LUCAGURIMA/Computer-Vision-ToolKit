"""
Sistema de logging unificado para todo o sistema.
Usa loguru para logs bonitos e funcionais.
"""

import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

# Importa configurações
from config import LOGS_DIR, LOGGING_CONFIG

class SystemLogger:
    """
    Logger centralizado do sistema.
    
    Por que centralizar o logging?
    1. Formato consistente em toda aplicação
    2. Fácil de mudar destino (arquivo, console, etc.)
    3. Controle centralizado de nível de log
    """
    
    def __init__(self):
        """Configura o logger do sistema"""
        self._configure_logger()
        
    def _configure_logger(self):
        """Configura handlers do loguru"""
        
        # Remove handlers padrão
        logger.remove()
        
        # Handler para console
        logger.add(
            sys.stdout,
            level=LOGGING_CONFIG["level"],
            format=LOGGING_CONFIG["format"],
            colorize=True  # Cores no terminal
        )
        
        # Handler para arquivo
        log_file = LOGS_DIR / f"system_{datetime.now().strftime('%Y%m%d')}.log"
        logger.add(
            str(log_file),
            level="DEBUG",  # No arquivo guardamos TUDO
            format=LOGGING_CONFIG["format"],
            rotation=LOGGING_CONFIG["rotation"],
            retention=LOGGING_CONFIG["retention"],
            compression="zip"  # Comprime logs antigos
        )
        
        # Handler para erros (arquivo separado)
        error_file = LOGS_DIR / "errors.log"
        logger.add(
            str(error_file),
            level="ERROR",
            format=LOGGING_CONFIG["format"],
            rotation="50 MB",
            retention="1 year"
        )
        
        logger.info("✅ Logger do sistema configurado")
        logger.info(f"📄 Logs principais: {log_file}")
        logger.info(f"❌ Logs de erro: {error_file}")
    
    def get_logger(self):
        """
        Retorna o logger configurado.
        
        Uso:
            from core.utils.logger import system_logger
            log = system_logger.get_logger()
            log.info("Mensagem informativa")
            log.error("Algo deu errado!")
        """
        return logger
    
    # Métodos de conveniência
    def info(self, message: str):
        """Log nível INFO"""
        logger.info(message)
    
    def error(self, message: str):
        """Log nível ERROR"""
        logger.error(message)
    
    def warning(self, message: str):
        """Log nível WARNING"""
        logger.warning(message)
    
    def debug(self, message: str):
        """Log nível DEBUG"""
        logger.debug(message)
    
    def critical(self, message: str):
        """Log nível CRITICAL"""
        logger.critical(message)

# Instância global do logger
system_logger = SystemLogger()
log = system_logger.get_logger()

# Exemplo de uso:
if __name__ == "__main__":
    log.info("Esta é uma mensagem informativa")
    log.warning("Cuidado! Algo pode estar errado")
    log.error("Erro crítico ocorreu!")
    log.debug("Debug: valor x = 42")