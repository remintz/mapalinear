# MapaLinear - Priorização de Features para POC

## Objetivo da POC
Criar uma prova de conceito simples para validar se é possível construir um mapa linear com POIs relevantes para casos reais de viagem.

## Lista de Features para Priorização

| Categoria | Feature | Descrição | POC (X) | Comentários |
|-----------|---------|-----------|---------|-------------|
| **CORE - Backend API** |
| Backend | Buscar rota entre duas cidades | API para calcular rota usando OSM | X | |
| Backend | Detectar POIs ao longo da rota | Encontrar postos, restaurantes, pedágios na rota | X | |
| Backend | Endpoint gerar mapa linear | `POST /api/roads/linear-map` básico | X | |
| Backend | Cache básico de resultados | Evitar reprocessar mesma rota | X | |
| **CORE - Frontend Básico** |
| Frontend | Página de busca | Formulário origem → destino | X | |
| Frontend | Exibir mapa linear | Timeline horizontal com POIs | X | Em celular o timeline deve ser vertical |
| Frontend | Mostrar detalhes do POI | Card com informações básicas do POI | X | |
| Frontend | Lista de POIs encontrados | Tabela/lista simples dos POIs | X | |
| **VISUALIZAÇÃO ESSENCIAL** |
| Frontend | Mapa geográfico básico | Leaflet com rota e markers | | |
| Frontend | Timeline linear visual | Linha com marcos de distância | X | |
| Frontend | Ícones por tipo de POI | Visual diferenciado para posto/restaurante/pedágio | X | |
| Frontend | Filtro por tipo de POI | Toggle show/hide tipos de POI | | |
| **POI FEATURES BÁSICAS** |
| Backend | POIs - Postos de combustível | Detectar amenity=fuel | X | |
| Backend | POIs - Restaurantes | Detectar amenity=restaurant | X | |
| Backend | POIs - Pedágios | Detectar barrier=toll_booth | X | |
| Backend | Informações básicas POI | Nome, coordenadas, distância da rota | X | |
| Backend | Filtro qualidade básico | Excluir POIs sem nome ou abandonados | | |
| **INTERFACE MÍNIMA** |
| Frontend | Layout responsivo básico | Funciona em desktop e mobile | X | |
| Frontend | Loading states | Indicador durante processamento | X | |
| Frontend | Error handling básico | Mensagens de erro amigáveis | X | |
| Frontend | Resultado exportável | JSON/CSV simples | | |
| **MELHORIAS OSM** |
| Backend | Queries OSM otimizadas | Ways + relations além de nodes | X | |
| Backend | Metadados enriquecidos | Operator, brand, opening_hours básicos | X | |
| Backend | Timeout e retry logic | Robustez nas consultas OSM | X | |
| **FEATURES AVANÇADAS - Backend** |
| Backend | Endpoint busca avançada POIs | `GET /api/pois/search` com filtros | | |
| Backend | Endpoint estatísticas rota | `GET /api/stats/route` com densidade POIs | | |
| Backend | Processamento assíncrono | Queue para operações longas | | |
| Backend | Sistema cache Redis | Cache distribuído | | |
| Backend | WebSocket notifications | Updates em tempo real | | |
| Backend | Exportação múltiplos formatos | GPX, KML, CSV | | |
| **PWA FEATURES** |
| PWA | Instalação como app | Add to Home Screen |  | |
| PWA | Service Worker básico | Cache offline básico |  | |
| PWA | Funciona offline | Rotas cached funcionam offline | | |
| PWA | Storage local | IndexedDB para dados offline | | |
| PWA | Background sync | Sincroniza quando volta online | | |
| PWA | Push notifications | Alertas de paradas recomendadas | | |
| PWA | Geolocalização | Posição atual do usuário | | |
| PWA | Web Share API | Compartilhamento nativo | | |
| **UX/UI AVANÇADO** |
| Frontend | Design system completo | Paleta cores, tipografia, componentes | X | |
| Frontend | Animações e transições | UX polida | | |
| Frontend | Modo escuro | Dark/light theme | | |
| Frontend | Múltiplas visualizações | Linear, geográfico, lista | X | Geográfico não é necessário |
| Frontend | Busca com autocomplete | Sugestões de cidades |  | |
| Frontend | Histórico de buscas | Rotas salvas anteriormente |  | |
| Frontend | Configurações usuário | Preferências pessoais | X | |
| **MOBILE OTIMIZATIONS** |
| Mobile | Touch gestures | Swipe, pinch, tap otimizados | | |
| Mobile | Bottom navigation | Navegação mobile-friendly | X | |
| Mobile | Modo landscape | Layout otimizado horizontal | X | |
| Mobile | Keyboard shortcuts | Atalhos para desktop | | |
| **ANALYTICS & INSIGHTS** |
| Analytics | Métricas básicas uso | Rotas mais buscadas | | |
| Analytics | Performance monitoring | Core Web Vitals | | |
| Analytics | Error tracking | Logs de erros estruturados | | |
| Analytics | User feedback | Sistema avaliação POIs | | |
| **DEVOPS & DEPLOY** |
| DevOps | Docker básico | Containerização simples | X | |
| DevOps | Docker Compose | Orquestração local | X | |
| DevOps | CI/CD básico | GitHub Actions simples | X | |
| DevOps | HTTPS deployment | SSL para PWA | | |
| DevOps | Lighthouse CI | Auditorias automáticas | X | |
| DevOps | Environment configs | Staging + Production | X | |
| **QUALIDADE & TESTES** |
| Quality | Testes unitários backend | pytest coverage básica | X | |
| Quality | Testes frontend | Jest + Testing Library | X | |
| Quality | E2E tests | Playwright casos críticos | X | |
| Quality | Code quality tools | ESLint, Black, mypy | X | |
| Quality | Documentation | Documentação API (Swagger) | X | |
| **SEGURANÇA & PERFORMANCE** |
| Security | Validação entrada | Sanitização dados usuário | | |
| Security | Rate limiting | Proteção contra abuso | | |
| Performance | Bundle optimization | Tree-shaking, code splitting | | |
| Performance | Image optimization | WebP, responsive images | | |
| Performance | Database optimization | Queries eficientes | | |
| **ACESSIBILIDADE** |
| A11y | Navegação teclado | Tab, Enter, Arrow keys | X | |
| A11y | Screen reader support | ARIA labels, landmarks | X | |
| A11y | Contraste adequado | WCAG 2.1 compliance | X | |
| A11y | Focus management | Estados focus visíveis | X | |

