# PRD: Refactoring para Suporte Multi-Provider de APIs Geográficas

## 1. Resumo Executivo

### Visão Geral
Este documento descreve o refactoring da arquitetura do MapaLinear para permitir o uso de múltiplos provedores de dados geográficos, possibilitando escolher entre OpenStreetMap (OSM), HERE Maps, TomTom e outros provedores conforme a necessidade e custo-benefício.

### Motivação
- **Limitações do OSM**: Taxa de requisições limitada, dados inconsistentes em algumas regiões
- **Flexibilidade de Negócio**: Possibilidade de escolher o provider mais adequado para cada caso de uso
- **Qualidade de Dados**: Acesso a POIs comerciais mais precisos e atualizados
- **Escalabilidade**: Preparar a plataforma para crescimento com opções de providers

### Contexto de Uso
O MapaLinear opera em dois modos distintos:
1. **Geração do mapa** (online): Busca dados do provider selecionado e gera o mapa linear
2. **Acompanhamento da viagem** (offline): Usa apenas GPS local com dados previamente baixados

## 2. Contexto e Problema

### Estado Atual
O MapaLinear atualmente está fortemente acoplado ao ecossistema OSM:
- **Overpass API**: Queries complexas para busca de dados
- **OSMnx**: Manipulação de grafos e roteamento
- **Nominatim**: Geocoding e reverse geocoding
- **Dependência direta**: 790+ linhas em `OSMService` com lógica específica do OSM

### Problemas Identificados
1. **Acoplamento forte**: Lógica de negócio misturada com implementação OSM
2. **Limitações de rate limiting**: Overpass API tem limites restritivos
3. **Falta de dados comerciais**: POIs comerciais incompletos ou desatualizados
4. **Inflexibilidade**: Impossível escolher provider mais adequado para cada situação
5. **Custo de oportunidade**: Não aproveita vantagens específicas de cada provider

## 3. Objetivos

### Objetivos Primários
1. **Criar abstração de provider**: Interface comum para todos os provedores
2. **Implementar HERE Maps**: Primeiro provider comercial alternativo
3. **Seleção configurável**: Escolher provider via configuração
4. **Cache unificado**: Otimizar uso de APIs e reduzir custos

### Objetivos Secundários
1. **Melhorar performance**: Reduzir latência com cache inteligente
2. **Reduzir custos**: Reutilizar dados cacheados entre requisições similares
3. **Preparar para expansão**: Facilitar adição de novos providers

## 4. Escopo

### Incluído
- ✅ Criação de interface abstrata `GeoProvider`
- ✅ Implementação de `OSMProvider` (refactoring do código atual)
- ✅ Implementação de `HEREProvider` 
- ✅ Sistema de configuração para seleção de provider
- ✅ Cache unificado com estratégias inteligentes
- ✅ Testes unitários e de integração

### Excluído
- ❌ Implementação de TomTom (fase 2)
- ❌ Implementação de Google Maps (fase 3)
- ❌ Fallback automático entre providers
- ❌ Dados de tráfego em tempo real
- ❌ Interface de configuração no frontend (será via ENV vars)

## 5. Solução Proposta

### Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────┐
│                     API Layer                           │
│                  (FastAPI Routes)                       │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                  Service Layer                          │
│         (RoadService, POIService, etc.)                 │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│              GeoProvider Factory                        │
│         (Provider instantiation based on config)        │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────┐
        │                     │              │
┌───────▼────────┐ ┌─────────▼──────┐ ┌─────▼──────┐
│  OSMProvider   │ │  HEREProvider  │ │ TomTomProv │
│                │ │                │ │  (Future)  │
└───────┬────────┘ └─────────┬──────┘ └─────┬──────┘
        │                     │              │
