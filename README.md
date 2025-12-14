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

## Comandos do CLI

O CLI do MapaLinear oferece diversos comandos para trabalhar com dados de estradas. Todos os comandos podem ser executados com `mapalinear` seguido do nome do comando.

### Buscando Estradas (`search`)

Busca estradas e rotas entre duas localidades no OpenStreetMap.

```bash
mapalinear search "Origem, UF" "Destino, UF" [opções]
```

#### Opções

- `--road-type [tipo]`: Tipo de estrada a ser considerada (all, highway, motorway, trunk, primary, secondary). Padrão: "all"
- `--output-file [arquivo]`: Salvar os resultados em um arquivo JSON
- `--no-wait`: Não aguardar a conclusão da operação, apenas retornar o ID da tarefa

#### Quando usar

Use este comando quando precisar encontrar as estradas que conectam duas cidades ou localidades. Isso é útil para:
- Verificar a existência de rotas entre locais
- Obter informações detalhadas sobre os segmentos de estrada
- Preparar dados para gerar um mapa linear posteriormente

#### Exemplo de saída

```
Operação iniciada com ID: a1b2c3d4-5678-90ab-cdef-123456789012
Buscando estradas entre Belo Horizonte, MG e Ouro Preto, MG...
[▮▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯]

Rota de Belo Horizonte, MG para Ouro Preto, MG
Total de segmentos: 12
Comprimento total: 95.68 km
ID da estrada: BH-OP-BR356

┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Segmento ┃ Nome                        ┃ Tipo      ┃ Referência ┃ Comprimento (km) ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 1        │ Avenida Nossa Senhora do... │ trunk     │ BR-356    │ 8.42             │
│ 2        │ Rodovia dos Inconfidentes   │ trunk     │ BR-356    │ 10.13            │
│ 3        │ -                           │ trunk     │ BR-356    │ 12.78            │
│ 4        │ Rodovia dos Inconfidentes   │ trunk     │ BR-356    │ 15.65            │
│ 5        │ -                           │ trunk     │ BR-356    │ 7.89             │
│ 6        │ Rodovia dos Inconfidentes   │ trunk     │ BR-040    │ 7.32             │
│ 7        │ -                           │ trunk     │ BR-356    │ 9.54             │
│ 8        │ Rodovia dos Inconfidentes   │ trunk     │ BR-356    │ 10.25            │
│ 9        │ -                           │ trunk     │ BR-356    │ 5.47             │
│ 10       │ Estrada Real                │ secondary │ -         │ 3.87             │
│ 11       │ Rua Padre Rolim             │ secondary │ -         │ 2.16             │
│ 12       │ Praça Tiradentes            │ secondary │ -         │ 2.20             │
└──────────┴─────────────────────────────┴───────────┴───────────┴──────────────────┘
```

### Gerando Mapa Linear (`generate-map`)

Gera um mapa linear de uma estrada entre dois pontos, incluindo pontos de interesse ao longo do trajeto.

```bash
mapalinear generate-map "Origem, UF" "Destino, UF" [opções]
```

#### Opções

- `--road-id [id]`: ID da estrada (opcional, se já conhecida)
- `--include-cities / --no-include-cities`: Incluir cidades como marcos (padrão: true)
- `--include-gas-stations / --no-include-gas-stations`: Incluir postos de gasolina como marcos (padrão: true)
- `--include-restaurants / --no-include-restaurants`: Incluir restaurantes como marcos (padrão: false)
- `--include-toll-booths / --no-include-toll-booths`: Incluir pedágios como marcos (padrão: true)
- `--max-distance [metros]`: Distância máxima em metros da estrada para incluir pontos de interesse (padrão: 1000)
- `--output-file [arquivo]`: Salvar os resultados em um arquivo JSON
- `--no-wait`: Não aguardar a conclusão da operação, apenas retornar o ID da tarefa

#### Quando usar

Use este comando quando quiser criar uma representação linear de uma estrada com seus pontos de interesse. Isso é útil para:
- Criar representações visuais de rodovias
- Identificar serviços e marcos ao longo de um trajeto
- Planejar viagens com paradas estratégicas

#### Exemplo de saída

