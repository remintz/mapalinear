import uvicorn
import logging
import os
import sys
import warnings
import signal
import threading

# General warning suppressions if needed
# warnings.filterwarnings("ignore", category=DeprecationWarning)

# Remover manipuladores existentes para evitar duplicação
root_logger = logging.getLogger()
if root_logger.handlers:
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Definir nível de logging para bibliotecas de terceiros
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduzir verbosidade
logging.getLogger("fastapi").setLevel(logging.INFO)

# Definir nível de logging para nossa aplicação
# Configurar o logger raiz da aplicação para DEBUG para ver mais informações
app_logger = logging.getLogger("api")
app_logger.setLevel(logging.DEBUG)
app_logger.propagate = False  # Evitar duplicação

# Configurar formatador que preserva quebras de linha em mensagens de erro
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Adicionar handler se não existir
if not app_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)
    
# Garantir que o middleware de erro tenha seu próprio logger com nível DEBUG
error_logger = logging.getLogger("api.middleware.error_handler")
error_logger.setLevel(logging.DEBUG)
error_logger.propagate = False  # Evitar duplicação

if not error_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    error_logger.addHandler(handler)

def setup_signal_handlers():
    """Configura handlers para shutdown graceful."""
    def signal_handler(signum, frame):
        print(f"\n🛑 Recebido sinal {signum}. Encerrando servidor...")
        
        # Limpar threads ativas se necessário
        active_threads = threading.active_count()
        if active_threads > 1:
            print(f"📝 {active_threads} threads ativas sendo finalizadas...")
        
        # Force exit se necessário
        os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Inicia o servidor da API localmente."""
    host = os.environ.get("MAPALINEAR_HOST", "127.0.0.1")
    port = int(os.environ.get("MAPALINEAR_PORT", 8000))
    
    print(f"Iniciando API em http://{host}:{port}")
    print("Pressione CTRL+C para sair.")
    
    # Configurar handlers de sinal para shutdown graceful
    setup_signal_handlers()
    
    # Configuração unificada de logs para evitar duplicação
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {"handlers": ["default"], "level": "INFO"},  # Root logger
            "api": {"handlers": ["default"], "level": "DEBUG", "propagate": False},
            "api.middleware": {"handlers": ["default"], "level": "DEBUG", "propagate": False},
            "api.middleware.error_handler": {"handlers": ["default"], "level": "DEBUG", "propagate": False},
            "api.services": {"handlers": ["default"], "level": "DEBUG", "propagate": False},
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        },
    }
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["api/", "mapalinear/"],
        reload_includes=["*.py"],
        log_config=log_config
    )

if __name__ == "__main__":
    main() 