┌───────▼────────────────────▼──────────────▼────────┐
│              Unified Cache Layer                    │
│        (Redis/Memory with provider-aware keys)      │
└──────────────────────────────────────────────────────┘
```

### Interface Principal

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum

class ProviderType(Enum):
    OSM = "osm"
    HERE = "here"
    TOMTOM = "tomtom"

class GeoLocation(BaseModel):
    """Unified location representation"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "Brasil"

class Route(BaseModel):
    """Unified route representation"""
    distance: float = Field(..., ge=0, description="Distance in km")
    duration: float = Field(..., ge=0, description="Duration in minutes")
    geometry: List[Tuple[float, float]] = Field(..., description="[(lat, lon), ...]")
    segments: List['RouteSegment'] = Field(default_factory=list)
    
class POI(BaseModel):
    """Unified POI representation"""
    id: str
    name: str
    location: GeoLocation
    category: str
    subcategory: Optional[str] = None
    amenities: List[str] = Field(default_factory=list)
    rating: Optional[float] = Field(None, ge=0, le=5)
    is_open: Optional[bool] = None
    provider_specific: Dict = Field(default_factory=dict, description="Provider-specific data")

class GeoProvider(ABC):
    """Abstract base class for geographic data providers"""
    
    @abstractmethod
    async def geocode(self, address: str) -> Optional[GeoLocation]:
        """Convert address to coordinates"""
        pass
    
    @abstractmethod
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[GeoLocation]:
        """Convert coordinates to address"""
        pass
    
    @abstractmethod
    async def calculate_route(
        self, 
        origin: GeoLocation, 
        destination: GeoLocation,
        waypoints: Optional[List[GeoLocation]] = None,
        avoid: Optional[List[str]] = None  # tolls, highways, ferries
    ) -> Optional[Route]:
        """Calculate route between points"""
        pass
    
    @abstractmethod
    async def search_pois(
        self,
        location: GeoLocation,
        radius: float,  # meters
        categories: List[str],
        limit: int = 50
    ) -> List[POI]:
        """Search for POIs around a location"""
        pass
    
    @abstractmethod
    async def get_poi_details(self, poi_id: str) -> Optional[POI]:
        """Get detailed information about a POI"""
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type"""
        pass
    
    @property
    @abstractmethod
    def supports_offline_export(self) -> bool:
        """Whether provider data can be exported for offline use"""
        pass
```

### Cache Unificado - Detalhamento

O cache unificado é um componente crítico para otimizar performance e reduzir custos. Ele funciona independentemente do provider utilizado, armazenando resultados de forma normalizada.

#### Estrutura do Cache

```python
from typing import Optional, Any
import hashlib
import json
from datetime import datetime, timedelta
from pydantic import BaseModel

class CacheKey(BaseModel):
    """Estrutura para gerar chaves de cache consistentes"""
    provider: ProviderType
    operation: str  # geocode, route, poi_search
    params: Dict[str, Any]
    
    def generate_key(self) -> str:
        """Gera chave única baseada nos parâmetros"""
        # Normaliza parâmetros para garantir consistência
        normalized = json.dumps(self.params, sort_keys=True)
        param_hash = hashlib.md5(normalized.encode()).hexdigest()
        return f"{self.provider.value}:{self.operation}:{param_hash}"

class CacheEntry(BaseModel):
    """Entrada do cache com metadados"""
    key: str
    data: Any
    provider: ProviderType
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    
class UnifiedCache:
    """
    Cache unificado para todos os providers.
    
    Estratégias de cache:
    1. Provider-aware: Cada provider tem seu namespace
    2. Semantic matching: Busca por similaridade (ex: "São Paulo, SP" = "Sao Paulo SP")
    3. Geospatial indexing: POIs próximos são agrupados
    4. TTL dinâmico: Ajusta expiração baseado em tipo de dado
    """
    
    def __init__(self, backend: str = "memory"):
        if backend == "redis":
            self.backend = RedisCache()
        else:
            self.backend = InMemoryCache()
        
        # TTLs por tipo de operação (em segundos)
        self.ttl_config = {
            "geocode": 86400 * 7,   # 7 dias - endereços não mudam frequentemente
            "route": 3600 * 6,      # 6 horas - rotas podem mudar com obras
            "poi_search": 86400,    # 1 dia - POIs mudam ocasionalmente
            "poi_details": 3600 * 12 # 12 horas - detalhes de POI
        }
    
    async def get(self, provider: ProviderType, operation: str, params: Dict) -> Optional[Any]:
        """
        Busca no cache com fallback para providers similares.
        
        Exemplo: Se buscando rota com HERE e não encontrar,
        verifica se existe resultado de OSM para mesma rota (se configurado).
        """
        # Gera chave primária
        key = CacheKey(provider=provider, operation=operation, params=params)
        primary_key = key.generate_key()
        
        # Tenta buscar exato
        entry = await self.backend.get(primary_key)
        if entry and entry.expires_at > datetime.utcnow():
            entry.hit_count += 1
            await self.backend.update_stats(primary_key, entry)
            return entry.data
        
        # Para geocoding, tenta match semântico
        if operation == "geocode" and "address" in params:
            similar_key = await self._find_similar_geocode(params["address"])
            if similar_key:
                entry = await self.backend.get(similar_key)
                if entry and entry.expires_at > datetime.utcnow():
                    return entry.data
        
        return None
    
    async def set(self, provider: ProviderType, operation: str, 
                  params: Dict, data: Any) -> None:
        """Armazena resultado no cache com TTL apropriado"""
        key = CacheKey(provider=provider, operation=operation, params=params)
        ttl = self.ttl_config.get(operation, 3600)
        
        entry = CacheEntry(
            key=key.generate_key(),
            data=data,
            provider=provider,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
            hit_count=0
        )
        
        await self.backend.set(entry.key, entry)
        
        # Para POIs, também indexa geograficamente
        if operation == "poi_search":
            await self._index_pois_geospatially(params, data)
    
    async def _find_similar_geocode(self, address: str) -> Optional[str]:
        """
        Busca endereços similares no cache.
        Ex: "Av. Paulista, São Paulo" pode match com "Avenida Paulista, SP"
        """
        # Normaliza endereço
        normalized = self._normalize_address(address)
        
        # Busca por padrões similares
        patterns = await self.backend.search_pattern(f"*:geocode:*")
        for pattern_key in patterns:
            entry = await self.backend.get(pattern_key)
            if entry and self._is_similar_address(normalized, entry.params.get("address", "")):
                return pattern_key
        
        return None
    
    def _normalize_address(self, address: str) -> str:
        """Normaliza endereço para comparação"""
        # Remove acentos, pontuação, padroniza abreviações
        replacements = {
            "avenida": "av",
            "rua": "r",
            "praça": "pca",
            "são": "sao",
            # etc...
        }
        normalized = address.lower()
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        return normalized
```