```
Operação iniciada com ID: a1b2c3d4-5678-90ab-cdef-123456789012
Gerando mapa linear entre Belo Horizonte, MG e Ouro Preto, MG...
[▮▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯]

Mapa linear de Belo Horizonte, MG para Ouro Preto, MG
ID do mapa: BH-OP-ML-123
Comprimento total: 95.68 km
Número de segmentos: 12
Número de marcos: 24

┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━┓
┃ Km   ┃ Marco                                ┃ Tipo            ┃ Lado ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━┩
│ 0.0  │ Belo Horizonte                       │ city            │ both │
│ 5.3  │ Posto Shell                          │ gas_station     │ right│
│ 12.7 │ Nova Lima                            │ city            │ left │
│ 18.2 │ Posto BR                             │ gas_station     │ right│
│ 24.5 │ Pedágio BR-356                       │ toll_booth      │ both │
│ 31.8 │ Posto Ipiranga                       │ gas_station     │ left │
│ 38.2 │ Itabirito                            │ city            │ right│
│ 45.7 │ Posto Petrobras                      │ gas_station     │ right│
│ 53.4 │ Posto Ale                            │ gas_station     │ left │
│ 60.8 │ Pedágio Itabirito-Ouro Preto         │ toll_booth      │ both │
│ 67.2 │ Cachoeira do Campo                   │ city            │ left │
│ 73.5 │ Posto Shell                          │ gas_station     │ right│
│ 80.1 │ Amarantina                           │ city            │ right│
│ 87.4 │ Posto BR                             │ gas_station     │ left │
│ 95.7 │ Ouro Preto                           │ city            │ both │
└──────┴────────────────────────────────────┴──────────────────┴──────┘
```

### Listar Mapas Salvos (`list-maps`)

Lista todos os mapas lineares que foram salvos no sistema.

```bash
mapalinear list-maps
```

#### Quando usar

Use este comando para visualizar todos os mapas que foram gerados e salvos no sistema. É útil para:
- Verificar mapas disponíveis
- Obter IDs de mapas para consulta detalhada
- Revisar origens e destinos de mapas existentes

#### Exemplo de saída

```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID                 ┃ Origem             ┃ Destino            ┃ Distância (km) ┃ Marcos ┃ Data de Criação       ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ BH-OP-ML-123       │ Belo Horizonte, MG │ Ouro Preto, MG     │ 95.68         │ 24     │ 2023-05-20 14:30:22   │
│ SP-RJ-ML-456       │ São Paulo, SP      │ Rio de Janeiro, RJ │ 430.12        │ 42     │ 2023-05-18 09:15:45   │
│ BSB-GYN-ML-789     │ Brasília, DF       │ Goiânia, GO        │ 209.33        │ 31     │ 2023-05-15 16:40:10   │
└────────────────────┴────────────────────┴────────────────────┴────────────────┴────────┴──────────────────────┘
```

### Obter Detalhes de um Mapa (`get-map`)

Exibe detalhes de um mapa linear específico.

```bash
mapalinear get-map [ID-DO-MAPA]
```

#### Quando usar

Use este comando quando precisar visualizar os detalhes de um mapa específico. É útil para:
- Obter informações detalhadas de um mapa existente
- Verificar datas de criação e metadados
- Conferir referências de estradas

#### Exemplo de saída

```
Mapa BH-OP-ML-123
Origem: Belo Horizonte, MG
Destino: Ouro Preto, MG
Distância total: 95.68 km
Número de marcos: 24
Data de criação: 2023-05-20 14:30:22
Referências: BR-356, BR-040
```

## Gerenciamento de Operações Assíncronas

O MapaLinear utiliza operações assíncronas para tarefas demoradas. As operações podem ser gerenciadas usando o subcomando `operations`.

### Verificar Status de uma Operação (`operations status`)

```bash
mapalinear operations status [ID-DA-OPERAÇÃO] [opções]
```

#### Opções

- `--wait`: Aguardar a conclusão da operação
- `--timeout [segundos]`: Tempo máximo de espera em segundos (padrão: 600)
- `--interval [segundos]`: Intervalo entre verificações de status em segundos (padrão: 3)
- `--output-file [arquivo]`: Salvar resultado da operação em arquivo

#### Quando usar

Use este comando para verificar o status de uma operação em andamento ou para esperar a conclusão de uma operação iniciada com `--no-wait`.

