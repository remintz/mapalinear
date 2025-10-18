# Plano de Desenvolvimento MapaLinear - Melhorias e Frontend NextJS

## Visão Geral

Este documento descreve o planejamento sequencial para implementar melhorias no backend do MapaLinear e desenvolver um frontend moderno em NextJS para criar uma aplicação web completa.

## Fase 1: Melhorias no Backend (API FastAPI)

### 1.1 Otimização da Detecção de POIs (Semana 1-2)

**Objetivo**: Melhorar a qualidade e completude dos dados de pontos de interesse.

#### 1.1.1 Atualizar Queries Overpass API
- **Arquivo**: `api/providers/osm/provider.py` (migrado de osm_service.py)
- **Melhorias**:
  - Incluir ways e relations além de nodes
  - Unificar queries usando regex: `amenity~"^(fuel|restaurant)$"`
  - Implementar `out geom` para obter coordenadas de ways/relations
  - Adicionar timeout configurável e retry logic

#### 1.1.2 Expandir Filtragem de Qualidade
- **Arquivo**: `api/services/road_service.py`
- **Melhorias**:
  - Priorizar POIs com `name`, `operator` ou `brand`
  - Excluir POIs abandonados (`disused=*`, `abandoned=*`)
  - Validar consistência de dados antes de incluir

#### 1.1.3 Adicionar Metadados Enriquecidos
- **Arquivo**: `api/models/road_models.py`
- **Novas propriedades**:
  - `operator`: string opcional para identificar operadora
  - `brand`: string opcional para marca do estabelecimento
  - `opening_hours`: string opcional para horário de funcionamento
  - `phone`: string opcional para telefone
  - `website`: string opcional para site
  - `cuisine`: string opcional para tipo de culinária (restaurantes)

### 1.2 Novos Endpoints da API (Semana 2-3)

#### 1.2.1 Endpoint de Busca Avançada de POIs
- **Rota**: `GET /api/pois/search`
- **Funcionalidade**: Buscar POIs com filtros avançados
- **Parâmetros**:
  - `lat`, `lon`: coordenadas centrais
  - `radius`: raio de busca em metros
  - `types`: lista de tipos de POI
  - `has_name`: filtrar apenas POIs com nome
  - `sort_by`: ordenação (distance, name, rating)

#### 1.2.2 Endpoint de Estatísticas
- **Rota**: `GET /api/stats/route`
- **Funcionalidade**: Estatísticas da rota e POIs
- **Retorno**:
  - Total de POIs por tipo
  - Densidade de POIs por km
  - Tempo estimado de viagem
  - Pontos de parada recomendados

#### 1.2.3 Endpoint de Exportação
- **Rota**: `GET /api/export/{map_id}`
- **Funcionalidade**: Exportar mapas em diferentes formatos
- **Formatos**: JSON, GPX, KML, CSV

### 1.3 Melhorias na Performance (Semana 3)

#### 1.3.1 Sistema de Cache Avançado
- **Implementar**: Redis ou cache em memória
- **Cachear**: Resultados de rotas, POIs processados, geocodificação
- **TTL**: Configurável por tipo de dados

#### 1.3.2 Processamento Assíncrono Melhorado
- **Arquivo**: `api/services/async_service.py`
- **Melhorias**:
  - Queue para operações longas
  - Progress tracking granular
  - Notificações WebSocket em tempo real

## Fase 2: Frontend PWA com NextJS (Semana 4-8)

### 2.1 Configuração Inicial do PWA (Semana 4)

#### 2.1.1 Setup do NextJS com PWA
```bash
# Criar projeto NextJS na pasta frontend/
npx create-next-app@latest frontend --typescript --tailwind --eslint --app
cd frontend
npm install

# Instalar dependências PWA
npm install next-pwa workbox-webpack-plugin
npm install -D @types/leaflet lighthouse
```

