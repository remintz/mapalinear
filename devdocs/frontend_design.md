# Design do Frontend - MapaLinear

## Visão Geral

O MapaLinear é uma aplicação web destinada a auxiliar motoristas e passageiros durante viagens rodoviárias, oferecendo uma visão antecipada dos pontos de interesse que encontrarão ao longo do percurso. Diferentemente de aplicações de navegação como Waze ou Google Maps, o foco não está em instruções turn-by-turn, mas sim em fornecer informação contextual sobre o que está à frente na viagem.

## Conceito Central

### Proposta de Valor
- **Planejamento de Paradas**: Permitir que viajantes vejam onde estão os próximos postos de combustível, restaurantes e cidades importantes
- **Visão Linear da Rota**: Apresentar a viagem como uma linha temporal com marcos distribuídos por distância
- **Informação Contextual**: Fornecer detalhes relevantes sobre estabelecimentos e pontos de parada
- **Complemento à Navegação**: Funcionar como ferramenta de apoio a apps de navegação tradicionais

### Diferencial Competitivo
| MapaLinear | Apps de Navegação Tradicionais |
|------------|-------------------------------|
| Foco em pontos de interesse à frente | Foco em próxima instrução de navegação |
| Visão linear/temporal da viagem | Visão espacial/geográfica |
| Planejamento de paradas | Orientação para chegada |
| Informação antecipada | Informação just-in-time |

## Personas e Casos de Uso

### Persona 1: Carlos - Motorista de Viagem Longa
- **Perfil**: Empresário, 45 anos, viaja São Paulo → Belo Horizonte mensalmente
- **Necessidades**:
  - Saber onde parar para abastecer sem desvios desnecessários
  - Identificar restaurantes de qualidade na rota
  - Planejar pausas estratégicas para descanso
- **Comportamento**: Usa Waze para navegação, mas quer informação complementar sobre a viagem

### Persona 2: Ana - Família em Viagem de Férias
- **Perfil**: Mãe de família, 38 anos, viajando com crianças Rio → Cabo Frio
- **Necessidades**:
  - Identificar paradas com estrutura para crianças
  - Encontrar restaurantes familiares próximos à estrada
  - Saber distâncias entre cidades para explicar às crianças
- **Comportamento**: Planeja com antecedência, gosta de previsibilidade

### Persona 3: Roberto - Motorista Profissional
- **Perfil**: Caminhoneiro, 52 anos, rotas variadas pelo país
- **Necessidades**:
  - Postos com estrutura para caminhões
  - Pontos de descanso adequados
  - Informações sobre pedágios e custos
- **Comportamento**: Conhece muitas rotas, mas precisa de informação sobre novas

## Arquitetura de Informação

### Hierarquia de Telas

```
1. Home / Busca
   ├── Formulário de Busca (Origem → Destino)
   ├── Filtros de POI
   └── Rotas Recentes

2. Mapa Linear
   ├── Visão Geral da Rota
   ├── Timeline Linear
   ├── Detalhes de POIs
   └── Controles de Filtro

3. Detalhes do POI
   ├── Informações Básicas
   ├── Avaliações/Reviews
   ├── Distância da Rota
   └── Como Chegar

4. Histórico
   ├── Mapas Salvos
   ├── Favoritos
   └── Exportações

5. Configurações
   ├── Preferências de POI
   ├── Unidades de Medida
   └── Configurações de Conta
```

## Wireframes Conceituais

### Tela 1: Home / Busca
```
┌─────────────────────────────────────────┐
│ 🗺️ MapaLinear                          │
├─────────────────────────────────────────┤
│                                         │
│    🚗 Planeje sua próxima viagem        │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │ 📍 De: [São Paulo, SP          ] │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐ │
│  │ 📍 Para: [Rio de Janeiro, RJ   ] │ │
│  └─────────────────────────────────────┘ │
│                                         │
│  📋 O que deseja encontrar?              │
│  ☑️ Postos de Combustível                │
│  ☑️ Restaurantes                         │
│  ☑️ Cidades Importantes                  │
│  ☐ Hotéis/Pousadas                      │
│  ☐ Pedágios                             │
│                                         │
│      [🔍 Criar Mapa Linear]            │
│                                         │
│  📚 Rotas Recentes:                     │
│  • SP → RJ (ontem)                      │
│  • BH → SP (3 dias atrás)              │
│                                         │
└─────────────────────────────────────────┘
```

