# Configuração de Logging

Este diretório contém as configurações de logging da API MapaLinear.

## Arquivos de Configuração

- **`logging_config.yaml`** - Configuração padrão (desenvolvimento)
- **`logging_config.debug.yaml`** - Configuração detalhada para debugging
- **`logging_config.production.yaml`** - Configuração otimizada para produção

## Como Usar

### Usar configuração padrão

A configuração padrão é carregada automaticamente quando a API inicia.

### Usar configuração específica

```python
from api.config.logging_setup import setup_logging

# Carregar configuração de debug
setup_logging("api/config/logging_config.debug.yaml")
```

Ou via variável de ambiente:

```bash
export LOGGING_CONFIG=api/config/logging_config.production.yaml
python -m api.run
```

## Estrutura do Arquivo YAML

```yaml
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: "formato da mensagem"

handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: default

loggers:
  api:
    level: DEBUG
    handlers: [console]
    propagate: false

root:
  level: INFO
  handlers: [console]
```

## Níveis de Log

- **DEBUG** - Informações detalhadas para diagnóstico
- **INFO** - Confirmação de operações normais
- **WARNING** - Algo inesperado mas a aplicação continua
- **ERROR** - Erro sério, mas a aplicação continua
- **CRITICAL** - Erro muito sério, aplicação pode parar

## Customização

Para criar sua própria configuração:

1. Copie um dos arquivos existentes
2. Ajuste os níveis de log por módulo
3. Configure handlers (console, arquivo, etc)
4. Use com `setup_logging("caminho/para/config.yaml")`