#### 2.1.2 Dependências Principais com PWA
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "next-pwa": "^5.6.0",
    "@tanstack/react-query": "^5.0.0",
    "leaflet": "^1.9.0",
    "react-leaflet": "^4.2.0",
    "axios": "^1.6.0",
    "zod": "^3.22.0",
    "react-hook-form": "^7.48.0",
    "@hookform/resolvers": "^3.3.0",
    "lucide-react": "^0.294.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "idb": "^8.0.0"
  },
  "devDependencies": {
    "@types/leaflet": "^1.9.0",
    "workbox-webpack-plugin": "^7.0.0",
    "lighthouse": "^11.0.0"
  }
}
```

#### 2.1.3 Estrutura de Pastas PWA
```
frontend/
├── app/
│   ├── (routes)/
│   │   ├── search/
│   │   ├── map/
│   │   ├── history/
│   │   └── offline/
│   ├── api/
│   ├── globals.css
│   ├── layout.tsx
│   ├── page.tsx
│   └── manifest.ts
├── components/
│   ├── ui/
│   ├── forms/
│   ├── maps/
│   ├── layout/
│   └── pwa/
│       ├── InstallPrompt.tsx
│       ├── OfflineIndicator.tsx
│       └── UpdateNotification.tsx
├── lib/
│   ├── api.ts
│   ├── types.ts
│   ├── utils.ts
│   ├── validations.ts
│   ├── pwa/
│   │   ├── storage.ts      # IndexedDB helper
│   │   ├── sync.ts         # Background sync
│   │   └── notifications.ts # Push notifications
│   └── offline/
│       ├── cache.ts        # Route/map caching
│       └── fallbacks.ts    # Offline fallbacks
├── hooks/
│   ├── useOnlineStatus.ts
│   ├── useInstallPrompt.ts
│   └── useOfflineStorage.ts
├── public/
│   ├── icons/              # PWA icons (192x192, 512x512, etc.)
│   ├── manifest.json
│   └── sw.js              # Service Worker
└── workers/
    ├── sw.ts              # Service Worker source
    └── background-sync.ts
