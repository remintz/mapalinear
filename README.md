# Mapa Linear

Aplicação para extração de dados do OpenStreetMap e criação de mapas lineares de estradas do Brasil.

## Características

- Extração de dados do OpenStreetMap para identificar marcos importantes em estradas
- API REST com FastAPI para processamento e armazenamento dos dados
- CLI para interação com a API e visualização dos dados

## Instalação

### Requisitos

- Python 3.9+
- Poetry

### Passos para instalação

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd mapalinear

# Instale as dependências
poetry install
```

## Uso

### CLI

```bash
# Executar o CLI
poetry run mapalinear --help
```

### API

```bash
# Executar a API
poetry run uvicorn mapalinear.api.main:app --reload
```

## Desenvolvimento

Este projeto está em fase inicial de desenvolvimento. O foco atual está na extração de dados do OpenStreetMap e identificação dos principais marcos nas estradas entre dois pontos determinados.