### Tela 2: Mapa Linear - Visão Principal
```
┌─────────────────────────────────────────────────────────────┐
│ ← São Paulo, SP → Rio de Janeiro, RJ    🔧 ⭐ 📤       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📊 Resumo da Viagem                                         │
│ • Distância Total: 429 km                                  │
│ • Tempo Estimado: 5h30                                     │
│ • 12 Postos • 8 Restaurantes • 5 Cidades                  │
│                                                             │
│ 🎛️ [⛽ Postos] [🍽️ Restaurantes] [🏙️ Cidades] [🛣️ Pedágios] │
│                                                             │
│ ━━━━━━━━━━━━━ LINHA TEMPORAL DA VIAGEM ━━━━━━━━━━━━━━         │
│                                                             │
│ 0km    50km   100km  150km  200km  250km  300km  350km 429km│
│ │      │      │      │      │      │      │      │      │  │
│ SP     ⛽      🏙️     ⛽🍽️    🏙️     ⛽      🍽️     ⛽      RJ │
│ │      │      │      │      │      │      │      │      │  │
│ │    Posto   Jacareí  Rest.  S.J.  Shell  Outback Dutra    │
│ │    Ipiranga       +Posto  Campos         Steakhouse      │
│                                                             │
│ ▼ Selecionado: Posto Ipiranga (Km 52)                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ⛽ Posto Ipiranga                                      │ │
│ │ 📍 Rod. Presidente Dutra, Km 52                       │ │
│ │ 🕒 24h • ⭐ 4.2 (127 avaliações)                     │ │
│ │ 💳 Cartão • 🚿 Banheiro • ☕ Lanchonete              │ │
│ │ 📏 50m da pista • 2min de desvio                      │ │
│ │ [📱 Como Chegar] [⭐ Favoritar] [ℹ️ Mais Info]       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Tela 3: Vista de Mapa Geográfico (Alternativa)
```
┌─────────────────────────────────────────────────────────────┐
│ 🗺️ [Linear] [Geográfico] [Lista]           🔧 ⭐ 📤       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │     🗺️ MAPA GEOGRÁFICO                              │  │
│  │                                                       │  │
│  │  📍SP ━━━━━⛽━━━━🏙️━━━⛽🍽️━━━🏙️━━━⛽━━━🍽️━━⛽━━━📍RJ │  │
│  │             │    │     │      │    │    │    │       │  │
│  │             │  Jacareí │   S.J.Campos │    │  Dutra   │  │
│  │           Posto   │   Posto+Rest │  Shell Outback    │  │
│  │          Ipiranga │               │      │           │  │
│  │                   │               │      │           │  │
│  │  [🔍 Zoom] [📍 Centralizar] [🎯 Minha Localização]  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│ 📋 POIs Próximos:                                          │
│ ⛽ Posto Ipiranga (52km) - 24h, 4.2⭐                     │
│ 🍽️ McDonald's Jacareí (87km) - até 23h, 4.0⭐            │
│ ⛽ Shell Select (156km) - 24h, 4.5⭐                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Sistema de Design

### Paleta de Cores

#### Cores Primárias
- **Azul Principal**: `#2563EB` (Blue-600) - Navegação, links, CTAs principais
- **Azul Escuro**: `#1E40AF` (Blue-700) - Estados hover, texto importante
- **Azul Claro**: `#DBEAFE` (Blue-100) - Backgrounds, destaques suaves

#### Cores Funcionais
- **Verde**: `#059669` (Emerald-600) - Sucesso, postos de combustível abertos
- **Vermelho**: `#DC2626` (Red-600) - Erro, estabelecimentos fechados
- **Amarelo**: `#D97706` (Amber-600) - Atenção, informações importantes
- **Laranja**: `#EA580C` (Orange-600) - Restaurantes, alimentação

#### Cores de POI
- **Postos**: `#059669` (Verde) + `⛽` 
- **Restaurantes**: `#EA580C` (Laranja) + `🍽️`
- **Cidades**: `#6366F1` (Indigo) + `🏙️`
- **Hotéis**: `#7C3AED` (Violet) + `🏨`
- **Pedágios**: `#DC2626` (Vermelho) + `🛣️`

#### Cores Neutras
- **Texto Principal**: `#111827` (Gray-900)
- **Texto Secundário**: `#6B7280` (Gray-500)
- **Background**: `#F9FAFB` (Gray-50)
- **Borders**: `#E5E7EB` (Gray-200)

### Tipografia

