# Development Guidelines - MapaLinear

## Visão Geral

Este documento estabelece os padrões de desenvolvimento para o projeto MapaLinear, garantindo consistência, qualidade e manutenibilidade do código em todas as contribuições.

## Índice

1. [Padrões Gerais](#padrões-gerais)
2. [Backend (Python/FastAPI)](#backend-pythonfastapi)
3. [Frontend (NextJS/TypeScript)](#frontend-nextjstypescript)
4. [Estrutura de Arquivos](#estrutura-de-arquivos)
5. [Git e Versionamento](#git-e-versionamento)
6. [Testes](#testes)
7. [Documentação](#documentação)
8. [Performance e Segurança](#performance-e-segurança)

---

## Padrões Gerais

### Princípios Fundamentais

1. **Clareza sobre Cleverness**: Código legível é preferível a código "inteligente"
2. **DRY (Don't Repeat Yourself)**: Evite duplicação de código
3. **SOLID**: Siga os princípios SOLID de design
4. **Fail Fast**: Detecte e reporte erros o mais cedo possível
5. **Type Safety**: Use tipagem estática sempre que possível

### Nomenclatura

#### Linguagens Naturais
- **Português**: Para comentários, documentação e mensagens de usuário
- **Inglês**: Para nomes de variáveis, funções, classes e commits

#### Convenções de Nome
```python
# Classes: PascalCase
class OSMService:
class LinearMapRequest:

# Funções e variáveis: snake_case
def search_road_data():
user_location = "São Paulo, SP"

# Constantes: UPPER_SNAKE_CASE
API_BASE_URL = "https://api.example.com"
MAX_RETRY_ATTEMPTS = 3

# Arquivos: snake_case
road_service.py
osm_models.py

# Diretórios: snake_case
api/services/
frontend/components/
```

### Comentários e Documentação

```python
# ✅ Bom: Explica o "porquê"
# Cache the result to avoid expensive OSM API calls for the same route
result = cache.get(cache_key)

# ❌ Ruim: Explica o "o quê" (óbvio)
# Get result from cache
result = cache.get(cache_key)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância geodésica entre dois pontos usando a fórmula de Haversine.
    
    Args:
        lat1, lon1: Coordenadas do primeiro ponto em graus decimais
        lat2, lon2: Coordenadas do segundo ponto em graus decimais
    
    Returns:
        Distância em quilômetros
        
    Raises:
        ValueError: Se as coordenadas estão fora dos limites válidos
    """
```

---

## Backend (Python/FastAPI)

### Estrutura de Módulos

```python
# Ordem de imports
# 1. Built-in libraries
import os
import logging
from typing import List, Optional, Dict

# 2. Third-party libraries
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# 3. Local imports
from api.models.osm_models import Coordinates
from api.services.osm_service import OSMService
```

### Modelos Pydantic

```python
class ExampleRequest(BaseModel):
    """Modelo para requisições de exemplo."""
    
    # Sempre usar Field com description
    origin: str = Field(..., description="Ponto de origem (ex: 'São Paulo, SP')")
    destination: str = Field(..., description="Ponto de destino")
    
    # Valores opcionais com defaults
    max_distance: float = Field(1000, description="Distância máxima em metros", ge=100, le=10000)
    include_pois: bool = Field(True, description="Incluir pontos de interesse")
    
    # Listas e dicts com factory
    filters: List[str] = Field(default_factory=list, description="Filtros aplicados")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")
    
    class Config:
        # Exemplos para documentação da API
        schema_extra = {
            "example": {
                "origin": "Belo Horizonte, MG",
                "destination": "Ouro Preto, MG",
                "max_distance": 1500,
                "include_pois": True
            }
        }
```

### Serviços

```python
class ExampleService:
    """Serviço responsável por [descrição da responsabilidade]."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._api_client = self._initialize_client()
    
    def public_method(self, param: str) -> ResultType:
        """
        Método público com responsabilidade específica.
        
        Args:
            param: Descrição do parâmetro
            
        Returns:
            Descrição do retorno
            
        Raises:
            ValueError: Quando param é inválido
            APIException: Quando a API externa falha
        """
        try:
            self.logger.info(f"Iniciando operação para: {param}")
            
            # Validação de entrada
            if not param or not param.strip():
                raise ValueError("Parâmetro não pode estar vazio")
            
            # Lógica principal
            result = self._process_data(param)
            
            self.logger.info(f"Operação concluída com sucesso")
            return result
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
            raise APIException(f"Falha na operação: {str(e)}")
    
    def _process_data(self, data: str) -> ResultType:
        """Método auxiliar privado (prefixo _)."""
        # Implementação do processamento
        pass
```

### Roteadores FastAPI

```python
router = APIRouter(prefix="/example", tags=["example"])
service = ExampleService()

@router.post("/endpoint", response_model=ExampleResponse)
async def create_example(request: ExampleRequest):
    """
    Cria um novo exemplo baseado nos parâmetros fornecidos.
    
    - **origin**: Ponto de origem da busca
    - **destination**: Ponto de destino
    - **max_distance**: Raio máximo de busca em metros
    """
    try:
        result = service.process_request(
            origin=request.origin,
            destination=request.destination,
            max_distance=request.max_distance
        )
        return ExampleResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except APIException as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Tratamento de Erros

```python
# Exceções customizadas
class OSMAPIException(Exception):
    """Exceção para erros da API do OpenStreetMap."""
    pass

class RouteNotFoundException(Exception):
    """Exceção quando uma rota não é encontrada."""
    pass

# Middleware de tratamento global
@app.exception_handler(ValueError)
async def validation_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### Logging

```python
# Configuração de logger por módulo
logger = logging.getLogger(__name__)

# Padrões de log com contexto
logger.info(f"🔔 Iniciando busca: {origin} → {destination}")
logger.warning(f"⚠️ Cache miss para rota {route_id}")
logger.error(f"❌ Falha na API OSM: {error_message}")
logger.debug(f"🔍 Query retornou {len(results)} resultados")

# Use structured logging para dados importantes
logger.info("Route search completed", extra={
    "route_id": route_id,
    "origin": origin,
    "destination": destination,
    "duration_ms": duration,
    "pois_found": len(pois)
})
```

---

## Frontend (NextJS/TypeScript)

### Estrutura de Componentes

```typescript
// components/example/ExampleComponent.tsx
import React from 'react';
import { clsx } from 'clsx';

interface ExampleComponentProps {
  /** Título do componente */
  title: string;
  /** Descrição opcional */
  description?: string;
  /** Se o componente está em estado de loading */
  isLoading?: boolean;
  /** Callback chamado ao clicar */
  onClick?: () => void;
  /** Classes CSS adicionais */
  className?: string;
}

export function ExampleComponent({
  title,
  description,
  isLoading = false,
  onClick,
  className
}: ExampleComponentProps) {
  return (
    <div className={clsx("example-component", className)}>
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && (
        <p className="text-gray-600">{description}</p>
      )}
      {isLoading && <div>Carregando...</div>}
    </div>
  );
}

// Export default para componentes principais
export default ExampleComponent;
```

### Hooks Customizados

```typescript
// hooks/useRouteSearch.ts
import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';

interface UseRouteSearchParams {
  origin: string;
  destination: string;
}

interface RouteSearchResult {
  data: RouteData | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useRouteSearch({ origin, destination }: UseRouteSearchParams): RouteSearchResult {
  const {
    data,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['route-search', origin, destination],
    queryFn: () => apiClient.searchRoute({ origin, destination }),
    enabled: Boolean(origin && destination),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    data: data || null,
    isLoading,
    error,
    refetch
  };
}
```

### Types e Interfaces

```typescript
// types/api.ts

// Base types
export interface Coordinates {
  lat: number;
  lon: number;
}

export interface POI {
  id: string;
  name: string;
  type: POIType;
  coordinates: Coordinates;
  distance_from_origin_km: number;
  tags: Record<string, unknown>;
}

// Enums
export enum POIType {
  CITY = 'city',
  GAS_STATION = 'gas_station',
  RESTAURANT = 'restaurant',
  TOLL_BOOTH = 'toll_booth'
}

// API Request/Response types
export interface RouteSearchRequest {
  origin: string;
  destination: string;
  include_gas_stations?: boolean;
  include_restaurants?: boolean;
  max_distance?: number;
}

export interface RouteSearchResponse {
  id: string;
  origin: string;
  destination: string;
  total_distance_km: number;
  pois: POI[];
  segments: RouteSegment[];
}

// Component props interfaces
export interface RouteMapProps {
  route: RouteSearchResponse;
  selectedPOI?: string;
  onPOISelect?: (poiId: string) => void;
}
```

### Utilities e Helpers

```typescript
// lib/utils.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utilitário para combinar classes CSS com Tailwind
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formata distância para exibição
 */
export function formatDistance(distanceKm: number): string {
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)}m`;
  }
  return `${distanceKm.toFixed(1)}km`;
}

/**
 * Valida se uma string é um CEP brasileiro válido
 */
export function isValidCEP(cep: string): boolean {
  return /^\d{5}-?\d{3}$/.test(cep);
}
```

### API Client

```typescript
// lib/api.ts
import axios, { AxiosInstance } from 'axios';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
      timeout: 30000,
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.client.interceptors.request.use((config) => {
      // Add auth headers, request ID, etc.
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        // Global error handling
        console.error('API Error:', error);
        return Promise.reject(error);
      }
    );
  }

  async searchRoute(params: RouteSearchRequest): Promise<RouteSearchResponse> {
    const { data } = await this.client.post<RouteSearchResponse>('/linear-map', params);
    return data;
  }
}

export const apiClient = new APIClient();
```

---

## Estrutura de Arquivos

### Backend Structure

```
api/
├── main.py                 # FastAPI app configuration
├── run.py                  # Development server entry point
├── models/                 # Pydantic models
│   ├── __init__.py
│   ├── base.py            # Base models and common types
│   ├── osm_models.py      # OpenStreetMap related models
│   ├── road_models.py     # Road and route models
│   └── user_models.py     # User related models (future)
├── routers/               # API endpoints
│   ├── __init__.py
│   ├── health.py          # Health check endpoints
│   ├── osm_router.py      # OSM data endpoints
│   ├── road_router.py     # Route and road endpoints
│   └── operations_router.py # Async operations
├── services/              # Business logic
│   ├── __init__.py
│   ├── base.py            # Base service class
│   ├── osm_service.py     # OpenStreetMap API integration
│   ├── road_service.py    # Route processing logic
│   ├── cache_service.py   # Caching logic
│   └── async_service.py   # Async operations management
├── middleware/            # Custom middleware
│   ├── __init__.py
│   ├── error_handler.py   # Global error handling
│   ├── cors.py            # CORS configuration
│   └── logging.py         # Request logging
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── osm_utils.py       # OSM data processing utilities
│   ├── geo_utils.py       # Geographic calculations
│   └── cache_utils.py     # Cache management utilities
└── tests/                 # Test files
    ├── __init__.py
    ├── conftest.py        # Pytest configuration
    ├── test_services/     # Service tests
    ├── test_routers/      # Router tests
    └── test_utils/        # Utility tests
```

### Frontend Structure

```
frontend/
├── app/                   # Next.js 14 app directory
│   ├── globals.css
│   ├── layout.tsx
│   ├── page.tsx
│   ├── (routes)/          # Route groups
│   │   ├── search/
│   │   │   ├── page.tsx
│   │   │   └── loading.tsx
│   │   ├── map/
│   │   │   └── [id]/
│   │   │       ├── page.tsx
│   │   │       └── loading.tsx
│   │   └── history/
│   │       └── page.tsx
│   └── api/               # API routes (if needed)
├── components/            # Reusable components
│   ├── ui/                # Base UI components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── card.tsx
│   │   └── index.ts       # Re-exports
│   ├── forms/             # Form components
│   │   ├── SearchForm.tsx
│   │   └── FilterForm.tsx
│   ├── maps/              # Map related components
│   │   ├── RouteMap.tsx
│   │   ├── POIMarker.tsx
│   │   └── MapControls.tsx
│   └── layout/            # Layout components
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── Footer.tsx
├── lib/                   # Utilities and configurations
│   ├── api.ts             # API client
│   ├── types.ts           # TypeScript types
│   ├── utils.ts           # General utilities
│   ├── validations.ts     # Form validations with Zod
│   └── constants.ts       # App constants
├── hooks/                 # Custom React hooks
│   ├── useRouteSearch.ts
│   ├── useMap.ts
│   └── useLocalStorage.ts
├── styles/                # Additional styles
│   └── components.css
└── public/                # Static assets
    ├── icons/
    ├── images/
    └── favicon.ico
```

---

## Git e Versionamento

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

#### Types
- **feat**: Nova funcionalidade
- **fix**: Correção de bug
- **docs**: Mudanças na documentação
- **style**: Formatação, ponto e vírgula, etc.
- **refactor**: Refatoração de código
- **test**: Adição ou correção de testes
- **chore**: Manutenção, atualizações de dependências

#### Exemplos
```
feat(api): add POI filtering by distance

Add new endpoint parameter max_distance_meters to filter POIs
within specified radius from the route.

Closes #123

fix(frontend): resolve map rendering issue on mobile

The map component was not properly resizing on mobile devices
due to incorrect container height calculation.

docs(readme): update installation instructions

chore(deps): update fastapi to 0.110.1
```

### Branch Naming

```
# Feature branches
feature/poi-filtering
feature/map-improvements

# Bug fixes
fix/mobile-map-rendering
fix/api-timeout-issues

# Documentation
docs/api-documentation
docs/development-setup

# Releases
release/v1.2.0
```

### Pull Request Guidelines

1. **Título descritivo**: Resumo claro das mudanças
2. **Descrição detalhada**: O que foi mudado e por quê
3. **Checklist**: 
   - [ ] Testes passando
   - [ ] Documentação atualizada
   - [ ] Code review feito
   - [ ] Breaking changes documentadas

---

## Testes

### Backend (Python)

```python
# tests/test_services/test_osm_service.py
import pytest
from unittest.mock import Mock, patch

from api.services.osm_service import OSMService
from api.models.osm_models import Coordinates

class TestOSMService:
    @pytest.fixture
    def osm_service(self):
        return OSMService()
    
    @pytest.fixture
    def sample_coordinates(self):
        return Coordinates(lat=-19.9167, lon=-43.9345)
    
    def test_search_pois_success(self, osm_service, sample_coordinates):
        """Testa busca bem-sucedida de POIs."""
        # Arrange
        expected_pois = [
            {"id": "1", "name": "Posto BR", "type": "gas_station"}
        ]
        
        # Act
        with patch.object(osm_service, '_query_overpass') as mock_query:
            mock_query.return_value = expected_pois
            result = osm_service.search_pois_around_coordinates(
                coordinates=[sample_coordinates],
                radius_meters=1000,
                poi_types=[{"amenity": "fuel"}]
            )
        
        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "Posto BR"
        mock_query.assert_called_once()
    
    def test_search_pois_empty_result(self, osm_service, sample_coordinates):
        """Testa comportamento quando nenhum POI é encontrado."""
        with patch.object(osm_service, '_query_overpass') as mock_query:
            mock_query.return_value = []
            result = osm_service.search_pois_around_coordinates(
                coordinates=[sample_coordinates],
                radius_meters=1000,
                poi_types=[{"amenity": "fuel"}]
            )
        
        assert result == []
    
    def test_search_pois_api_error(self, osm_service, sample_coordinates):
        """Testa tratamento de erro da API Overpass."""
        with patch.object(osm_service, '_query_overpass') as mock_query:
            mock_query.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API Error"):
                osm_service.search_pois_around_coordinates(
                    coordinates=[sample_coordinates],
                    radius_meters=1000,
                    poi_types=[{"amenity": "fuel"}]
                )
```

### Frontend (TypeScript/Jest)

```typescript
// __tests__/components/SearchForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchForm } from '@/components/forms/SearchForm';

const mockOnSubmit = jest.fn();

describe('SearchForm', () => {
  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it('renders all form fields', () => {
    render(<SearchForm onSubmit={mockOnSubmit} />);
    
    expect(screen.getByLabelText(/origem/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/destino/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /buscar/i })).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    render(<SearchForm onSubmit={mockOnSubmit} />);
    
    const submitButton = screen.getByRole('button', { name: /buscar/i });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/origem é obrigatória/i)).toBeInTheDocument();
      expect(screen.getByText(/destino é obrigatório/i)).toBeInTheDocument();
    });
    
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('submits form with valid data', async () => {
    render(<SearchForm onSubmit={mockOnSubmit} />);
    
    const originInput = screen.getByLabelText(/origem/i);
    const destinationInput = screen.getByLabelText(/destino/i);
    const submitButton = screen.getByRole('button', { name: /buscar/i });
    
    fireEvent.change(originInput, { target: { value: 'São Paulo, SP' } });
    fireEvent.change(destinationInput, { target: { value: 'Rio de Janeiro, RJ' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        origin: 'São Paulo, SP',
        destination: 'Rio de Janeiro, RJ',
        includeGasStations: true,
        includeRestaurants: false,
        maxDistance: 1000
      });
    });
  });
});
```

---

## Documentação

### Docstrings Python

```python
def calculate_route_distance(coordinates: List[Coordinates]) -> float:
    """
    Calcula a distância total de uma rota baseada em coordenadas.
    
    Esta função utiliza a fórmula de Haversine para calcular distâncias
    geodésicas entre pontos consecutivos e soma todas as distâncias.
    
    Args:
        coordinates: Lista de coordenadas representando a rota.
                    Deve conter pelo menos 2 pontos.
    
    Returns:
        Distância total da rota em quilômetros.
    
    Raises:
        ValueError: Se a lista contém menos de 2 coordenadas.
        TypeError: Se algum elemento não é uma instância válida de Coordinates.
    
    Example:
        >>> coords = [
        ...     Coordinates(lat=-23.5505, lon=-46.6333),  # São Paulo
        ...     Coordinates(lat=-22.9068, lon=-43.1729)   # Rio de Janeiro
        ... ]
        >>> distance = calculate_route_distance(coords)
        >>> print(f"Distância: {distance:.2f}km")
        Distância: 357.45km
    
    Note:
        A precisão do cálculo pode variar para distâncias muito longas
        devido à aproximação esférica da Terra.
    """
```

### JSDoc TypeScript

```typescript
/**
 * Componente para exibir informações de um POI no mapa
 * 
 * @param poi - Dados do ponto de interesse
 * @param onSelect - Callback executado quando o POI é selecionado
 * @param isSelected - Se este POI está atualmente selecionado
 * 
 * @example
 * ```tsx
 * <POIMarker
 *   poi={gasStation}
 *   onSelect={(id) => console.log(`Selected: ${id}`)}
 *   isSelected={selectedPOI === gasStation.id}
 * />
 * ```
 */
interface POIMarkerProps {
  /** Dados do ponto de interesse */
  poi: POI;
  /** Callback executado quando o POI é clicado */
  onSelect?: (poiId: string) => void;
  /** Indica se este POI está selecionado */
  isSelected?: boolean;
}
```

### API Documentation

Toda API deve ter documentação automática via FastAPI + OpenAPI:

```python
@router.post("/linear-map", response_model=LinearMapResponse)
async def generate_linear_map(request: LinearMapRequest):
    """
    Gera um mapa linear com POIs ao longo de uma rota.
    
    Este endpoint cria um mapa linear mostrando pontos de interesse
    distribuídos ao longo da rota entre origem e destino.
    
    **Processo:**
    1. Busca a rota no OpenStreetMap
    2. Identifica POIs próximos à rota
    3. Calcula distâncias e posições relativas
    4. Retorna dados estruturados do mapa linear
    
    **Limitações:**
    - Funciona apenas para localidades brasileiras
    - Máximo de 100 POIs por rota
    - Timeout de 5 minutos para operações longas
    """
```

---

## Performance e Segurança

### Performance Guidelines

#### Backend
```python
# ✅ Use async/await para I/O
async def fetch_data_from_api():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# ✅ Cache resultados caros
@lru_cache(maxsize=128)
def expensive_calculation(param: str) -> float:
    # Cálculo custoso
    return result

# ✅ Paginação em queries grandes
@router.get("/pois")
async def get_pois(page: int = 1, size: int = 20):
    offset = (page - 1) * size
    return database.get_pois(offset=offset, limit=size)
```

#### Frontend
```typescript
// ✅ Lazy loading de componentes
const MapComponent = lazy(() => import('./components/MapComponent'));

// ✅ Memoização de cálculos caros
const expensiveCalculation = useMemo(() => {
  return processLargeDataset(data);
}, [data]);

// ✅ Debounce em inputs de busca
const debouncedSearch = useDebouncedCallback(
  (query: string) => performSearch(query),
  300
);
```

### Segurança

#### Validação de Entrada
```python
# ✅ Sempre validar dados de entrada
def process_coordinates(lat: float, lon: float):
    if not (-90 <= lat <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    if not (-180 <= lon <= 180):
        raise ValueError("Longitude must be between -180 and 180")
```

#### Sanitização
```typescript
// ✅ Sanitizar dados do usuário
import DOMPurify from 'dompurify';

function sanitizeUserInput(input: string): string {
  return DOMPurify.sanitize(input);
}
```

#### Environment Variables
```python
# ✅ Nunca commitar secrets
API_KEY = os.getenv("OSM_API_KEY")
if not API_KEY:
    raise ValueError("OSM_API_KEY environment variable is required")

# ✅ Use diferentes configs por ambiente
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./dev.db" if os.getenv("ENV") == "development" else None
)
```

---

## Ferramentas de Qualidade

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
```

### Scripts de Desenvolvimento

```json
// package.json scripts
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "lint:fix": "next lint --fix",
    "type-check": "tsc --noEmit",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage"
  }
}
```

```toml
# pyproject.toml scripts
[tool.poetry.scripts]
dev = "python -m api.run"
format = "black . && isort ."
lint = "flake8 . && mypy ."
test = "pytest"
```

---

Este documento deve ser revisado e atualizado regularmente conforme o projeto evolui e novas práticas são adotadas pela equipe.

Última atualização: 2025-01-12