# PRD: Sistema de Auditoria e Estatísticas de Uso

**Status:** APROVADO - Pronto para implementação
**Data:** 2025-12-25

## Objetivo

Implementar um sistema de logs de auditoria e estatísticas de uso para entender como os usuários utilizam o MapaLinear e quais funcionalidades são mais importantes.

## Decisões

- **Usuários anônimos**: Incluir (rastrear visitantes não logados)
- **Dashboard**: Básico com exportação para planilhas (CSV)
- **Retenção**: 1 ano (365 dias)
- **Eventos extras**: Incluir erros, performance e funil de conversão

---

## Fase 1: Backend - Modelo e Infraestrutura

### 1.1 Criar modelo UserEvent

**Arquivo:** `api/database/models/user_event.py`

Campos:
- `id` (UUID, PK)
- `user_id` (UUID, nullable - para anônimos)
- `event_type` (String, indexed) - tipo do evento
- `event_category` (String, indexed) - categoria
- `event_data` (JSONB) - dados específicos do evento
- `device_type` (String) - mobile/tablet/desktop
- `os`, `browser` (String)
- `screen_width`, `screen_height` (Int)
- `session_id` (String, indexed)
- `page_path`, `referrer` (String)
- `latitude`, `longitude` (Float, nullable)
- `duration_ms` (Int, nullable) - para eventos de performance
- `error_message` (String, nullable) - para eventos de erro
- `created_at` (DateTime, indexed)

Índices compostos para queries analíticas.

### 1.2 Criar enums de tipos de eventos

**Arquivo:** `api/database/models/event_types.py`

Categorias:
- `auth`: login, logout
- `navigation`: page_view, linear_map_view, osm_map_view
- `map_management`: map_create, map_adopt, map_remove, map_search, map_export_*
- `preferences`: poi_filter_toggle
- `interaction`: poi_click
- `reporting`: problem_report_start, problem_report_submit
- `tracking`: route_tracking_start, route_tracking_stop
- `error`: api_error, geolocation_error, offline_cache_miss
- `performance`: map_load_time, search_response_time
- `conversion`: search_started, search_completed, search_abandoned

### 1.3 Criar repositório

**Arquivo:** `api/database/repositories/user_event.py`

Métodos:
- `create_event()` - criar evento
- `get_stats_by_event_type()` - agregação por tipo
- `get_stats_by_device()` - agregação por dispositivo
- `get_daily_active_users()` - DAU
- `get_user_journey()` - jornada de um usuário
- `get_feature_usage()` - uso de funcionalidades
- `get_poi_filter_usage()` - uso de filtros POI
- `get_conversion_funnel()` - funil de conversão
- `cleanup_old_events()` - limpeza (365 dias)
- `export_to_csv()` - exportação para CSV

### 1.4 Criar serviço de logging

**Arquivo:** `api/services/user_event_logger.py`

- Singleton com batched writes (como ApiCallLogger)
- Queue + flush periódico (5s ou 100 itens)
- Métodos helper para cada tipo de evento

---

## Fase 2: Backend - API Endpoints

### 2.1 Criar router de eventos

**Arquivo:** `api/routers/user_events_router.py`

Endpoints públicos:
- `POST /api/events/track` - recebe eventos do frontend (aceita anônimos)

Endpoints admin:
- `GET /api/events/stats` - overview geral
- `GET /api/events/stats/features` - uso de funcionalidades
- `GET /api/events/stats/devices` - dispositivos
- `GET /api/events/stats/poi-filters` - filtros POI
- `GET /api/events/stats/funnel` - funil de conversão
- `GET /api/events/stats/daily` - DAU e tendências
- `GET /api/events/stats/errors` - erros recentes
- `GET /api/events/export/csv` - exportar para CSV
- `DELETE /api/events/cleanup` - limpeza manual

### 2.2 Registrar router

**Arquivo:** `api/main.py`
- Adicionar `user_events_router`

---

## Fase 3: Frontend - Hook de Analytics

### 3.1 Criar hook useAnalytics

**Arquivo:** `frontend/hooks/useAnalytics.ts`