#### Hierarquia de Fontes
```css
/* Font Family */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

/* Títulos */
.title-xl { font-size: 2.5rem; font-weight: 700; } /* 40px - Título principal */
.title-lg { font-size: 2rem; font-weight: 600; }   /* 32px - Títulos de seção */
.title-md { font-size: 1.5rem; font-weight: 600; } /* 24px - Subtítulos */
.title-sm { font-size: 1.25rem; font-weight: 500; }/* 20px - Títulos menores */

/* Corpo de texto */
.text-lg { font-size: 1.125rem; }  /* 18px - Texto importante */
.text-base { font-size: 1rem; }    /* 16px - Texto padrão */
.text-sm { font-size: 0.875rem; }  /* 14px - Texto secundário */
.text-xs { font-size: 0.75rem; }   /* 12px - Labels, captions */
```

### Componentes Base

#### Botões
```typescript
// Botão Primário
<Button variant="primary" size="lg">
  🔍 Criar Mapa Linear
</Button>

// Botão Secundário  
<Button variant="secondary" size="md">
  📱 Como Chegar
</Button>

// Botão de Ícone
<IconButton icon="star" variant="ghost" />
```

#### Cards de POI
```typescript
interface POICardProps {
  poi: {
    type: 'gas_station' | 'restaurant' | 'city' | 'hotel';
    name: string;
    distance: number;
    rating?: number;
    isOpen: boolean;
    amenities: string[];
  };
  isSelected?: boolean;
  onClick?: () => void;
}

// Exemplo de uso
<POICard 
  poi={{
    type: 'gas_station',
    name: 'Posto Ipiranga',
    distance: 52,
    rating: 4.2,
    isOpen: true,
    amenities: ['24h', 'Cartão', 'Banheiro', 'Lanchonete']
  }}
  isSelected={true}
/>
```

#### Timeline Linear
```typescript
<LinearTimeline>
  <TimelineMarker position={0} type="origin" label="São Paulo, SP" />
  <TimelineMarker position={52} type="gas_station" label="Posto Ipiranga" />
  <TimelineMarker position={87} type="city" label="Jacareí" />
  <TimelineMarker position={156} type="restaurant" label="McDonald's" />
  <TimelineMarker position={429} type="destination" label="Rio de Janeiro, RJ" />
</LinearTimeline>
```

#### Filtros de POI
```typescript
<POIFilters>
  <FilterChip 
    icon="⛽" 
    label="Postos" 
    count={12} 
    isActive={true}
    color="green"
  />
  <FilterChip 
    icon="🍽️" 
    label="Restaurantes" 
    count={8} 
    isActive={false}
    color="orange"
  />
  <FilterChip 
    icon="🏙️" 
    label="Cidades" 
    count={5} 
    isActive={true}
    color="indigo"
  />
</POIFilters>
```

## Interações e Fluxos

### Fluxo Principal: Criação de Mapa Linear

1. **Home Page**
   - Usuário insere origem e destino
   - Seleciona tipos de POI desejados
   - Clica em "Criar Mapa Linear"

2. **Loading State**
   - Exibe progress bar com etapas:
     - "Buscando rota..."
     - "Encontrando postos de combustível..."
     - "Localizando restaurantes..."
     - "Calculando distâncias..."

3. **Mapa Linear**
   - Apresenta timeline linear da viagem
   - POIs distribuídos por distância
   - Card com resumo da viagem

### Interações na Timeline

#### Hover em POI
- **Desktop**: Hover mostra preview rápido com nome, distância e rating
- **Mobile**: Tap curto mostra preview, tap longo seleciona

#### Seleção de POI
- POI selecionado fica destacado na timeline
- Card de detalhes aparece na parte inferior
- Opções: "Como Chegar", "Favoritar", "Mais Informações"

#### Zoom e Navegação
- **Scroll Horizontal**: Navegar pela timeline
- **Zoom Controls**: Aproximar/afastar para ver mais detalhes
- **Jump to Distance**: Input para ir direto para um KM específico

### Estados de Interface

#### Estados de Loading
```typescript
// Loading inicial
<RouteLoader steps={[
  'Calculando rota...',
  'Buscando postos de combustível...',
  'Encontrando restaurantes...',
  'Finalizando...'
]} />

// Loading de POI individual
<POICard isLoading={true} skeleton={true} />
```

