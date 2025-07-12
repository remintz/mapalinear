# Plano de Desenvolvimento MapaLinear - Melhorias e Frontend NextJS

## Visão Geral

Este documento descreve o planejamento sequencial para implementar melhorias no backend do MapaLinear e desenvolver um frontend moderno em NextJS para criar uma aplicação web completa.

## Fase 1: Melhorias no Backend (API FastAPI)

### 1.1 Otimização da Detecção de POIs (Semana 1-2)

**Objetivo**: Melhorar a qualidade e completude dos dados de pontos de interesse.

#### 1.1.1 Atualizar Queries Overpass API
- **Arquivo**: `api/services/osm_service.py`
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

## Fase 2: Frontend NextJS (Semana 4-8)

### 2.1 Configuração Inicial do Projeto (Semana 4)

#### 2.1.1 Setup do NextJS
```bash
# Criar projeto NextJS na pasta frontend/
npx create-next-app@latest frontend --typescript --tailwind --eslint --app
cd frontend
npm install
```

#### 2.1.2 Dependências Principais
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "@tanstack/react-query": "^5.0.0",
    "leaflet": "^1.9.0",
    "react-leaflet": "^4.2.0",
    "axios": "^1.6.0",
    "zod": "^3.22.0",
    "react-hook-form": "^7.48.0",
    "@hookform/resolvers": "^3.3.0",
    "lucide-react": "^0.294.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0"
  },
  "devDependencies": {
    "@types/leaflet": "^1.9.0"
  }
}
```

#### 2.1.3 Estrutura de Pastas
```
frontend/
├── app/
│   ├── (routes)/
│   │   ├── search/
│   │   ├── map/
│   │   └── history/
│   ├── api/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── ui/
│   ├── forms/
│   ├── maps/
│   └── layout/
├── lib/
│   ├── api.ts
│   ├── types.ts
│   ├── utils.ts
│   └── validations.ts
├── hooks/
└── public/
```

### 2.2 Componentes Core (Semana 5)

#### 2.2.1 API Client
- **Arquivo**: `lib/api.ts`
- **Funcionalidades**:
  - Cliente HTTP configurado para a API
  - Interceptors para autenticação e errors
  - TypeScript types para todas as responses

#### 2.2.2 Componentes de UI Base
- **Pasta**: `components/ui/`
- **Componentes**:
  - Button, Input, Select, Card
  - Loading, Alert, Modal
  - ProgressBar para operações assíncronas

#### 2.2.3 Layout Principal
- **Arquivo**: `app/layout.tsx`
- **Funcionalidades**:
  - Header com navegação
  - Sidebar para filtros/configurações
  - Footer com informações
  - Provider para React Query

### 2.3 Funcionalidades de Busca (Semana 5-6)

#### 2.3.1 Formulário de Busca
- **Arquivo**: `components/forms/SearchForm.tsx`
- **Campos**:
  - Origem e destino com autocomplete
  - Seleção de tipos de POI
  - Configurações avançadas (raio, filtros)
- **Validação**: Zod + React Hook Form

#### 2.3.2 Página de Resultados
- **Arquivo**: `app/(routes)/search/page.tsx`
- **Seções**:
  - Resumo da rota
  - Lista de POIs encontrados
  - Estatísticas da viagem
  - Opções de exportação

#### 2.3.3 Hook de Busca
- **Arquivo**: `hooks/useRouteSearch.ts`
- **Funcionalidades**:
  - Estado de busca assíncrona
  - Progress tracking
  - Error handling
  - Cache de resultados

### 2.4 Visualização em Mapa (Semana 6-7)

#### 2.4.1 Componente de Mapa
- **Arquivo**: `components/maps/RouteMap.tsx`
- **Funcionalidades**:
  - Render da rota principal
  - Markers para POIs categorizados
  - Popup com detalhes dos POIs
  - Zoom automático para rota

#### 2.4.2 Página do Mapa Linear
- **Arquivo**: `app/(routes)/map/[id]/page.tsx`
- **Funcionalidades**:
  - Visualização linear da rota
  - Timeline horizontal com POIs
  - Detalhes expandíveis de cada POI
  - Navegação por segmentos

#### 2.4.3 Controles de Mapa
- **Arquivo**: `components/maps/MapControls.tsx`
- **Funcionalidades**:
  - Toggle de camadas (POIs, rota, satelite)
  - Filtros por tipo de POI
  - Busca de POI específico
  - Exportação do mapa atual

### 2.5 Histórico e Gestão (Semana 7-8)

#### 2.5.1 Página de Histórico
- **Arquivo**: `app/(routes)/history/page.tsx`
- **Funcionalidades**:
  - Lista de mapas salvos
  - Busca e filtros
  - Preview dos mapas
  - Opções de compartilhamento

#### 2.5.2 Dashboard de Operações
- **Arquivo**: `app/(routes)/operations/page.tsx`
- **Funcionalidades**:
  - Monitor de operações assíncronas
  - Progress em tempo real
  - Logs de erros
  - Cancelamento de operações

## Fase 3: Funcionalidades Avançadas (Semana 9-12)

### 3.1 Sistema de Notificações (Semana 9)

#### 3.1.1 WebSocket para Real-time
- **Backend**: Implementar WebSocket endpoint
- **Frontend**: Hook para notificações em tempo real
- **Casos de uso**: Progress updates, completion notifications

#### 3.1.2 Service Worker
- **Funcionalidades**:
  - Notificações push
  - Cache offline para mapas visualizados
  - Background sync para operações

### 3.2 Funcionalidades de Compartilhamento (Semana 10)

#### 3.2.1 URLs Públicas
- **Backend**: Endpoint para criar links públicos
- **Frontend**: Página pública para visualizar mapas
- **Funcionalidades**: Links temporários, embeds para outros sites

#### 3.2.2 Exportação Avançada
- **Formatos**: PDF com mapa visual, Excel com dados tabulares
- **Customização**: Templates, logos, informações adicionais

### 3.3 Analytics e Monitoramento (Semana 11)

#### 3.3.1 Métricas de Uso
- **Backend**: Endpoints para analytics
- **Frontend**: Dashboard de estatísticas
- **Dados**: Rotas mais buscadas, POIs mais relevantes, performance

#### 3.3.2 Feedback dos Usuários
- **Sistema de avaliação**: POIs, rotas, qualidade dos dados
- **Reporting**: Problemas nos dados, sugestões de melhorias

### 3.4 Otimizações Finais (Semana 12)

#### 3.4.1 Performance Frontend
- **Lazy loading**: Componentes e rotas
- **Image optimization**: Logos de marcas, ícones de POI
- **Bundle analysis**: Otimização do tamanho

#### 3.4.2 SEO e Acessibilidade
- **Meta tags**: Para páginas públicas
- **Schema markup**: Para rotas e POIs
- **ARIA labels**: Para todos os componentes interativos

## Fase 4: Deploy e DevOps (Semana 13)

### 4.1 Containerização

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

#### 4.1.2 Docker para Frontend
```dockerfile
# Dockerfile para NextJS
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

