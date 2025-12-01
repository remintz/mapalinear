# PRD: Migração para PostgreSQL com SQLAlchemy e Alembic

**Status:** APROVADO
**Data:** 2025-11-30
**Autor:** Claude Code

---

## 1. Resumo Executivo

Migrar o armazenamento de mapas e POIs de arquivos JSON para PostgreSQL, usando SQLAlchemy ORM e Alembic para migrações. O cache geográfico existente também será migrado para SQLAlchemy.

### Escopo

| Item | Status | Descrição |
|------|--------|-----------|
| Mapas | ✅ Incluído | Atualmente em `saved_maps/*.json` |
| POIs | ✅ Incluído | Tabela separada, normalizada |
| Cache geográfico | ✅ Incluído | Migrar de SQL puro para SQLAlchemy |
| Async operations | ❌ Excluído | Permanecem em arquivos JSON |

---

## 2. Schema do Banco de Dados

### 2.1 Diagrama ERD

```
┌─────────────────────┐       ┌─────────────────────┐
│       maps          │       │        pois         │
├─────────────────────┤       ├─────────────────────┤
│ id (UUID) PK        │       │ id (UUID) PK        │
│ origin              │       │ osm_id (unique)     │
│ destination         │       │ name                │
│ total_length_km     │       │ type (enum)         │
│ road_id             │       │ latitude            │
│ created_at          │       │ longitude           │
│ updated_at          │       │ city                │
│ segments (JSONB)    │       │ operator            │
│ metadata (JSONB)    │       │ brand               │
└─────────┬───────────┘       │ opening_hours       │
          │                   │ phone               │
          │                   │ website             │
          │                   │ amenities (JSONB)   │
          │                   │ tags (JSONB)        │
          │                   │ created_at          │
          │                   │ updated_at          │
          │                   └─────────┬───────────┘
          │                             │
          │    ┌────────────────────────┘
          │    │
          ▼    ▼
┌─────────────────────┐
│    map_pois         │
│  (junction table)   │
├─────────────────────┤
│ id (UUID) PK        │
│ map_id FK           │
│ poi_id FK           │
│ segment_index (int) │
│ distance_from_origin│
│ distance_from_road  │
│ side (left/right)   │
│ junction_distance   │
│ junction_lat        │
│ junction_lon        │
│ requires_detour     │
│ quality_score       │
└─────────────────────┘

┌─────────────────────┐
│   cache_entries     │
├─────────────────────┤
│ key (TEXT) PK       │
│ data (JSONB)        │
│ provider            │
│ operation           │
│ params (JSONB)      │
│ created_at          │
│ expires_at          │
│ hit_count           │
└─────────────────────┘
```

### 2.2 Decisões de Design

| Decisão | Justificativa |
|---------|---------------|
| Segments como JSONB | Simplifica schema, segmentos são sempre acessados via mapa |
| Geometry como JSONB | Sem PostGIS - suficiente para o caso de uso atual |
| POIs normalizados | Tabela separada permite reutilização entre mapas |

### 2.3 Relacionamentos

- **Map ↔ POIs**: N:M via `map_pois` (um POI pode aparecer em vários mapas)
- **MapPOI → Segment**: Via `segment_index` (índice do segmento no array JSONB)

---

## 3. Estrutura de Arquivos

```
api/
├── database/
│   ├── __init__.py           # Exporta engine, session, Base
│   ├── connection.py         # AsyncEngine, async_session_maker
│   └── models/
│       ├── __init__.py       # Exporta todos os models
│       ├── map.py            # Map (segments como JSONB)
│       ├── poi.py            # POI, MilestoneType enum
│       ├── map_poi.py        # MapPOI (tabela associativa)
│       └── cache.py          # CacheEntry
├── repositories/
│   ├── __init__.py
│   ├── base.py               # BaseRepository (CRUD genérico async)
│   ├── map_repository.py     # MapRepository
│   ├── poi_repository.py     # POIRepository
│   └── cache_repository.py   # CacheRepository
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
└── alembic.ini (na raiz do projeto)
```

---

## 4. SQLAlchemy Models

### 4.1 Connection e Base

```python
# api/database/connection.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

### 4.2 Map Model

```python
# api/database/models/map.py
class Map(Base):
    __tablename__ = "maps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    origin: Mapped[str]
    destination: Mapped[str]
    total_length_km: Mapped[float]
    road_id: Mapped[Optional[str]]
    segments: Mapped[list] = mapped_column(JSONB, default=[])  # LinearRoadSegment[] como JSONB
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default={})

    # Relationships
    map_pois: Mapped[List["MapPOI"]] = relationship(back_populates="map", cascade="all, delete-orphan")

    # Helper para converter para Pydantic
    def to_linear_map_response(self) -> "LinearMapResponse": ...
