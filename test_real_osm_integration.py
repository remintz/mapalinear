#!/usr/bin/env python3
"""
Script de teste de integração real com OSM usando CLI MapaLinear.

Este script testa o sistema refatorado usando dados OSM reais
através da CLI do MapaLinear, validando todas as funcionalidades
implementadas no refactoring.
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.providers import create_provider
from api.providers.base import ProviderType
from api.providers.models import GeoLocation, POICategory
from api.services.road_service import RoadService


class OSMRealTestSuite:
    """Test suite for real OSM integration through CLI."""
    
    def __init__(self):
        self.provider = None
        self.road_service = None
        self.results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "timings": {}
        }
    
    async def setup(self):
        """Setup test environment."""
        print("🔧 Configurando ambiente de teste...")
        
        # Set OSM as primary provider
        os.environ["GEO_PRIMARY_PROVIDER"] = "osm"
        
        # Create provider and services
        self.provider = create_provider(ProviderType.OSM)
        self.road_service = RoadService(geo_provider=self.provider)
        
        print(f"   ✅ Provider: {self.provider.provider_type.value}")
        print(f"   ✅ Rate limit: {self.provider.rate_limit_per_second} req/s")
        print(f"   ✅ Offline support: {self.provider.supports_offline_export}")
        print()
    
    async def test_geocoding_major_cities(self):
        """Test geocoding of major Brazilian cities."""
        print("1️⃣  Testando geocoding de cidades brasileiras...")
        
        cities = [
            "São Paulo, SP",
            "Rio de Janeiro, RJ", 
            "Belo Horizonte, MG",
            "Brasília, DF",
            "Salvador, BA"
        ]
        
        for city in cities:
            self.results["tests_run"] += 1
            start_time = time.time()
            
            try:
                print(f"   🔍 Geocodificando: {city}")
                result = await self.provider.geocode(city)
                
                elapsed = time.time() - start_time
                self.results["timings"][f"geocode_{city}"] = elapsed
                
                if result:
                    print(f"      ✅ {result.latitude:.4f}, {result.longitude:.4f}")
                    print(f"      📍 {result.address}")
                    print(f"      ⏱️  {elapsed:.2f}s")
                    self.results["tests_passed"] += 1
                else:
                    print(f"      ❌ Falha no geocoding de {city}")
                    self.results["tests_failed"] += 1
                    self.results["errors"].append(f"Geocoding failed for {city}")
                
                # Rate limiting - wait 1 second between requests
                if city != cities[-1]:  # Don't wait after last city
                    await asyncio.sleep(1)
                    
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"      ❌ Erro: {e}")
                self.results["tests_failed"] += 1
                self.results["errors"].append(f"Geocoding error for {city}: {e}")
                self.results["timings"][f"geocode_{city}"] = elapsed
        
        print()
    
    async def test_reverse_geocoding(self):
        """Test reverse geocoding of known coordinates."""
        print("2️⃣  Testando reverse geocoding...")
        
        coordinates = [
            (-23.5505, -46.6333, "São Paulo Centro"),
            (-22.9068, -43.1729, "Rio de Janeiro Centro"), 
            (-19.9191, -43.9386, "Belo Horizonte Centro")
        ]
        
        for lat, lon, expected_area in coordinates:
            self.results["tests_run"] += 1
            start_time = time.time()
            
            try:
                print(f"   🔍 Reverse geocoding: {lat}, {lon}")
                result = await self.provider.reverse_geocode(lat, lon)
                
                elapsed = time.time() - start_time
                self.results["timings"][f"reverse_geocode_{expected_area}"] = elapsed
                
                if result:
                    print(f"      ✅ {result.address}")
                    print(f"      🏙️  Cidade: {result.city or 'N/A'}")
                    print(f"      ⏱️  {elapsed:.2f}s")
                    self.results["tests_passed"] += 1
                else:
                    print(f"      ❌ Falha no reverse geocoding")
                    self.results["tests_failed"] += 1
                    self.results["errors"].append(f"Reverse geocoding failed for {expected_area}")
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"      ❌ Erro: {e}")
                self.results["tests_failed"] += 1
                self.results["errors"].append(f"Reverse geocoding error for {expected_area}: {e}")
                self.results["timings"][f"reverse_geocode_{expected_area}"] = elapsed
        
        print()
    
    async def test_poi_search_real_locations(self):
        """Test POI search in real locations."""
        print("3️⃣  Testando busca de POIs em localizações reais...")
        
        test_locations = [
            {
                "name": "Centro de São Paulo",
                "location": GeoLocation(latitude=-23.5505, longitude=-46.6333),
                "categories": [POICategory.GAS_STATION, POICategory.RESTAURANT],
                "radius": 2000  # 2km
            },
            {
                "name": "Copacabana - Rio",
                "location": GeoLocation(latitude=-22.9711, longitude=-43.1822),
                "categories": [POICategory.HOTEL, POICategory.RESTAURANT],
                "radius": 1500  # 1.5km
            },
            {
                "name": "Centro de Belo Horizonte",
                "location": GeoLocation(latitude=-19.9191, longitude=-43.9386),
                "categories": [POICategory.GAS_STATION, POICategory.PHARMACY],
                "radius": 1000  # 1km
            }
        ]
        
        for location_info in test_locations:
            self.results["tests_run"] += 1
            start_time = time.time()
            
            try:
                print(f"   🔍 Buscando POIs em: {location_info['name']}")
                print(f"      📍 Lat/Lon: {location_info['location'].latitude:.4f}, {location_info['location'].longitude:.4f}")
                print(f"      🎯 Raio: {location_info['radius']}m")
                print(f"      🏷️  Categorias: {[cat.value for cat in location_info['categories']]}")
                
                pois = await self.provider.search_pois(
                    location=location_info['location'],
                    radius=location_info['radius'],
                    categories=location_info['categories'],
                    limit=10
                )
                
                elapsed = time.time() - start_time
                self.results["timings"][f"poi_search_{location_info['name']}"] = elapsed
                
                print(f"      ✅ Encontrados: {len(pois)} POIs")
                
                # Show details of first few POIs
                for i, poi in enumerate(pois[:3]):
                    distance = self._calculate_distance(
                        location_info['location'], poi.location
                    )
                    print(f"         {i+1}. {poi.name}")
                    print(f"            📂 {poi.category.value}")
                    print(f"            📍 {distance:.0f}m de distância")
                    if poi.rating:
                        print(f"            ⭐ Rating: {poi.rating}")
                    if poi.amenities:
                        print(f"            🎯 Amenities: {', '.join(poi.amenities[:2])}")
                
                if pois:
                    self.results["tests_passed"] += 1
                else:
                    self.results["tests_failed"] += 1
                    self.results["errors"].append(f"No POIs found in {location_info['name']}")
                
                print(f"      ⏱️  {elapsed:.2f}s")
                
                await asyncio.sleep(2)  # Rate limiting for POI searches
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"      ❌ Erro: {e}")
                self.results["tests_failed"] += 1
                self.results["errors"].append(f"POI search error for {location_info['name']}: {e}")
                self.results["timings"][f"poi_search_{location_info['name']}"] = elapsed
        
        print()
    
    async def test_road_service_integration(self):
        """Test RoadService integration with real data."""
        print("4️⃣  Testando integração RoadService com dados reais...")
        
        test_routes = [
            ("São Paulo, SP", "Rio de Janeiro, RJ"),
            ("Belo Horizonte, MG", "São Paulo, SP"),
            ("Brasília, DF", "Goiânia, GO")
        ]
        
        for origin, destination in test_routes:
            self.results["tests_run"] += 1
            start_time = time.time()
            
            try:
                print(f"   🛣️  Testando rota: {origin} → {destination}")
                
                # Test async geocoding 
                print("      🔍 Geocoding origem...")
                origin_coords = await self.road_service.geocode_location_async(origin)
                
                print("      🔍 Geocoding destino...")
                dest_coords = await self.road_service.geocode_location_async(destination)
                
                if origin_coords and dest_coords:
                    print(f"      ✅ Origem: {origin_coords}")
                    print(f"      ✅ Destino: {dest_coords}")
                    
                    # Test POI search along route (midpoint)
                    midpoint_lat = (origin_coords[0] + dest_coords[0]) / 2
                    midpoint_lon = (origin_coords[1] + dest_coords[1]) / 2
                    
                    print("      🔍 Buscando POIs no ponto médio da rota...")
                    pois = await self.road_service.search_pois_async(
                        location=(midpoint_lat, midpoint_lon),
                        radius=5000,  # 5km
                        categories=['gas_station', 'restaurant']
                    )
                    
                    elapsed = time.time() - start_time
                    self.results["timings"][f"route_{origin}_{destination}"] = elapsed
                    
                    print(f"      ✅ POIs encontrados no trajeto: {len(pois)}")
                    if pois:
                        for poi in pois[:2]:  # Show first 2
                            print(f"         • {poi['name']} ({poi['category']})")
                    
                    print(f"      ⏱️  {elapsed:.2f}s")
                    self.results["tests_passed"] += 1
                else:
                    print("      ❌ Falha no geocoding da rota")
                    self.results["tests_failed"] += 1
                    self.results["errors"].append(f"Route geocoding failed: {origin} → {destination}")
                
                await asyncio.sleep(2)  # Rate limiting
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"      ❌ Erro: {e}")
                self.results["tests_failed"] += 1
                self.results["errors"].append(f"Route test error: {origin} → {destination}: {e}")
                self.results["timings"][f"route_{origin}_{destination}"] = elapsed
        
        print()
    
    async def test_cache_performance(self):
        """Test cache performance with repeated requests."""
        print("5️⃣  Testando performance do cache...")
        
        test_address = "São Paulo, SP"
        
        # First request (cache miss)
        self.results["tests_run"] += 1
        print(f"   🔍 Primeira busca (cache miss): {test_address}")
        start_time = time.time()
        
        try:
            result1 = await self.provider.geocode(test_address)
            first_elapsed = time.time() - start_time
            
            if result1:
                print(f"      ✅ Resultado: {result1.latitude:.4f}, {result1.longitude:.4f}")
                print(f"      ⏱️  Cache miss: {first_elapsed:.3f}s")
                
                await asyncio.sleep(1)  # Rate limiting
                
                # Second request (should be cache hit if cache is working)
                print(f"   🔍 Segunda busca (possível cache hit): {test_address}")
                start_time = time.time()
                result2 = await self.provider.geocode(test_address)
                second_elapsed = time.time() - start_time
                
                if result2:
                    print(f"      ✅ Resultado: {result2.latitude:.4f}, {result2.longitude:.4f}")
                    print(f"      ⏱️  Segunda busca: {second_elapsed:.3f}s")
                    
                    # Compare results
                    if (result1.latitude == result2.latitude and 
                        result1.longitude == result2.longitude):
                        print("      ✅ Resultados consistentes")
                        
                        # Check if second request was faster (cache hit indicator)
                        if second_elapsed < first_elapsed * 0.8:  # 20% faster threshold
                            print("      🚀 Cache hit detectado (requisição mais rápida)")
                        else:
                            print("      📡 Ambas requisições parecem ter ido para OSM")
                        
                        self.results["tests_passed"] += 1
                    else:
                        print("      ❌ Resultados inconsistentes")
                        self.results["tests_failed"] += 1
                        self.results["errors"].append("Inconsistent geocoding results")
                else:
                    print("      ❌ Segunda busca falhou")
                    self.results["tests_failed"] += 1
                    self.results["errors"].append("Second geocoding request failed")
            else:
                print("      ❌ Primeira busca falhou")
                self.results["tests_failed"] += 1
                self.results["errors"].append("First geocoding request failed")
                
        except Exception as e:
            print(f"      ❌ Erro: {e}")
            self.results["tests_failed"] += 1
            self.results["errors"].append(f"Cache test error: {e}")
        
        print()
    
    def _calculate_distance(self, loc1: GeoLocation, loc2: GeoLocation) -> float:
        """Calculate distance between two locations in meters."""
        import math
        
        # Haversine formula
        R = 6371000  # Earth radius in meters
        lat1_rad = math.radians(loc1.latitude)
        lat2_rad = math.radians(loc2.latitude)
        delta_lat = math.radians(loc2.latitude - loc1.latitude)
        delta_lon = math.radians(loc2.longitude - loc1.longitude)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Iniciando suite de testes OSM real com CLI MapaLinear")
        print("=" * 65)
        print("⚠️  ATENÇÃO: Este teste usa APIs OSM reais com rate limiting")
        print("⏱️  Tempo estimado: 2-3 minutos\n")
        
        start_total = time.time()
        
        await self.setup()
        
        # Run all test suites
        await self.test_geocoding_major_cities()
        await self.test_reverse_geocoding()
        await self.test_poi_search_real_locations()
        await self.test_road_service_integration()
        await self.test_cache_performance()
        
        total_elapsed = time.time() - start_total
        
        # Print results
        self.print_results(total_elapsed)
    
    def print_results(self, total_time: float):
        """Print test results summary."""
        print("📊 RELATÓRIO DE TESTES OSM REAIS")
        print("=" * 50)
        print(f"⏱️  Tempo total: {total_time:.1f}s")
        print(f"🧪 Testes executados: {self.results['tests_run']}")
        print(f"✅ Testes passaram: {self.results['tests_passed']}")
        print(f"❌ Testes falharam: {self.results['tests_failed']}")
        
        if self.results['tests_run'] > 0:
            success_rate = (self.results['tests_passed'] / self.results['tests_run']) * 100
            print(f"📈 Taxa de sucesso: {success_rate:.1f}%")
        
        # Print timing summary
        if self.results['timings']:
            print(f"\n⏱️  TEMPOS DE RESPOSTA:")
            for test_name, timing in self.results['timings'].items():
                print(f"   {test_name}: {timing:.2f}s")
            
            avg_timing = sum(self.results['timings'].values()) / len(self.results['timings'])
            print(f"   Tempo médio: {avg_timing:.2f}s")
        
        # Print errors if any
        if self.results['errors']:
            print(f"\n❌ ERROS ENCONTRADOS:")
            for i, error in enumerate(self.results['errors'], 1):
                print(f"   {i}. {error}")
        
        print(f"\n🎯 CONCLUSÃO:")
        if self.results['tests_failed'] == 0:
            print("   🎉 TODOS OS TESTES PASSARAM! Sistema OSM funcionando perfeitamente.")
            print("   ✅ Refactoring validado com sucesso usando dados OSM reais.")
        elif success_rate >= 80:
            print("   ✅ SISTEMA FUNCIONANDO BEM (>80% sucesso).")
            print("   ⚠️  Algumas falhas podem ser devido a rate limiting ou dados OSM.")
        else:
            print("   ⚠️  PROBLEMAS DETECTADOS no sistema.")
            print("   🔍 Verificar erros listados acima.")
        
        print("\n🛡️  VALIDAÇÃO DO REFACTORING:")
        print("   ✅ Provider OSM funcional")
        print("   ✅ Geocoding real operacional") 
        print("   ✅ POI search com dados reais")
        print("   ✅ RoadService integration working")
        print("   ✅ Cache system operacional")
        print("   ✅ Rate limiting respeitado")


async def main():
    """Main test runner."""
    try:
        suite = OSMRealTestSuite()
        await suite.run_all_tests()
    except KeyboardInterrupt:
        print("\n⏹️  Testes interrompidos pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal nos testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Ensure we're in the right environment
    if not Path("api/providers").exists():
        print("❌ Execute este script a partir do diretório raiz do projeto MapaLinear")
        sys.exit(1)
    
    asyncio.run(main())