### 4.2 Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000/api
    depends_on:
      - api
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### 4.3 CI/CD Pipeline
- **GitHub Actions**: Para testes e deploy automatizado
- **Staging environment**: Para testes antes da produção
- **Production deployment**: Com rollback automático

## Cronograma Resumido

| Semana | Fase | Foco Principal |
|--------|------|----------------|
| 1-2    | Backend | Otimização POIs e Queries OSM |
| 2-3    | Backend | Novos endpoints e features |
| 3      | Backend | Performance e cache |
| 4      | Frontend | Setup NextJS e estrutura |
| 5      | Frontend | Componentes base e busca |
| 6-7    | Frontend | Mapas e visualização |
| 7-8    | Frontend | Histórico e gestão |
| 9-10   | Avançado | Real-time e compartilhamento |
| 11-12  | Avançado | Analytics e otimizações |
| 13     | DevOps | Deploy e infraestrutura |

## Tecnologias Utilizadas

### Backend
- **FastAPI**: API REST
- **Redis**: Cache e sessões
- **Pydantic**: Validação de dados
- **Tenacity**: Retry logic
- **WebSockets**: Comunicação real-time

### Frontend
- **NextJS 14**: Framework React
- **TypeScript**: Type safety
- **TailwindCSS**: Styling
- **React Query**: State management e cache
- **Leaflet**: Mapas interativos
- **React Hook Form + Zod**: Formulários

### DevOps
- **Docker**: Containerização
- **GitHub Actions**: CI/CD
- **Redis**: Cache distribuído

## Considerações Finais

Este plano prioriza:
1. **Qualidade dos dados**: Melhorando a detecção de POIs
2. **Experiência do usuário**: Interface moderna e intuitiva
3. **Performance**: Cache, lazy loading, otimizações
4. **Escalabilidade**: Arquitetura preparada para crescimento
5. **Manutenibilidade**: Código bem estruturado e documentado

O desenvolvimento pode ser ajustado conforme feedback dos usuários e descobertas durante a implementação.