```

### 4.3 POI Model

```python
# api/database/models/poi.py
class POI(Base):
    __tablename__ = "pois"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    osm_id: Mapped[Optional[str]] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(index=True)
    type: Mapped[str]  # MilestoneType.value
    latitude: Mapped[float]
    longitude: Mapped[float]
    city: Mapped[Optional[str]] = mapped_column(index=True)
    operator: Mapped[Optional[str]]
    brand: Mapped[Optional[str]] = mapped_column(index=True)
    opening_hours: Mapped[Optional[str]]
    phone: Mapped[Optional[str]]
    website: Mapped[Optional[str]]
    amenities: Mapped[list] = mapped_column(JSONB, default=[])
    tags: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # Relationships
    map_pois: Mapped[List["MapPOI"]] = relationship(back_populates="poi")

    # Helper para converter para Pydantic RoadMilestone
    def to_road_milestone(self, map_poi: "MapPOI") -> "RoadMilestone": ...
```

### 4.4 MapPOI (Tabela Associativa)

```python
# api/database/models/map_poi.py
class MapPOI(Base):
    __tablename__ = "map_pois"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    map_id: Mapped[UUID] = mapped_column(ForeignKey("maps.id", ondelete="CASCADE"), index=True)
    poi_id: Mapped[UUID] = mapped_column(ForeignKey("pois.id", ondelete="CASCADE"), index=True)
    segment_index: Mapped[Optional[int]]  # Índice no array segments JSONB

    distance_from_origin_km: Mapped[float]
    distance_from_road_meters: Mapped[float]
    side: Mapped[str]  # "left", "right", "center"
    junction_distance_km: Mapped[Optional[float]]
    junction_lat: Mapped[Optional[float]]
    junction_lon: Mapped[Optional[float]]
    requires_detour: Mapped[bool] = mapped_column(default=False)
    quality_score: Mapped[Optional[float]]

    # Relationships
    map: Mapped["Map"] = relationship(back_populates="map_pois")
    poi: Mapped["POI"] = relationship(back_populates="map_pois")

    # Índice composto para queries de mapa
    __table_args__ = (
        Index("idx_map_pois_map_distance", "map_id", "distance_from_origin_km"),
    )
```

### 4.5 CacheEntry Model

```python
# api/database/models/cache.py
class CacheEntry(Base):
    __tablename__ = "cache_entries"

    key: Mapped[str] = mapped_column(primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(index=True)
    operation: Mapped[str] = mapped_column(index=True)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime] = mapped_column(index=True)
    hit_count: Mapped[int] = mapped_column(default=0)

    __table_args__ = (
        Index("idx_cache_operation_expires", "operation", "expires_at"),
    )
```

---

## 5. Plano de Implementação

### Fase 1: Setup Básico (SQLAlchemy + Alembic)

1. **Adicionar dependências ao `pyproject.toml`:**
   ```toml
   sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
   alembic = "^1.13"
   # asyncpg já existe
   ```

2. **Criar estrutura de diretórios:**
   ```bash
   mkdir -p api/database/models
   mkdir -p api/repositories
   mkdir -p api/alembic/versions
   ```

3. **Configurar Alembic:**
   - Criar `alembic.ini` na raiz
   - Configurar `api/alembic/env.py` para async com SQLAlchemy 2.0
   - Target metadata do Base

### Fase 2: Models e Repositories

4. **Implementar SQLAlchemy models:**
   - `Map` (com segments como JSONB)
   - `POI` (normalizado)
   - `MapPOI` (tabela associativa com dados de posição)
   - `CacheEntry` (mesmo schema atual)

5. **Implementar repositories (async):**
   - `BaseRepository`: CRUD genérico async
   - `MapRepository`: `create`, `get`, `list`, `delete`, `get_with_pois`
   - `POIRepository`: `get_or_create_by_osm_id`, `find_by_location`, `bulk_create`
   - `CacheRepository`: `get`, `set`, `delete`, `cleanup_expired`

### Fase 3: Integração com Services

6. **Atualizar `MapStorageService`:**
   - Usar `MapRepository` ao invés de arquivos JSON
   - Extrair POIs dos milestones e salvar na tabela `pois`
   - Criar relacionamentos via `map_pois`
   - Manter interface pública compatível

7. **Atualizar `UnifiedCache`:**
   - Usar `CacheRepository` ao invés de SQL puro com asyncpg
   - Manter lógica de matching semântico/espacial
   - Simplificar gerenciamento de conexões

8. **Atualizar `RoadService`:**
   - Ao salvar mapa, extrair POIs únicos (por osm_id)
   - Criar/reutilizar POIs existentes
   - Associar via MapPOI com dados de posição

### Fase 4: Alembic e Cleanup

9. **Criar migration inicial:**
   ```bash
   alembic revision --autogenerate -m "initial_schema"
   ```

10. **Atualizar Makefile:**
    ```makefile
    db-migrate:    # Criar nova migration
    db-upgrade:    # Aplicar migrations
    db-downgrade:  # Reverter migration
    db-current:    # Mostrar versão atual
    ```

11. **Cleanup:**
    - Remover `api/providers/cache_schema.sql` (substituído por Alembic)

---

## 6. Arquivos a Criar/Modificar

### Criar (15 arquivos)

```
api/database/
├── __init__.py              # Exporta engine, session, Base
├── connection.py            # AsyncEngine, session factory, get_session()
└── models/
    ├── __init__.py          # Exporta todos os models
    ├── map.py               # Map model
    ├── poi.py               # POI model
    ├── map_poi.py           # MapPOI model
    └── cache.py             # CacheEntry model

