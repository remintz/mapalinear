# Setup GitHub Project Kanban - MapaLinear POC

## Estrutura do Project

### Colunas do Kanban:
1. **📋 Backlog** - Issues planejadas
2. **🔄 Em Progresso** - Issues sendo trabalhadas
3. **👀 Em Review** - PRs pendentes de review
4. **✅ Concluído** - Issues finalizadas
5. **🧪 Validação** - Features prontas para teste

### Milestones:
- **M1: Backend Core** (Semanas 1-2) ✅ Completo
- **M2: Frontend Setup** (Semana 3.1) 
- **M3: Frontend Core** (Semana 3.2)
- **M4: Polimento** (Semana 4)
- **M5: Validação POC** (Semana 5)

---

## Issues para Criar no GitHub

### 🎯 **MILESTONE 1: Backend Core** ✅ (Completo)

#### Epic: Otimização POIs
- [x] **#1** - Melhorar queries Overpass API (incluir ways/relations)
- [x] **#2** - Implementar timeout e retry logic 
- [x] **#3** - Adicionar metadados enriquecidos (operator, brand, etc.)
- [x] **#4** - Filtros de qualidade POI

#### Epic: Endpoints Básicos
- [x] **#5** - Endpoint `POST /api/roads/linear-map`
- [x] **#6** - Cache básico de resultados
- [x] **#7** - Error handling robusto

---

### 🚀 **MILESTONE 2: Frontend Setup** (Semana 3.1)

#### Epic: Configuração Inicial
- [ ] **#8** - Setup projeto NextJS com TypeScript + Tailwind
  ```
  Criar projeto base sem PWA:
  - npx create-next-app@latest frontend --typescript --tailwind --eslint --app
  - Instalar dependências mínimas (React Query, Leaflet, Axios, Zod)
  - Configurar estrutura de pastas simplificada
  
  Acceptance Criteria:
  - [ ] Projeto NextJS funcionando em localhost:3000
  - [ ] TypeScript configurado sem erros
  - [ ] TailwindCSS aplicando estilos
  - [ ] Dependências principais instaladas
  ```

- [ ] **#9** - Configurar cliente API básico
  ```
  Implementar lib/api.ts:
  - Cliente HTTP com Axios
  - Interceptors básicos para error handling
  - Types TypeScript para requests/responses
  - Configuração de baseURL
  
  Acceptance Criteria:
  - [ ] Cliente API funcional conectando com backend
  - [ ] Error handling básico implementado
  - [ ] Types de resposta definidos
  ```

- [ ] **#10** - Estrutura de componentes básicos
  ```
  Criar componentes UI fundamentais:
  - Button, Input, Card, Loading
  - Layout responsivo básico
  - Navigation component
  
  Acceptance Criteria:
  - [ ] Componentes UI reutilizáveis
  - [ ] Design system básico aplicado
  - [ ] Layout responsivo funcional
  ```

---

### 🎨 **MILESTONE 3: Frontend Core** (Semana 3.2)

#### Epic: Página de Busca
- [ ] **#11** - Implementar formulário de busca
  ```
  Componente SearchForm.tsx:
  - Campos origem e destino
  - Validação com Zod + React Hook Form
  - Loading states durante busca
  - Error handling com mensagens claras
  
  Acceptance Criteria:
  - [ ] Formulário funcional com validação
  - [ ] Estados de loading implementados
  - [ ] Errors exibidos ao usuário
  - [ ] Responsivo mobile/desktop
  ```

- [ ] **#12** - Página de busca (/search)
  ```
  Implementar app/search/page.tsx:
  - Layout da página de busca
  - Integração com SearchForm
  - Redirecionamento para resultado
  
  Acceptance Criteria:
  - [ ] Página acessível via /search
  - [ ] Formulário integrado
  - [ ] Navegação funcionando
  ```

#### Epic: Visualização Mapa Linear
- [ ] **#13** - Componente Timeline Linear
  ```
  Implementar components/maps/LinearMap.tsx:
  - Timeline horizontal (desktop) / vertical (mobile)
  - Pontos marcados por distância
  - Ícones diferenciados por tipo POI
  - Informações básicas no hover/tap
  
  Acceptance Criteria:
  - [ ] Timeline responsiva
  - [ ] POIs posicionados corretamente
  - [ ] Ícones visuais por tipo
  - [ ] Interação hover/tap funcional
  ```

- [ ] **#14** - Cards de POI
  ```
  Implementar components/poi/POICard.tsx:
  - Card com informações do POI
  - Ícone por tipo (posto, restaurante, pedágio)
  - Distância da origem
  - Nome e detalhes básicos
  
  Acceptance Criteria:
  - [ ] Cards visuais atrativos
  - [ ] Informações organizadas
  - [ ] Ícones consistentes
  - [ ] Layout responsivo
  ```