#### Estados de Erro
```typescript
// Erro de rota não encontrada
<ErrorState 
  title="Rota não encontrada"
  message="Não conseguimos encontrar uma rota entre os pontos informados"
  action="Tentar novamente"
/>

// Erro de API
<ErrorState 
  title="Erro temporário"
  message="Tivemos um problema ao buscar os dados. Tente novamente em alguns instantes."
  action="Recarregar"
/>
```

#### Estados Vazios
```typescript
// Nenhum POI encontrado
<EmptyState 
  icon="🔍"
  title="Nenhum resultado encontrado"
  message="Tente ajustar os filtros ou verificar se a rota está correta"
/>
```

## Responsividade

### Breakpoints
- **Mobile**: 320px - 767px
- **Tablet**: 768px - 1023px  
- **Desktop**: 1024px+

### Layout Adaptivo

#### Mobile (Portrait)
- Timeline vertical em vez de horizontal
- Cards de POI em lista stack
- Navigation drawer para filtros
- Bottom sheet para detalhes de POI

#### Mobile (Landscape)
- Timeline horizontal compacta
- Detalhes de POI em side panel
- Controles de zoom otimizados para touch

#### Tablet
- Layout híbrido entre mobile e desktop
- Timeline horizontal com mais espaço
- Side panel para filtros sempre visível

#### Desktop
- Timeline horizontal completa
- Side panels para filtros e detalhes
- Hover states e tooltips
- Keyboard shortcuts

## Acessibilidade

### Navegação por Teclado
- **Tab**: Navegar entre POIs na timeline
- **Enter/Space**: Selecionar POI
- **Arrow Keys**: Navegar na timeline
- **Esc**: Fechar modals/overlays

### Screen Readers
- Labels descritivos para todos os elementos interativos
- Landmarks para navegação (main, navigation, complementary)
- Live regions para updates dinâmicos
- Alt text para ícones e imagens

### Contraste e Legibilidade
- Ratio mínimo de 4.5:1 para texto normal
- Ratio mínimo de 3:1 para texto grande
- Ícones com alternativas textuais
- Estados de foco bem definidos

## Performance

### Estratégias de Otimização

#### Carregamento de Dados
- **Lazy Loading**: POIs carregados conforme viewport
- **Pagination**: Timeline dividida em segmentos
- **Caching**: Cache de rotas recentes
- **Prefetch**: Dados de POIs próximos ao viewport

#### Renderização
- **Virtualization**: Apenas POIs visíveis renderizados
- **Memoization**: Componentes de POI otimizados
- **Image Optimization**: Ícones e logos otimizados

#### Offline Support
- **Service Worker**: Cache de dados básicos
- **Progressive Enhancement**: Funcionalidade básica sem conexão
- **Sync**: Sincronização quando conexão retornar

## Métricas e Analytics

### KPIs de Produto
- **Taxa de Conversão**: % de buscas que geram mapas
- **Engagement**: Tempo médio na timeline
- **Utilidade**: % de POIs que recebem cliques
- **Retenção**: Usuários que retornam

### Eventos de Tracking
```typescript
// Busca realizada
analytics.track('route_search', {
  origin: 'São Paulo, SP',
  destination: 'Rio de Janeiro, RJ',
  poi_types: ['gas_station', 'restaurant'],
  total_distance: 429
});

// POI selecionado
analytics.track('poi_selected', {
  poi_type: 'gas_station',
  poi_name: 'Posto Ipiranga',
  distance_from_origin: 52,
  route_id: 'route_123'
});

// Ação tomada
analytics.track('poi_action', {
  action: 'get_directions',
  poi_id: 'poi_456',
  user_position: 45 // km da origem
});
```

## Considerações Técnicas

### Stack Tecnológico Recomendado
- **Framework**: Next.js 14 com App Router
- **Styling**: TailwindCSS + CSS Modules para componentes específicos
- **Maps**: Leaflet + OpenStreetMap tiles
- **State**: Zustand para estado global, React Query para server state
- **Forms**: React Hook Form + Zod validation
- **Icons**: Lucide React + emojis para POI types

### Integração com Backend
- **API Calls**: Axios com interceptors
- **Real-time**: WebSockets para progress updates
- **Caching**: React Query com stale-while-revalidate
- **Error Handling**: Toast notifications + retry logic

### Browser Support
- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Progressive Enhancement**: Funcionalidade básica em browsers antigos
- **Polyfills**: Para features modernas quando necessário

---

Este documento de design serve como referência principal para o desenvolvimento do frontend, estabelecendo a visão, padrões e especificações técnicas necessárias para criar uma experiência consistente e útil para os usuários do MapaLinear.