# Plano POC MapaLinear - Foco na Validação do Conceito

## Objetivo da POC
Criar uma **prova de conceito simples** para validar se é possível construir um mapa linear com POIs relevantes para casos reais de viagem, priorizando funcionalidade core sobre features avançadas.

## Escopo Reduzido da POC

### ✅ **Features INCLUÍDAS na POC** (25 features marcadas)

#### **🎯 CORE - Backend API (4/4)**
- ✅ Buscar rota entre duas cidades
- ✅ Detectar POIs ao longo da rota  
- ✅ Endpoint gerar mapa linear (`POST /api/roads/linear-map`)
- ✅ Cache básico de resultados

#### **🎯 CORE - Frontend Básico (4/4)**
- ✅ Página de busca (formulário origem → destino)
- ✅ Exibir mapa linear (timeline horizontal/vertical para mobile)
- ✅ Mostrar detalhes do POI
- ✅ Lista de POIs encontrados

#### **📊 VISUALIZAÇÃO ESSENCIAL (2/4)**
- ✅ Timeline linear visual
- ✅ Ícones por tipo de POI
- ❌ Mapa geográfico básico (não essencial para POC)
- ❌ Filtro por tipo de POI (pode ser adicionado depois)

#### **📍 POI FEATURES BÁSICAS (4/5)**
- ✅ POIs - Postos de combustível
- ✅ POIs - Restaurantes  
- ✅ POIs - Pedágios
- ✅ Informações básicas POI
- ❌ Filtro qualidade básico (pode usar dados existentes)

#### **💻 INTERFACE MÍNIMA (3/4)**
- ✅ Layout responsivo básico
- ✅ Loading states
- ✅ Error handling básico
- ❌ Resultado exportável (não prioritário)

#### **⚡ MELHORIAS OSM (3/3)**
- ✅ Queries OSM otimizadas
- ✅ Metadados enriquecidos
- ✅ Timeout e retry logic

#### **🎨 UX/UI CORE (3/7)**
- ✅ Design system completo
- ✅ Múltiplas visualizações (linear + lista)
- ✅ Configurações usuário
- ❌ Features avançadas de UX (modo escuro, animações, etc.)

#### **📱 MOBILE BÁSICO (2/4)**
- ✅ Bottom navigation
- ✅ Modo landscape
- ❌ Touch gestures avançados
- ❌ Keyboard shortcuts

#### **🐳 DEVOPS ESSENCIAL (6/6)**
- ✅ Docker básico
- ✅ Docker Compose
- ✅ CI/CD básico
- ✅ Lighthouse CI
- ✅ Environment configs
- ❌ HTTPS deployment (pode ser HTTP para POC)

#### **🧪 QUALIDADE BÁSICA (5/5)**
- ✅ Testes unitários backend
- ✅ Testes frontend
- ✅ E2E tests
- ✅ Code quality tools
- ✅ Documentation

#### **♿ ACESSIBILIDADE BÁSICA (4/4)**
- ✅ Navegação teclado
- ✅ Screen reader support
- ✅ Contraste adequado
- ✅ Focus management

### ❌ **Features EXCLUÍDAS da POC** (50 features)

#### **PWA Features (8/8)** - Todas excluídas
- ❌ Instalação como app
- ❌ Service Worker
- ❌ Funciona offline
- ❌ Storage local
- ❌ Background sync
- ❌ Push notifications
- ❌ Geolocalização
- ❌ Web Share API

#### **Features Avançadas Backend (6/6)** - Todas excluídas
- ❌ Endpoint busca avançada POIs
- ❌ Endpoint estatísticas rota
- ❌ Processamento assíncrono
- ❌ Sistema cache Redis
- ❌ WebSocket notifications
- ❌ Exportação múltiplos formatos

#### **Analytics, Segurança, Performance** - Todas excluídas
- ❌ Métricas e analytics
- ❌ Validação entrada avançada
- ❌ Rate limiting
- ❌ Bundle optimization
- ❌ Image optimization

---

## Cronograma POC Simplificado

### **Semana 1-2: Backend Core** ✅ (Já implementado)
- ✅ Otimização detecção POIs 
- ✅ Queries OSM melhoradas
- ✅ Endpoints básicos funcionando

### **Semana 3: Frontend Setup e Core (2 semanas)**

#### **Semana 3.1: Setup NextJS Básico**
```bash
# Criar projeto NextJS simples (SEM PWA)
npx create-next-app@latest frontend --typescript --tailwind --eslint --app
cd frontend
npm install

# Dependências mínimas para POC
npm install leaflet react-leaflet axios @tanstack/react-query
npm install react-hook-form @hookform/resolvers zod
npm install lucide-react clsx tailwind-merge
```