- [ ] **#15** - Página do mapa linear (/map/[id])
  ```
  Implementar app/map/[id]/page.tsx:
  - Receber dados da rota via API
  - Exibir LinearMap component
  - Lista de POIs lateral/inferior
  - Loading e error states
  
  Acceptance Criteria:
  - [ ] Página carrega dados da API
  - [ ] Mapa linear exibido
  - [ ] Lista POIs funcional
  - [ ] Estados de loading/error
  ```

#### Epic: Lista e Navegação
- [ ] **#16** - Lista de POIs
  ```
  Componente para listar POIs encontrados:
  - Tabela/lista simples
  - Filtro por tipo básico
  - Ordenação por distância
  - Click para highlight no mapa
  
  Acceptance Criteria:
  - [ ] Lista exibe todos POIs
  - [ ] Filtros básicos funcionais
  - [ ] Ordenação implementada
  - [ ] Integração com mapa
  ```

- [ ] **#17** - Navegação mobile-first
  ```
  Bottom navigation para mobile:
  - Home, Search, History, Settings
  - Icons clara e intuitiva
  - Active state indicado
  - Modo landscape otimizado
  
  Acceptance Criteria:
  - [ ] Navigation responsiva
  - [ ] Icons e labels claros
  - [ ] Estados ativos visíveis
  - [ ] Acessível por teclado
  ```

---

### 🎨 **MILESTONE 4: Polimento** (Semana 4)

#### Epic: Design System
- [ ] **#18** - Design system completo
  ```
  Definir e implementar:
  - Paleta de cores consistente
  - Tipografia (headings, body, small)
  - Spacing e layout system
  - Component library documented
  
  Acceptance Criteria:
  - [ ] Cores definidas e aplicadas
  - [ ] Typography scale consistente
  - [ ] Spacing system implementado
  - [ ] Documentação components
  ```

- [ ] **#19** - Ícones e assets POI
  ```
  Sistema de ícones para POIs:
  - Ícones posto de combustível
  - Ícones restaurante
  - Ícones pedágio
  - Estados hover/active
  
  Acceptance Criteria:
  - [ ] Ícones visualmente claros
  - [ ] Consistência visual
  - [ ] Estados interativos
  - [ ] Otimizados para mobile
  ```

#### Epic: UX/UI Polish
- [ ] **#20** - Loading states melhorados
  ```
  Skeleton loading e indicators:
  - Skeleton para timeline
  - Loading spinners contextuais
  - Progress bars para operações longas
  - Empty states amigáveis
  
  Acceptance Criteria:
  - [ ] Loading states visuais
  - [ ] Skeleton layouts implementados
  - [ ] Empty states informativos
  - [ ] UX fluida durante carregamento
  ```

- [ ] **#21** - Error handling e UX
  ```
  Melhorar tratamento de erros:
  - Mensagens de erro amigáveis
  - Retry buttons onde apropriado
  - Fallbacks para casos de falha
  - Toast notifications
  
  Acceptance Criteria:
  - [ ] Errors claramente comunicados
  - [ ] Actions de recovery disponíveis
  - [ ] UX não quebra em falhas
  - [ ] Feedback visual adequado
  ```

#### Epic: Responsividade
- [ ] **#22** - Layout responsivo completo
  ```
  Otimizar para todos devices:
  - Mobile portrait/landscape
  - Tablet
  - Desktop
  - Breakpoints bem definidos
  
  Acceptance Criteria:
  - [ ] Funciona em mobile portrait
  - [ ] Funciona em mobile landscape
  - [ ] Funciona em tablet
  - [ ] Funciona em desktop
  ```

---

### 🧪 **MILESTONE 5: Validação POC** (Semana 5)

#### Epic: Testes
- [ ] **#23** - Testes unitários backend
  ```
  Implementar testes pytest:
  - Testes serviços OSM
  - Testes endpoints API
  - Testes modelos Pydantic
  - Coverage mínimo 70%
  
  Acceptance Criteria:
  - [ ] Tests passando em CI
  - [ ] Coverage >= 70%
  - [ ] Tests casos críticos
  - [ ] Mocks apropriados
  ```

- [ ] **#24** - Testes frontend
  ```
  Implementar testes Jest + Testing Library:
  - Testes componentes principais
  - Testes hooks customizados
  - Testes integração API
  - Snapshot tests components UI
  
  Acceptance Criteria:
  - [ ] Tests passando em CI
  - [ ] Coverage components principais
  - [ ] Tests user interactions
  - [ ] Mock API calls
  ```

- [ ] **#25** - E2E tests críticos
  ```
  Implementar testes Playwright:
  - Fluxo busca completo
  - Visualização mapa linear
  - Responsividade mobile/desktop
  - Performance básica
  
  Acceptance Criteria:
  - [ ] Fluxo principal testado
  - [ ] Tests mobile/desktop
  - [ ] Performance aceitável
  - [ ] Tests rodando em CI
  ```