#### Benefícios do Cache Unificado

1. **Redução de Custos**: Menos chamadas às APIs pagas
2. **Performance**: Respostas instantâneas para dados cacheados  
3. **Resiliência**: Continua funcionando mesmo com provider offline (dados cacheados)
4. **Inteligência**: Aproveita dados similares entre providers
5. **Offline Mode**: Dados cacheados podem ser exportados para uso offline

## 6. Requisitos Funcionais

### RF1: Abstração de Provider
- **RF1.1**: Sistema deve permitir configuração de provider via variáveis de ambiente
- **RF1.2**: Providers devem implementar interface comum `GeoProvider`

### RF2: Implementação OSM Provider
- **RF2.1**: Manter toda funcionalidade atual do OSM
- **RF2.2**: Refatorar código existente para nova arquitetura
- **RF2.3**: Migrar para cache unificado

### RF3: Implementação HERE Provider
- **RF3.1**: Implementar geocoding via HERE Geocoding API
- **RF3.2**: Implementar roteamento via HERE Routing API v8
- **RF3.3**: Implementar busca de POIs via HERE Places API
- **RF3.4**: Exportar dados para uso offline no app

### RF4: Sistema de Configuração
- **RF4.1**: Seleção de provider via variável de ambiente
- **RF4.2**: Logging detalhado de uso por provider
- **RF4.3**: Métricas de performance e custos

### RF5: Cache Unificado
- **RF5.1**: Cache deve funcionar independente do provider
- **RF5.2**: TTL configurável por tipo de dado
- **RF5.3**: Possibilidade de invalidar cache seletivamente

## 7. Requisitos Não-Funcionais

### Performance
- **RNF1**: Processamento interno de dados geográficos < 100ms (p95)
- **RNF2**: Transformação e normalização de respostas < 50ms 
- **RNF3**: Cache hit rate > 60% após warm-up

### Confiabilidade
- **RNF4**: Disponibilidade > 99% do provider selecionado
- **RNF5**: Timeout configurável por tipo de operação

### Escalabilidade
- **RNF6**: Configuração sem necessidade de redeploy

### Segurança
- **RNF7**: API keys armazenadas seguramente (env vars/secrets)
- **RNF8**: Métricas de rate de requisições enviadas para providers
- **RNF9**: Não vazar informações de provider nas respostas

### Manutenibilidade
- **RNF10**: Cobertura de testes > 90%
- **RNF11**: Documentação completa de cada provider
- **RNF12**: Logs estruturados para debugging

## 8. Plano de Implementação

### Fase 1: Preparação (Sprint 1)
1. **Semana 1-2**: 
   - Criar estrutura de diretórios `api/providers/`
   - Definir interfaces base (`GeoProvider`, modelos unificados)
   - Setup de testes unitários

