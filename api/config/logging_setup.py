"""
Setup de logging configurável para a API MapaLinear.

Carrega configuração de logs a partir de arquivo YAML.
"""
import logging
import logging.config
import os
from pathlib import Path
import yaml


def setup_logging(config_path: str = None, default_level: int = logging.INFO):
    """
    Configura o sistema de logging a partir de arquivo YAML.

    Args:
        config_path: Caminho para o arquivo de configuração YAML.
                     Se None, usa o arquivo padrão em api/config/logging_config.yaml
        default_level: Nível de logging padrão caso não consiga carregar a configuração
    """
    if config_path is None:
        # Usar arquivo de configuração padrão
        config_dir = Path(__file__).parent
        config_path = config_dir / "logging_config.yaml"

    config_path = Path(config_path)

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # Criar diretório de logs se não existir
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)

            # Aplicar configuração
            logging.config.dictConfig(config)

            logger = logging.getLogger(__name__)
            logger.info(f"Logging configurado a partir de: {config_path}")

        except Exception as e:
            # Fallback para configuração básica se houver erro
            logging.basicConfig(
                level=default_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            logging.error(f"Erro ao carregar configuração de logging: {e}")
            logging.warning("Usando configuração de logging padrão")
    else:
        # Arquivo não existe, usar configuração básica
        logging.basicConfig(
            level=default_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logging.warning(f"Arquivo de configuração não encontrado: {config_path}")
        logging.info("Usando configuração de logging padrão")


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado.

    Args:
        name: Nome do logger (geralmente __name__ do módulo)

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)