#### Epic: DevOps
- [ ] **#26** - Docker setup completo
  ```
  Containerização:
  - Dockerfile frontend otimizado
  - Docker Compose orquestração
  - Environment configs
  - Development workflow
  
  Acceptance Criteria:
  - [ ] Container frontend funcionando
  - [ ] Docker Compose rodando stack
  - [ ] Env configs organizadas
  - [ ] Dev workflow documentado
  ```

- [ ] **#27** - CI/CD pipeline
  ```
  GitHub Actions:
  - Build e test automatizado
  - Lint e type checking
  - E2E tests em pipeline
  - Deploy preview branches
  
  Acceptance Criteria:
  - [ ] Pipeline rodando em PRs
  - [ ] Tests automatizados
  - [ ] Qualidade code gates
  - [ ] Deploy preview funcional
  ```

#### Epic: Validação com Usuários
- [ ] **#28** - Testar rotas reais
  ```
  Validar POC com casos reais:
  - São Paulo → Rio de Janeiro
  - Belo Horizonte → São Paulo
  - Brasília → Goiânia
  - São Paulo → Curitiba
  
  Acceptance Criteria:
  - [ ] POIs encontrados em todas rotas
  - [ ] Informações precisas
  - [ ] Performance aceitável (<10s)
  - [ ] UX intuitiva
  ```

- [ ] **#29** - Documentação POC
  ```
  Documentar resultados:
  - README atualizado
  - API documentation
  - Deployment instructions
  - Lessons learned
  
  Acceptance Criteria:
  - [ ] Docs completas e atuais
  - [ ] Setup instructions claras
  - [ ] API documented
  - [ ] Learnings documentados
  ```

- [ ] **#30** - Demo e apresentação
  ```
  Preparar demo POC:
  - Video walkthrough
  - Screenshots key features
  - Performance metrics
  - Next steps roadmap
  
  Acceptance Criteria:
  - [ ] Demo video gravado
  - [ ] Screenshots profissionais
  - [ ] Metrics coletadas
  - [ ] Roadmap definido
  ```

---

## Labels Sugeridas

- **`epic`** - Issues grandes que agrupam features
- **`frontend`** - Código frontend/UI
- **`backend`** - Código backend/API  
- **`design`** - UX/UI design work
- **`testing`** - Implementação de testes
- **`devops`** - Infrastructure e deployment
- **`poc`** - Específico da POC
- **`priority:high`** - Alta prioridade
- **`priority:medium`** - Média prioridade
- **`priority:low`** - Baixa prioridade
- **`good first issue`** - Para contribuidores novos
- **`bug`** - Correção de bugs
- **`enhancement`** - Melhoria de feature existente

## Commands para Setup

```bash
# Criar milestones
gh api repos/:owner/:repo/milestones -f title="M1: Backend Core" -f description="Semanas 1-2: APIs e POI detection" -f due_on="2025-01-26T00:00:00Z"

gh api repos/:owner/:repo/milestones -f title="M2: Frontend Setup" -f description="Semana 3.1: NextJS + dependências" -f due_on="2025-02-02T00:00:00Z"

gh api repos/:owner/:repo/milestones -f title="M3: Frontend Core" -f description="Semana 3.2: Busca + timeline + POIs" -f due_on="2025-02-09T00:00:00Z"

gh api repos/:owner/:repo/milestones -f title="M4: Polimento" -f description="Semana 4: Design + UX + responsivo" -f due_on="2025-02-16T00:00:00Z"

gh api repos/:owner/:repo/milestones -f title="M5: Validação POC" -f description="Semana 5: Testes + deploy + validação" -f due_on="2025-02-23T00:00:00Z"

# Criar labels
gh label create "epic" --description "Epic/large feature" --color "8B5CF6"
gh label create "frontend" --description "Frontend/UI work" --color "06B6D4" 
gh label create "backend" --description "Backend/API work" --color "EF4444"
gh label create "design" --description "UX/UI design" --color "F59E0B"
gh label create "testing" --description "Test implementation" --color "10B981"
gh label create "devops" --description "Infrastructure/deployment" --color "6B7280"
gh label create "poc" --description "POC specific" --color "EC4899"
```

---

## Como Usar

1. **Criar Project**: GitHub → Projects → New Project → Board template
2. **Configurar Colunas**: Backlog, Em Progresso, Em Review, Concluído, Validação
3. **Criar Milestones**: Use os commands acima
4. **Criar Issues**: Copie descrições acima para cada issue
5. **Assignar Milestones**: Linke cada issue ao milestone correto
6. **Adicionar ao Project**: Arraste issues para coluna Backlog
7. **Começar Sprint**: Mova issues prioritárias para Em Progresso

Isso criará um kanban completo e organizado para gerenciar toda a POC do MapaLinear! 🚀