### Fase 2: Refactoring OSM (Sprint 2)
2. **Semana 3-4**:
   - Extrair lógica OSM para `OSMProvider`
   - Implementar `GeoProviderManager`
   - Manter retrocompatibilidade com código existente
   - Testes de regressão

### Fase 3: Implementação HERE (Sprint 3-4)
3. **Semana 5-6**:
   - Implementar `HEREProvider`
   - Integrar HERE REST APIs
   - Mapear modelos HERE para modelos unificados

4. **Semana 7-8**:
   - Implementar sistema de fallback
   - Cache unificado
   - Testes de integração

### Fase 4: Deploy e Monitoramento (Sprint 5)
5. **Semana 9-10**:
   - Deploy em staging
   - Configuração de monitoramento
   - Documentação
   - Deploy em produção

## 9. Configuração Proposta

### Variáveis de Ambiente

```bash
# Provider Configuration
GEO_PRIMARY_PROVIDER=here  # osm, here, tomtom
GEO_FALLBACK_PROVIDERS=osm,tomtom  # comma-separated list

# HERE Maps Configuration
HERE_API_KEY=your_here_api_key
HERE_APP_ID=your_app_id  # optional for some endpoints
HERE_APP_CODE=your_app_code  # optional

# OSM Configuration (existing)
OSM_OVERPASS_ENDPOINT=https://overpass-api.de/api/interpreter
OSM_NOMINATIM_ENDPOINT=https://nominatim.openstreetmap.org
OSM_USER_AGENT=mapalinear/1.0

# Cache Configuration
GEO_CACHE_TTL_GEOCODE=86400  # 24 hours
GEO_CACHE_TTL_ROUTE=3600  # 1 hour
GEO_CACHE_TTL_POI=7200  # 2 hours

# Rate Limiting
GEO_RATE_LIMIT_HERE=10  # requests per second
GEO_RATE_LIMIT_OSM=1  # requests per second
```

## 10. Exemplo de Uso

### Configuração Simples

```python
# api/services/road_service.py
from api.providers import create_provider

class RoadService:
    def __init__(self):
        # Provider selecionado via ENV var
        self.geo_provider = create_provider()
    
    async def generate_linear_map(self, origin: str, destination: str):
        # Uso transparente, independente do provider
        origin_location = await self.geo_provider.geocode(origin)
        destination_location = await self.geo_provider.geocode(destination)
        
        route = await self.geo_provider.calculate_route(
            origin_location, 
            destination_location
        )
        
        # Busca POIs ao longo da rota
        pois = []
        for segment in route.segments:
            segment_pois = await self.geo_provider.search_pois(
                location=segment.midpoint,
                radius=5000,
                categories=["gas_station", "restaurant", "hotel"]
            )
            pois.extend(segment_pois)
        
        return {
            "route": route,
            "pois": pois,
            "provider": self.geo_provider.provider_type.value
        }
```

## 11. Riscos e Mitigações

### Riscos Técnicos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Incompatibilidade de dados entre providers | Alta | Alto | Criar camada de normalização robusta |
| Aumento de complexidade | Média | Médio | Documentação extensa e testes |
| Performance degradada | Baixa | Médio | Cache agressivo e timeouts otimizados |
| Custos HERE Maps excedem orçamento | Média | Alto | Monitoramento de uso e alertas |

### Riscos de Negócio

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Diferenças na qualidade dos dados | Média | Médio | Documentar características de cada provider |
| Provider indisponível | Baixa | Alto | Cache robusto para operações críticas |

## 12. Métricas de Sucesso

### Métricas Técnicas
- **Flexibilidade**: Trocar de provider em < 1 minuto (mudança de ENV var)
- **Latência**: Mantida ou melhorada vs implementação atual
- **Cache hit rate**: >60%
- **Uptime**: >99% para provider selecionado

### Métricas de Negócio
- **Cobertura de POIs**: +40% mais POIs identificados
- **Precisão de rotas**: Rotas 15% mais precisas
- **Satisfação do usuário**: NPS aumenta 10 pontos

### Métricas de Desenvolvimento
- **Tempo para adicionar provider**: <5 dias
- **Cobertura de testes**: >85%
- **Bugs em produção**: <2 por sprint

## 13. Considerações de Segurança

### Gestão de API Keys
- Usar AWS Secrets Manager ou similar
- Rotação automática de keys
- Diferentes keys para dev/staging/prod

### Rate Limiting
- Implementar circuit breaker por provider
- Queue de requisições para evitar bursts
- Monitoring de quotas