api/repositories/
├── __init__.py              # Exporta todos os repositories
├── base.py                  # BaseRepository[T] genérico async
├── map_repository.py        # MapRepository
├── poi_repository.py        # POIRepository
└── cache_repository.py      # CacheRepository

api/alembic/
├── env.py                   # Configuração async para Alembic
├── script.py.mako           # Template de migrations
└── versions/
    └── 001_initial_schema.py  # Migration inicial

alembic.ini                  # Config principal do Alembic
```

### Modificar (6 arquivos)

| Arquivo | Mudança |
|---------|---------|
| `pyproject.toml` | Adicionar SQLAlchemy 2.0 e Alembic |
| `api/services/map_storage_service.py` | Usar MapRepository + POIRepository |
| `api/providers/cache.py` | Usar CacheRepository ao invés de asyncpg direto |
| `api/services/road_service.py` | Extrair POIs ao salvar mapa |
| `Makefile` | Comandos para Alembic |
| `api/main.py` | Inicializar engine na startup |

### Remover

- `api/providers/cache_schema.sql` → substituído por Alembic

---

## 7. Conversão de Models

### Pydantic ↔ SQLAlchemy

| Pydantic Model | SQLAlchemy Model | Estratégia |
|----------------|------------------|------------|
| `LinearMapResponse` | `Map` | Segments como JSONB, POIs via relacionamento |
| `LinearRoadSegment` | JSONB em `Map.segments` | Serializado/deserializado automaticamente |
| `RoadMilestone` | `POI` + `MapPOI` | POI normalizado, posição no MapPOI |
| `CacheEntry` (existente) | `CacheEntry` | Mesmo schema, migrar para SQLAlchemy |

### Métodos de Conversão

```python
# Map model
class Map(Base):
    def to_linear_map_response(self) -> LinearMapResponse:
        """Converte para Pydantic incluindo POIs como milestones"""
        milestones = [mp.poi.to_road_milestone(mp) for mp in self.map_pois]
        return LinearMapResponse(
            id=str(self.id),
            origin=self.origin,
            destination=self.destination,
            total_length_km=self.total_length_km,
            segments=[LinearRoadSegment(**s) for s in self.segments],
            milestones=milestones,
            creation_date=self.created_at,
        )

    @classmethod
    def from_linear_map_response(cls, response: LinearMapResponse) -> "Map":
        """Cria Map a partir de Pydantic (sem POIs - tratados separadamente)"""
        return cls(
            id=UUID(response.id) if response.id else uuid4(),
            origin=response.origin,
            destination=response.destination,
            total_length_km=response.total_length_km,
            segments=[s.model_dump() for s in response.segments],
        )
```

---

## 8. Ordem de Execução

| # | Fase | Descrição |
|---|------|-----------|
| 1 | Setup | Dependências + estrutura de diretórios |
| 2 | Database | connection.py + Base |
| 3 | Models | Map, POI, MapPOI, CacheEntry |
| 4 | Alembic | Configuração + migration inicial |
| 5 | Repositories | Base, Map, POI, Cache |
| 6 | Integração | Atualizar services existentes |
| 7 | Testes | Verificar API existente |
| 8 | Cleanup | Remover arquivos obsoletos |

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Performance degradada | Média | Médio | Índices em `osm_id`, `map_id`, `distance_from_origin_km` |
| Quebra de API | Média | Alto | Manter interface pública dos services inalterada |
| POIs duplicados | Baixa | Baixo | `osm_id` como unique constraint + get_or_create |

---

## 10. Dependências Técnicas

### Versões Requeridas

```toml
[tool.poetry.dependencies]
python = "^3.11"
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
alembic = "^1.13"
asyncpg = "^0.29"  # já existente
```

### Variáveis de Ambiente

Reutiliza as existentes:
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DATABASE`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