## Critérios para POC

**OBRIGATÓRIO para POC:**
- ✅ Funcionalidade core: busca rota + detecção POIs + visualização linear
- ✅ Interface mínima funcional
- ✅ Casos reais testáveis

**OPCIONAL para POC:**
- PWA features (pode ser web app normal primeiro)
- Features avançadas de UX/UI
- Analytics e métricas
- Testes extensivos
- DevOps complexo

**FORA DO ESCOPO POC:**
- Push notifications
- Background sync
- Múltiplos formatos exportação
- Sistema usuário/autenticação
- Features enterprise

---

## Instruções de Uso

1. ✅ Marque com **X** na coluna POC as features essenciais para validar o conceito
2. 📝 Use a coluna **Comentários** para anotar:
   - Por que é/não é necessário para POC
   - Dependências ou riscos
   - Versão simplificada aceitável
   - Prioridade (P0/P1/P2)

## Casos de Teste POC

Para validar a POC, testar com rotas reais como:
- São Paulo, SP → Rio de Janeiro, RJ
- Belo Horizonte, MG → São Paulo, SP  
- Brasília, DF → Goiânia, GO
- São Paulo, SP → Curitiba, PR

Verificar se consegue encontrar POIs relevantes e apresentá-los de forma útil em um mapa linear.