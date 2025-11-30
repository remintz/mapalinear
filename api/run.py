import uvicorn
import os
import signal
import threading
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

from api.config.logging_setup import setup_logging

# Configurar logging a partir do arquivo YAML
setup_logging()

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

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["api/", "mapalinear/"],
        reload_includes=["*.py"],
        log_config=None  # Usar configuração já inicializada
    )

if __name__ == "__main__":
    main() 