```

### 2.2 Configuração PWA e Componentes Core (Semana 5)

#### 2.2.1 Configuração PWA Base
- **Arquivo**: `next.config.js`
- **Funcionalidades**:
  - Configuração do next-pwa
  - Service Worker otimizado para caching
  - Manifest.json dinâmico
  - Estratégias de cache específicas para mapas

#### 2.2.2 API Client com Offline Support
- **Arquivo**: `lib/api.ts`
- **Funcionalidades**:
  - Cliente HTTP configurado para a API
  - Interceptors para autenticação e errors
  - Cache local para requests offline
  - Queue para requests quando offline
  - TypeScript types para todas as responses

#### 2.2.3 Componentes PWA Específicos
- **Pasta**: `components/pwa/`
- **Componentes**:
  - InstallPrompt: Prompt para instalar o app
  - OfflineIndicator: Indicador de status offline/online
  - UpdateNotification: Notificação de nova versão disponível
  - SyncIndicator: Indicador de sincronização em background

#### 2.2.4 Componentes de UI Base
- **Pasta**: `components/ui/`
- **Componentes**:
  - Button, Input, Select, Card
  - Loading, Alert, Modal
  - ProgressBar para operações assíncronas
  - TouchFriendly: Componentes otimizados para mobile

#### 2.2.5 Layout Principal PWA
- **Arquivo**: `app/layout.tsx`
- **Funcionalidades**:
  - Header com navegação mobile-first
  - Bottom navigation para mobile
  - PWA meta tags e configurações
  - Provider para React Query com persistence
  - Service Worker registration

### 2.3 Funcionalidades de Busca com Offline (Semana 5-6)

#### 2.3.1 Formulário de Busca Mobile-First
- **Arquivo**: `components/forms/SearchForm.tsx`
- **Campos**:
  - Origem e destino com autocomplete
  - Seleção de tipos de POI com ícones visuais
  - Configurações avançadas (raio, filtros)
  - Modo offline: busca em rotas cachadas
- **Validação**: Zod + React Hook Form
- **PWA Features**: Geolocalização para origem automática

#### 2.3.2 Página de Resultados com Cache
- **Arquivo**: `app/(routes)/search/page.tsx`
- **Seções**:
  - Resumo da rota
  - Lista de POIs encontrados
  - Estatísticas da viagem
  - Opções de cache offline
  - Botão "Salvar para offline"
- **Offline Support**: Mostra resultados cached quando offline

#### 2.3.3 Hook de Busca com Persistence
- **Arquivo**: `hooks/useRouteSearch.ts`
- **Funcionalidades**:
  - Estado de busca assíncrona
  - Progress tracking
  - Error handling com retry offline
  - Cache de resultados no IndexedDB
  - Background sync quando volta online

### 2.4 Visualização em Mapa com PWA (Semana 6-7)

#### 2.4.1 Componente de Mapa Mobile-Optimized
- **Arquivo**: `components/maps/RouteMap.tsx`
- **Funcionalidades**:
  - Render da rota principal
  - Markers para POIs categorizados
  - Popup com detalhes dos POIs adaptado para mobile
  - Zoom automático para rota
  - Cache de tiles para uso offline
  - Gestos touch otimizados

#### 2.4.2 Página do Mapa Linear PWA
- **Arquivo**: `app/(routes)/map/[id]/page.tsx`
- **Funcionalidades**:
  - Visualização linear da rota
  - Timeline horizontal com POIs (swipe-friendly)
  - Detalhes expandíveis de cada POI
  - Navegação por segmentos com gestos
  - Modo landscape otimizado
  - Posição atual do usuário (GPS)
  - Alertas de proximidade

#### 2.4.3 Controles de Mapa Touch-Friendly
- **Arquivo**: `components/maps/MapControls.tsx`
- **Funcionalidades**:
  - Toggle de camadas (POIs, rota, satelite)
  - Filtros por tipo de POI com ícones grandes
  - Busca de POI específico
  - Compartilhamento nativo (Web Share API)
  - Fullscreen mode para landscape

#### 2.4.4 Cache Offline para Mapas
- **Arquivo**: `lib/offline/map-cache.ts`
- **Funcionalidades**:
  - Download de tiles para área da rota
  - Compressão e otimização de dados
  - Limpeza automática de cache antigo
  - Indicador de progresso de download

### 2.5 Histórico e Gestão PWA (Semana 7-8)

#### 2.5.1 Página de Histórico com Storage Local
- **Arquivo**: `app/(routes)/history/page.tsx`
- **Funcionalidades**:
  - Lista de mapas salvos (online + offline)
  - Busca e filtros local
  - Preview dos mapas cached
  - Opções de compartilhamento nativo
  - Gestão de storage (limpar cache, tamanho usado)
  - Sincronização com servidor quando online

#### 2.5.2 Página Offline
- **Arquivo**: `app/(routes)/offline/page.tsx`
- **Funcionalidades**:
  - Lista de conteúdo disponível offline
  - Status de sincronização
  - Opções de download para offline
  - Gestão de espaço em disco

#### 2.5.3 Dashboard de Operações PWA
- **Arquivo**: `app/(routes)/operations/page.tsx`
- **Funcionalidades**:
  - Monitor de operações assíncronas
  - Progress em tempo real
  - Background sync status
  - Queue de operações offline
  - Logs de erros

## Fase 3: Funcionalidades PWA Avançadas (Semana 9-12)

### 3.1 Sistema de Notificações PWA (Semana 9)

#### 3.1.1 Push Notifications
- **Backend**: Implementar endpoint para VAPID e push notifications
- **Frontend**: Gerenciamento de permissões e subscrições
- **Casos de uso**: 
  - Alertas de paradas recomendadas
  - Notificações de chegada próxima
  - Updates de condições da estrada
  - Lembretes de reabastecimento

#### 3.1.2 Service Worker Avançado
- **Arquivo**: `workers/sw.ts`
- **Funcionalidades**:
  - Estratégias de cache inteligentes
  - Background sync para dados críticos
  - Periodic background sync
  - Push notifications handling
  - Update management automático

#### 3.1.3 Geolocation e Proximity
- **Funcionalidades**:
  - Tracking de posição durante viagem
  - Alertas baseados em proximidade
  - Estimativas de tempo até próximo POI
  - Sugestões contextuais baseadas em localização

### 3.2 Compartilhamento e Web APIs (Semana 10)

#### 3.2.1 Web Share API
- **Frontend**: Implementar compartilhamento nativo
- **Funcionalidades**: 
  - Compartilhar rotas via apps nativos
  - Share target para receber rotas compartilhadas
  - Integração com apps de navegação

#### 3.2.2 URLs Públicas e Deep Links
- **Backend**: Endpoint para criar links públicos
- **Frontend**: 
  - Deep linking para rotas específicas
  - Página pública para visualizar mapas
  - PWA installation via shared links

#### 3.2.3 File System Access API
- **Funcionalidades**:
  - Exportar/importar rotas para arquivos locais
  - Backup de dados offline
  - Integração com sistema de arquivos do device

### 3.3 Analytics e PWA Insights (Semana 11)

#### 3.3.1 Métricas PWA Específicas
- **Backend**: Endpoints para analytics PWA
- **Frontend**: Dashboard com métricas mobile
- **Dados**: 
  - Install rates e usage patterns
  - Offline usage statistics
  - Performance metrics (LCP, FID, CLS)
  - Cache effectiveness
  - Push notification engagement

#### 3.3.2 User Feedback PWA
- **Sistema de avaliação**: POIs, rotas, qualidade dos dados
- **Reporting**: Problemas nos dados, sugestões de melhorias
- **PWA Features**:
  - Feedback offline (sync later)
  - Rating prompts contextuais
  - Bug reporting com device info

### 3.4 Otimizações PWA Finais (Semana 12)

#### 3.4.1 Performance PWA
- **Core Web Vitals**: Otimização para LCP, FID, CLS
- **Bundle optimization**: Tree-shaking, code splitting
- **Image optimization**: WebP, responsive images
- **Service Worker optimization**: Cache strategies refinement
- **Preloading crítico**: Critical resources e rotas

#### 3.4.2 PWA Compliance Final
- **Lighthouse audits**: 90+ scores em todas as categorias
- **App Store readiness**: Manifest, icons, screenshots
- **Cross-browser testing**: Chrome, Safari, Firefox mobile
- **Accessibility**: WCAG compliance, screen readers
- **Performance budget**: Monitoring contínuo

## Fase 4: Deploy PWA e DevOps (Semana 13)

### 4.1 Containerização e PWA

#### 4.1.1 Docker para Backend
```dockerfile
# Dockerfile para API FastAPI
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev
COPY . .
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 4.1.2 Docker para Frontend PWA
```dockerfile
# Dockerfile para NextJS PWA
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

#### 4.1.3 HTTPS e PWA Requirements
- **Configuração**: SSL certificates para HTTPS (obrigatório para PWA)
- **Service Worker**: Deployment correto com cache busting
- **CDN**: Configuração para assets estáticos e service worker

### 4.2 Docker Compose PWA
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - VAPID_PUBLIC_KEY=${VAPID_PUBLIC_KEY}
      - VAPID_PRIVATE_KEY=${VAPID_PRIVATE_KEY}
    depends_on:
      - redis
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=https://api.mapalinear.com/api
      - NEXT_PUBLIC_VAPID_PUBLIC_KEY=${VAPID_PUBLIC_KEY}
      - NEXT_PUBLIC_APP_VERSION=${APP_VERSION}
    depends_on:
      - api
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - frontend
      - api
```