#### **Dependências POC Simplificadas**
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

#### **Estrutura Simplificada POC**
```
frontend/
├── app/
│   ├── search/page.tsx        # Página de busca
│   ├── map/[id]/page.tsx      # Página do mapa linear
│   ├── layout.tsx             # Layout básico
│   └── page.tsx               # Home
├── components/
│   ├── ui/                    # Button, Input, Card básicos
│   ├── forms/SearchForm.tsx   # Formulário de busca
│   ├── maps/LinearMap.tsx     # Componente mapa linear
│   └── poi/POICard.tsx        # Card de POI
├── lib/
│   ├── api.ts                 # Cliente HTTP básico
│   ├── types.ts               # Types principais
│   └── utils.ts               # Utilities
└── hooks/
    └── useRouteSearch.ts      # Hook de busca
```

### **Semana 3.2: Frontend Core**

#### **Implementar Features Core**
1. **Página de Busca**
   - Formulário origem → destino simples
   - Loading state durante busca
   - Error handling básico

2. **Mapa Linear**
   - Timeline horizontal (desktop) / vertical (mobile)
   - Ícones diferenciados por tipo POI
   - Cards com detalhes básicos do POI

3. **Lista de POIs**
   - Tabela/lista simples dos POIs encontrados
   - Informações básicas (nome, tipo, distância)

4. **Layout Responsivo**
   - Mobile-first design básico
   - Bottom navigation para mobile
   - Modo landscape otimizado

### **Semana 4: Polimento e Testes**

#### **Design System Básico**
- Paleta de cores simples
- Tipografia consistente
- Componentes UI padronizados
- Ícones para tipos de POI

#### **Qualidade e Testes**
- Testes unitários backend (pytest)
- Testes frontend (Jest + Testing Library)
- E2E tests casos críticos (Playwright)
- Documentation API (Swagger)

#### **DevOps POC**
- Docker setup básico
- Docker Compose local
- CI/CD simples (GitHub Actions)
- Environment configs básicas

---

## Casos de Teste POC

### **Rotas de Validação**
1. **São Paulo, SP → Rio de Janeiro, RJ** (429km)
   - Verificar postos na Dutra
   - Restaurantes em pontos estratégicos
   - Pedágios identificados

2. **Belo Horizonte, MG → São Paulo, SP** (586km)
   - POIs na BR-381 (Fernão Dias)
   - Pontos de parada em Três Corações, Cambuí

3. **Brasília, DF → Goiânia, GO** (209km)
   - Rota mais curta para teste rápido
   - Validar detecção em rodovia menor

4. **São Paulo, SP → Curitiba, PR** (408km)
   - Teste na BR-116 (Régis Bittencourt)
   - POIs em região montanhosa

### **Critérios de Sucesso POC**
- ✅ **Funcional**: Encontra e exibe POIs relevantes
- ✅ **Usável**: Interface intuitiva mobile/desktop
- ✅ **Rápido**: Carrega resultados em <10s
- ✅ **Preciso**: POIs a <1km da rota principal
- ✅ **Completo**: Informações básicas suficientes

---

## Tecnologias POC Simplificadas

### **Backend** (mantém atual)
- FastAPI + Pydantic
- Cache simples (não Redis)
- OSM Overpass API
- Processamento síncrono

### **Frontend**
- NextJS 14 (sem PWA)
- TypeScript + TailwindCSS
- React Query (sem persistence)
- Leaflet (opcional para POC)

### **DevOps**
- Docker + Docker Compose
- GitHub Actions básico
- Deploy HTTP (sem HTTPS)

---

## Próximos Passos Pós-POC

Após validar o conceito core, expandir para:

1. **PWA Features** (offline, instalação, notifications)
2. **Features Avançadas** (estatísticas, busca avançada, exportação)
3. **Performance** (Redis, async, otimizações)
4. **Analytics** (métricas de uso, feedback)
5. **Security** (HTTPS, validação, rate limiting)

## Timeline POC

| Semana | Foco | Status |
|--------|------|--------|
| 1-2 | Backend Core | ✅ Completo |
| 3 | Frontend Setup + Core | 🔄 Próximo |
| 4 | Polimento + Testes | ⏳ Pendente |
| 5 | Deploy + Validação | ⏳ Pendente |

**Meta: POC funcional em 5 semanas para validar conceito antes de investir em features avançadas.**