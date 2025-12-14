# MapaLinear

MapaLinear é uma ferramenta para extrair dados do OpenStreetMap e criar mapas lineares de estradas do Brasil. Este projeto permite buscar rotas entre cidades, extrair informações sobre estradas e gerar mapas lineares com pontos de interesse.

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/mapalinear.git
cd mapalinear

# Instalar dependências usando Poetry
poetry install

# Ativar o ambiente virtual
poetry shell
```

## Configuração

O MapaLinear utiliza uma API para processar as operações. Por padrão, a API é acessada em `http://localhost:8000/api`. Você pode configurar a URL da API através da variável de ambiente:

```bash
export MAPALINEAR_API_URL="http://seu-servidor-api.com/api"
```

### Configuração de Provedores de Dados

O MapaLinear suporta múltiplos provedores de dados geográficos. Cada etapa da geração de mapas pode ser configurada independentemente:

#### Pipeline de Geração de Mapas

```
1. Geocoding (origem/destino)     → OSM (Nominatim) - sempre
2. Cálculo de Rota                → OSM (OSRM) - sempre
3. Busca de POIs                  → Configurável: OSM ou HERE
4. Enriquecimento Google Places   → Opcional: ratings de restaurantes/hotéis
5. Enriquecimento HERE            → Opcional: telefone, website, horários
```

#### Variáveis de Ambiente

**Busca de POIs:**
```bash
# Provedor para busca de POIs (osm ou here)
POI_PROVIDER=osm  # padrão

# Chave HERE (obrigatória se POI_PROVIDER=here ou HERE_ENRICHMENT_ENABLED=true)
HERE_API_KEY=sua-chave-here
```

**Enriquecimento de Dados:**
```bash
# Google Places - adiciona ratings para restaurantes e hotéis
GOOGLE_PLACES_ENABLED=true  # padrão
GOOGLE_PLACES_API_KEY=sua-chave-google

# HERE - adiciona telefone, website, horários, endereço estruturado
# (apenas quando POI_PROVIDER=osm)
HERE_ENRICHMENT_ENABLED=false  # padrão
```

#### Matriz de Configuração

| POI_PROVIDER | GOOGLE_PLACES_ENABLED | HERE_ENRICHMENT_ENABLED | Resultado |
|--------------|----------------------|-------------------------|-----------|
| osm          | true                 | false                   | POIs OSM + ratings Google |
| osm          | true                 | true                    | POIs OSM + ratings Google + dados HERE |
| osm          | false                | true                    | POIs OSM + dados HERE |
| here         | true                 | N/A                     | POIs HERE + ratings Google |
| here         | false                | N/A                     | POIs HERE apenas |

**Nota:** Quando `POI_PROVIDER=here`, os POIs já vêm com dados de contato do HERE, então `HERE_ENRICHMENT_ENABLED` é ignorado.

#### Custos dos Provedores

- **OSM**: Gratuito (rate limit: 1 req/segundo)
- **Google Places**: ~$17-35 por 1.000 requests
- **HERE Maps**: Free tier 250.000/mês, depois ~$0.50-5 por 1.000 requests

### Monitoramento de Custos de API

O MapaLinear registra automaticamente todas as chamadas a APIs externas (OSM, HERE, Google Places) em um banco de dados para monitoramento e análise de custos.

#### Endpoints de Estatísticas

```bash
# Estatísticas agregadas por provedor (últimos 30 dias)
curl http://localhost:8001/api/api-logs/stats

# Estatísticas diárias para análise de tendências
curl http://localhost:8001/api/api-logs/stats/daily

# Logs recentes para debug
curl http://localhost:8001/api/api-logs/recent?limit=50

# Logs de erros para troubleshooting
curl http://localhost:8001/api/api-logs/errors

# Limpeza de logs antigos (mantém 90 dias por padrão)
curl -X DELETE "http://localhost:8001/api/api-logs/cleanup?days_to_keep=90"
```

#### Informações Registradas

Para cada chamada de API:
- Provedor (osm, here, google_places)
- Tipo de operação (geocode, poi_search, route, etc.)
- Endpoint e método HTTP
- Status de resposta e duração
- Tamanho da resposta em bytes
- Quantidade de resultados
- Cache hit/miss
- Mensagens de erro (se houver)

#### Exemplo de Resposta de Estatísticas

```json
{
  "period_start": "2024-11-14T00:00:00",
  "period_end": "2024-12-14T00:00:00",
  "by_provider": [
    {
      "provider": "osm",
      "total_calls": 1250,
      "api_calls": 450,
      "cache_hits": 800,
      "cache_hit_rate": 64.0,
      "avg_duration_ms": 342.5,
      "total_bytes": 2450000
    },
    {
      "provider": "google_places",
      "total_calls": 320,
      "api_calls": 280,
      "cache_hits": 40,
      "cache_hit_rate": 12.5,
      "avg_duration_ms": 185.3,
      "total_bytes": 156000
    }
  ],
  "by_operation": [
    {
      "provider": "osm",
      "operation": "poi_search",
      "total_calls": 800,
      "api_calls": 300,
      "avg_duration_ms": 420.1,
      "total_results": 4500
    }
  ]
}
```

## Uso via API

O MapaLinear é acessado através de sua API REST. Veja a documentação da API em `http://localhost:8001/docs` quando o servidor estiver rodando.

### Exemplos de Uso da API

```bash
# Verificar se a API está funcionando
curl http://localhost:8001/api/health

# Buscar POIs em uma localização
curl "http://localhost:8001/api/pois/search?lat=-23.5505&lon=-46.6333&radius=1000&types=gas_station,restaurant"

# Buscar estatísticas de rotas
curl "http://localhost:8001/api/roads/stats?origin=São Paulo, SP&destination=Rio de Janeiro, RJ"
```

## Solução de Problemas

### Erros de conexão

Se você estiver recebendo erros de conexão:
1. Verifique se a URL da API está configurada corretamente
2. Confirme que o servidor da API está em execução
3. Verifique sua conexão com a internet

## Contribuindo

Contribuições são bem-vindas! Por favor, sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.