### 4.3 CI/CD Pipeline PWA
- **GitHub Actions**: 
  - Testes automatizados (backend + frontend)
  - Lighthouse CI para auditorias PWA
  - Build e deploy automatizado
- **Staging environment**: 
  - Ambiente de testes com HTTPS
  - Testes de PWA compliance
  - Performance testing
- **Production deployment**: 
  - Deploy com zero downtime
  - Service Worker versioning automático
  - Rollback automático se auditorias falharem

## Cronograma Resumido PWA

| Semana | Fase | Foco Principal |
|--------|------|----------------|
| 1-2    | Backend | Otimização POIs e Queries OSM ✅ |
| 2-3    | Backend | Novos endpoints e features ✅ |
| 3      | Backend | Performance e cache |
| 4      | PWA Setup | NextJS + PWA configuration |
| 5      | PWA Core | Componentes base + offline storage |
| 6-7    | PWA Maps | Mapas mobile + cache tiles |
| 7-8    | PWA Storage | Histórico offline + sync |
| 9-10   | PWA Advanced | Push notifications + geolocation |
| 11-12  | PWA Polish | Analytics + performance optimization |
| 13     | DevOps | Deploy PWA + HTTPS + monitoring |

## Tecnologias Utilizadas

### Backend
- **FastAPI**: API REST
- **Redis**: Cache e sessões
- **Pydantic**: Validação de dados
- **Tenacity**: Retry logic
- **WebSockets**: Comunicação real-time
- **Web Push**: Push notifications (pywebpush)

### Frontend PWA
- **NextJS 14**: Framework React com App Router
- **TypeScript**: Type safety
- **TailwindCSS**: Styling mobile-first
- **next-pwa**: PWA configuration e Service Worker
- **React Query**: State management com persistence
- **Leaflet**: Mapas interativos offline-capable
- **React Hook Form + Zod**: Formulários
- **IndexedDB (idb)**: Storage local para offline
- **Workbox**: Service Worker strategies

### Web APIs Utilizadas
- **Service Worker**: Cache e background sync
- **Push API**: Notificações push
- **Geolocation API**: Posicionamento
- **Web Share API**: Compartilhamento nativo
- **File System Access API**: Acesso a arquivos
- **Notification API**: Notificações locais

### DevOps
- **Docker**: Containerização multi-stage
- **GitHub Actions**: CI/CD com Lighthouse
- **Nginx**: Reverse proxy com HTTPS
- **Redis**: Cache distribuído
- **Let's Encrypt**: SSL certificates

## Considerações Finais PWA

Este plano PWA prioriza:
1. **Qualidade dos dados**: Melhorando a detecção de POIs ✅
2. **Experiência Mobile**: Interface touch-first e instalável
3. **Funcionalidade Offline**: Uso essencial sem internet durante viagens
4. **Performance**: Core Web Vitals otimizados para mobile
5. **Native-like Experience**: PWA que se comporta como app nativo
6. **Escalabilidade**: Arquitetura preparada para crescimento
7. **Acessibilidade**: WCAG compliance e usabilidade universal

### Vantagens da Abordagem PWA
- ✅ **Desenvolvimento único** para todas as plataformas
- ✅ **Deploy simples** sem app stores
- ✅ **Atualizações automáticas** e transparentes
- ✅ **Funcionalidade offline crítica** para uso em estradas
- ✅ **Performance nativa** com Service Workers
- ✅ **Instalação opcional** mas disponível
- ✅ **Menor barreira de entrada** para usuários

O desenvolvimento pode ser ajustado conforme feedback dos usuários e descobertas durante a implementação, mantendo sempre o foco na experiência mobile e funcionalidade offline.