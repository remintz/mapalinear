import uvicorn
import logging
import os
import sys
import warnings

# Suprimir o warning específico do overpass
warnings.filterwarnings("ignore", category=SyntaxWarning, module="overpass.api")

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    """Inicia o servidor da API localmente."""
    host = os.environ.get("MAPALINEAR_HOST", "127.0.0.1")
    port = int(os.environ.get("MAPALINEAR_PORT", 8000))
    
    print(f"Iniciando API em http://{host}:{port}")
    print("Pressione CTRL+C para sair.")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True
    )

if __name__ == "__main__":
    main() 