#### Exemplo de saída

```
Operação a1b2c3d4-5678-90ab-cdef-123456789012
Status: completed
Tipo: osm_search
Iniciada: 2023-05-20 15:30:45
Progresso: 100.0%

Resultado da operação:
Busca OSM de Belo Horizonte, MG para Ouro Preto, MG
ID da estrada: BH-OP-BR356
Comprimento total: 95.68 km
Segmentos: 12
```

### Listar Operações (`operations list`)

Lista todas as operações ativas ou concluídas.

```bash
mapalinear operations list [opções]
```

#### Opções

- `--all`: Listar todas as operações (incluindo concluídas e falhas)
- `--limit [número]`: Número máximo de operações a exibir (padrão: 10)

#### Quando usar

Use este comando para visualizar todas as operações em andamento ou recentemente concluídas. É útil para:
- Monitorar múltiplas operações
- Identificar operações que podem estar travadas
- Obter IDs de operações para verificar status detalhado

#### Exemplo de saída

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID                                            ┃ Tipo         ┃ Status        ┃ Progresso  ┃ Iniciada em           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ a1b2c3d4-5678-90ab-cdef-123456789012         │ osm_search   │ completed     │ 100.0%     │ 2023-05-20 15:30:45   │
│ b2c3d4e5-6789-01bc-defg-2345678901234        │ linear_map   │ in_progress   │ 35.0%      │ 2023-05-20 15:45:30   │
│ c3d4e5f6-7890-12cd-efgh-34567890123456       │ osm_search   │ failed        │ -          │ 2023-05-20 15:15:20   │
└──────────────────────────────────────────────┴──────────────┴───────────────┴───────────┴─────────────────────────┘

Dica: Use operations status <id> para verificar o progresso de uma operação específica.
```

### Cancelar uma Operação (`operations cancel`)

Cancela uma operação em andamento.

```bash
mapalinear operations cancel [ID-DA-OPERAÇÃO]
```

#### Quando usar

Use este comando quando precisar interromper uma operação que está demorando muito ou foi iniciada por engano.

#### Exemplo de saída

```
Operação b2c3d4e5-6789-01bc-defg-2345678901234 cancelada com sucesso.
```

### Limpar Operações Antigas (`operations cleanup`)

Remove operações antigas do sistema.

```bash
mapalinear operations cleanup [--max-age-hours HORAS]
```

#### Opções

- `--max-age-hours [horas]`: Idade máxima em horas para manter operações (padrão: 24)

#### Quando usar

Use este comando para fazer manutenção do sistema, removendo operações antigas que não são mais necessárias.

#### Exemplo de saída

```
Foram removidas 15 operações com mais de 24 horas.
```

## Exemplos de Uso Comuns

### Buscar uma rota e salvar os resultados em um arquivo

```bash
mapalinear search "São Paulo, SP" "Campinas, SP" --output-file rota-sp-campinas.json
```

### Gerar um mapa linear incluindo restaurantes

```bash
mapalinear generate-map "Rio de Janeiro, RJ" "Angra dos Reis, RJ" --include-restaurants
```

### Iniciar uma busca em segundo plano e verificar mais tarde

```bash
# Iniciar a busca
mapalinear search "Brasília, DF" "Goiânia, GO" --no-wait
# Saída: Operação iniciada com ID: a1b2c3d4-5678-90ab-cdef-123456789012

# Verificar status posteriormente
mapalinear operations status a1b2c3d4-5678-90ab-cdef-123456789012

# Esperar a conclusão quando conveniente
mapalinear operations status a1b2c3d4-5678-90ab-cdef-123456789012 --wait
```

## Solução de Problemas

### A operação está demorando muito

Para operações que estão demorando muito, você pode:
1. Usar o comando `operations status` para verificar o progresso
2. Cancelar a operação com `operations cancel` e tentar novamente com parâmetros diferentes
3. Verificar se a API está funcionando corretamente

### Erros de conexão

Se você estiver recebendo erros de conexão:
1. Verifique se a URL da API está configurada corretamente
2. Confirme que o servidor da API está em execução
3. Verifique sua conexão com a internet

## Contribuindo

Contribuições são bem-vindas! Por favor, sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.