## 14. Exemplo de Uso HERE Maps

### Geocoding
```python
class HEREProvider(GeoProvider):
    async def geocode(self, address: str) -> Optional[GeoLocation]:
        url = "https://geocode.search.hereapi.com/v1/geocode"
        params = {
            "q": address,
            "apiKey": self.api_key,
            "limit": 1
        }
        response = await self.http_client.get(url, params=params)
        # Parse and map to GeoLocation
```

### Routing
```python
async def calculate_route(self, origin: GeoLocation, destination: GeoLocation) -> Optional[Route]:
    url = "https://router.hereapi.com/v8/routes"
    params = {
        "transportMode": "car",
        "origin": f"{origin.latitude},{origin.longitude}",
        "destination": f"{destination.latitude},{destination.longitude}",
        "return": "polyline,summary,actions",
        "apiKey": self.api_key
    }
    response = await self.http_client.get(url, params=params)
    # Parse and map to Route
```

## 15. Próximos Passos

1. **Aprovação**: Revisar e aprovar este PRD
2. **Spike técnico**: POC com HERE Maps (2 dias)
3. **Refinamento**: Detalhar stories no Jira
4. **Kick-off**: Reunião com time de desenvolvimento
5. **Implementação**: Seguir plano das fases

## 16. Apêndices

### A. Comparação de Providers

| Feature | OSM | HERE | TomTom | Google |
|---------|-----|------|---------|---------|
| Geocoding | ✅ Grátis | ✅ 250k/mês grátis | ✅ 2.5k/dia grátis | ✅ $200/mês grátis |
| Routing | ✅ Básico | ✅ Com tráfego | ✅ Com tráfego | ✅ Com tráfego |
| POIs | ⚠️ Variável | ✅ Rico | ✅ Rico | ✅ Muito rico |
| Real-time | ❌ | ✅ | ✅ | ✅ |
| Brasil coverage | ⚠️ Médio | ✅ Bom | ✅ Bom | ✅ Excelente |
| Custo | Grátis | $$ | $$ | $$$ |

### B. Estrutura de Diretórios Proposta

```
api/
├── providers/
│   ├── __init__.py
│   ├── base.py           # GeoProvider interface
│   ├── models.py          # Unified models
│   ├── manager.py         # GeoProviderManager
│   ├── cache.py           # UnifiedCache
│   ├── osm/
│   │   ├── __init__.py
│   │   ├── provider.py    # OSMProvider
│   │   ├── models.py      # OSM-specific models
│   │   └── utils.py
│   ├── here/
│   │   ├── __init__.py
│   │   ├── provider.py    # HEREProvider
│   │   ├── models.py      # HERE-specific models
│   │   └── client.py      # HERE API client
│   └── tomtom/            # Future
│       └── ...
├── services/
│   ├── road_service.py    # Refactored to use providers
│   └── ...
└── ...
```

### C. Estimativas de Custo HERE Maps

Para 10.000 usuários ativos mensais:
- Geocoding: 50k requests = Grátis (dentro do limite)
- Routing: 100k requests = ~$100/mês
- Places: 50k requests = ~$50/mês
- **Total estimado**: $150/mês

### D. Referências

- [HERE Maps API Documentation](https://developer.here.com/documentation)
- [HERE Pricing](https://www.here.com/pricing)
- [OSM Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [Provider Pattern in Python](https://refactoring.guru/design-patterns/strategy/python/example)

---

**Documento criado por**: MapaLinear Team  
**Data**: 2025-08-15  
**Versão**: 1.2  
**Status**: REVISADO

## Changelog

### Versão 1.1 (2025-08-15)
- Removido sistema de fallback automático entre providers
- Removido suporte a tráfego em tempo real
- Alterado de dataclass para Pydantic em todos os modelos
- Expandida documentação do cache unificado com exemplos detalhados
- Removidas seções de migração de dados (app novo sem usuários)
- Simplificada arquitetura para seleção única de provider
- Adicionado contexto dos dois modos de operação (online/offline)

### Versão 1.2 (2025-08-15)
- Removido RF1.2 sobre ordem de fallback (não necessário)
- Ajustado RF2.2 para não exigir compatibilidade retroativa
- Revisados requisitos de performance para focar no processamento interno
- Removido RNF6 sobre tempo para adicionar provider
- Ajustado RNF9 para métricas ao invés de controle de rate limiting
- Aumentada cobertura de testes obrigatória para 90%