Funcionalidades:
- Detecção de dispositivo (mobile/tablet/desktop)
- Detecção de OS e browser
- Session ID persistente (sessionStorage)
- Queue de eventos com debounce
- sendBeacon para eventos no unload
- Tracking automático de page views

### 3.2 Integrar nas páginas principais

| Página/Componente | Evento |
|-------------------|--------|
| `app/map/page.tsx` | `linear_map_view`, `map_load_time` |
| `RouteMapModal.tsx` | `osm_map_view` |
| `app/search/page.tsx` | `search_started`, `search_completed`, `search_abandoned` |
| `POIFilters.tsx` | `poi_filter_toggle` |
| `POICard.tsx` | `poi_click` |
| Auth callbacks | `login`, `logout` |
| `app/maps/page.tsx` | `map_adopt`, `map_remove` |
| Map creation flow | `map_create` |
| Export buttons | `map_export_pdf`, `map_export_geojson`, `map_export_gpx` |
| Problem report | `problem_report_start`, `problem_report_submit` |
| API interceptor | `api_error` |
| Geolocation hook | `geolocation_error` |
| Route tracking | `route_tracking_start`, `route_tracking_stop` |

---

## Fase 4: Dashboard Admin

### 4.1 Criar página de estatísticas

**Arquivo:** `frontend/app/admin/analytics/page.tsx`

Seções:
1. **Overview**: Total de eventos, usuários únicos, período
2. **Eventos por tipo**: Tabela ordenada por contagem
3. **Dispositivos**: Tabela com device_type, OS, browser
4. **Uso de filtros POI**: Quais filtros são mais usados
5. **DAU**: Tabela de usuários ativos diários
6. **Funil de conversão**: Search → Create → Save
7. **Erros recentes**: Últimos erros para debugging
8. **Botão exportar CSV**: Download de dados

### 4.2 Adicionar link no menu admin

**Arquivo:** `frontend/app/admin/layout.tsx` ou similar

---

## Fase 5: Migração e Testes

### 5.1 Criar migração Alembic

```bash
alembic revision --autogenerate -m "add_user_events_table"
alembic upgrade head
```

### 5.2 Testes

- Testes unitários para UserEventRepository
- Testes de integração para endpoints
- Teste manual do fluxo completo

---

## Arquivos a Criar/Modificar

### Novos arquivos:
- `api/database/models/user_event.py`
- `api/database/models/event_types.py`
- `api/database/repositories/user_event.py`
- `api/services/user_event_logger.py`
- `api/routers/user_events_router.py`
- `frontend/hooks/useAnalytics.ts`
- `frontend/app/admin/analytics/page.tsx`

### Arquivos a modificar:
- `api/database/models/__init__.py` - exportar UserEvent
- `api/database/repositories/__init__.py` - exportar UserEventRepository
- `api/main.py` - registrar router
- `frontend/app/map/page.tsx` - adicionar tracking
- `frontend/components/RouteMapModal.tsx` - adicionar tracking
- `frontend/app/search/page.tsx` - adicionar tracking
- `frontend/components/ui/POIFilters.tsx` - adicionar tracking
- `frontend/components/ui/POICard.tsx` - adicionar tracking
- `frontend/app/maps/page.tsx` - adicionar tracking
- `frontend/lib/api.ts` - interceptor de erros
- `frontend/hooks/useGeolocation.ts` - tracking de erros
- `frontend/app/admin/layout.tsx` - link para analytics

---

## Padrões a Seguir

Seguir os padrões existentes de:
- `api/database/models/api_call_log.py` - estrutura do modelo
- `api/services/api_call_logger.py` - batched writes singleton
- `api/database/repositories/api_call_log.py` - queries de agregação
- `api/routers/api_logs_router.py` - endpoints de estatísticas

---

## Considerações de Privacidade

1. **Dados mínimos**: Não armazenar IP, apenas device info
2. **Session ID**: Não persistente entre sessões
3. **Limpeza automática**: 365 dias
4. **LGPD**: Documentar coleta na política de privacidade
