# Eventos de Analytics - MapaLinear

Este documento lista todos os eventos rastreados pelo sistema de analytics.

## Categorias de Eventos

| Categoria | Descricao |
|-----------|-----------|
| `auth` | Eventos de autenticacao |
| `navigation` | Eventos de navegacao entre paginas |
| `map_management` | Eventos de gerenciamento de mapas |
| `preferences` | Eventos de preferencias do usuario |
| `interaction` | Eventos de interacao com elementos |
| `reporting` | Eventos de reportes de problemas |
| `tracking` | Eventos de rastreamento de rota |
| `performance` | Eventos de metricas de performance |
| `conversion` | Eventos de funil de conversao |

---

## Lista de Eventos

### Auth (`auth`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `login` | Usuario fez login | `{ provider }` | `LoginButton.tsx` |
| `logout` | Usuario fez logout | `{ user_id }` | `LoginButton.tsx` |

### Navigation (`navigation`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `page_view` | Usuario visualizou uma pagina | `page_path` | `map/page.tsx`, `maps/page.tsx` |
| `linear_map_view` | Usuario visualizou o mapa linear | `{ map_id, origin, destination }` | `map/page.tsx` |
| `osm_map_view` | Usuario abriu o mapa OSM (modal) | `{ map_id }` | `map/page.tsx` |

### Map Management (`map_management`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `map_create` | Mapa foi criado | `{ map_id }` | (via backend) |
| `map_adopt` | Usuario adotou um mapa existente do cache | `{ map_id }` | `search/page.tsx` |
| `map_remove` | Usuario removeu um mapa salvo | `{ map_id }` | `maps/page.tsx` |
| `map_search` | Usuario pesquisou mapas disponiveis | `{ origin?, destination? }` | `maps/available/page.tsx` |
| `map_export_pdf` | Usuario exportou mapa para PDF | `{ map_id }` | `map/page.tsx` |
| `map_export_geojson` | Usuario exportou mapa para GeoJSON | `{ map_id }` | `map/page.tsx` |
| `map_export_gpx` | Usuario exportou mapa para GPX | `{ map_id }` | `map/page.tsx` |

### Preferences (`preferences`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `poi_filter_toggle` | Usuario alterou filtro de POI | `{ filter_name, enabled }` | `POIFilters.tsx` |

### Interaction (`interaction`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `poi_click` | Usuario clicou em um POI | `{ poi_id, poi_name, poi_type }` | `POIFeed.tsx` |

### Reporting (`reporting`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `problem_report_start` | Usuario abriu o modal de reporte | `{ map_id }` | `ReportProblemModal.tsx` |
| `problem_report_submit` | Usuario enviou reporte com sucesso | `{ map_id, problem_type_id, has_photos, has_audio, poi_id }` | `ReportProblemModal.tsx` |

### Tracking (`tracking`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `route_tracking_start` | Usuario iniciou rastreamento/simulacao | `{ map_id, mode }` | `SimulationControls.tsx` |
| `route_tracking_stop` | Usuario parou rastreamento/simulacao | `{ map_id, mode, distance_traveled_km, progress_percent }` | `SimulationControls.tsx` |

### Performance (`performance`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `map_load_time` | Tempo de carregamento do mapa | `{ map_id, poi_count, segment_count }` + `duration_ms` | `map/page.tsx` |
| `search_response_time` | Tempo de resposta da busca de rota | `{ origin, destination, total_distance_km, poi_count }` + `duration_ms` | `useAsyncRouteSearch.ts` |

### Conversion (`conversion`)

| Evento | Descricao | Dados | Arquivo |
|--------|-----------|-------|---------|
| `search_started` | Usuario iniciou uma busca de rota | `{ origin, destination }` | `search/page.tsx` |
| `search_completed` | Busca foi concluida com sucesso | `{ map_id }` | `search/page.tsx` |
| `search_abandoned` | Usuario abandonou a busca antes de completar | `{ origin, destination, progress_percent }` | `search/page.tsx` |

---

## Informacoes Coletadas em Cada Evento

Alem dos dados especificos de cada evento, todos os eventos incluem:

| Campo | Descricao |
|-------|-----------|
| `session_id` | ID unico da sessao do usuario |
| `user_id` | ID do usuario (se autenticado) |
| `device_type` | Tipo de dispositivo (mobile, tablet, desktop) |
| `os` | Sistema operacional |
| `browser` | Navegador |
| `screen_width` | Largura da tela |
| `screen_height` | Altura da tela |
| `page_path` | Caminho da pagina atual |
| `referrer` | URL de origem |
| `timestamp` | Data/hora do evento (adicionado pelo backend) |
| `duration_ms` | Duracao em milissegundos (eventos de performance) |

---

## Arquivos Relacionados

- **Tipos**: `frontend/lib/analytics-types.ts`
- **Hook**: `frontend/hooks/useAnalytics.ts`
- **Dashboard Admin**: `frontend/app/admin/analytics/page.tsx`
- **API Backend**: `api/routers/events_router.py`

---

## Status de Implementacao

| Categoria | Implementados | Total |
|-----------|---------------|-------|
| Auth | 2 | 2 |
| Navigation | 3 | 3 |
| Map Management | 7 | 7 |
| Preferences | 1 | 1 |
| Interaction | 1 | 1 |
| Reporting | 2 | 2 |
| Tracking | 2 | 2 |
| Performance | 2 | 2 |
| Conversion | 3 | 3 |
| **Total** | **23** | **23** |

Todos os eventos definidos estao implementados.

*Ultima atualizacao: 2026-01-04*
