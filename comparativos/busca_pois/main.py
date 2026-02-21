"""
Teste Comparativo de Busca de POIs: Overpass vs Mapbox vs HERE

Este script executa uma comparação entre três provedores de busca de POIs:
- Overpass API (OpenStreetMap)
- Mapbox Search API
- HERE Browse API

Rota de teste: Belo Horizonte -> Ouro Preto (MG)
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from constants import (
    POI_CATEGORIES,
    SEARCH_RADIUS_METERS,
    ROUTE_DATA_FILE,
    REPORT_FILE,
    MAPBOX_TOKEN,
    HERE_API_KEY,
)
from providers import OverpassProvider, MapboxProvider, HereProvider
from utils.metrics import (
    compare_results,
    calculate_category_stats,
    generate_summary,
    calculate_data_quality_score,
)


async def load_route_data() -> dict:
    """Load route data from JSON file."""
    route_file = Path(__file__).parent / ROUTE_DATA_FILE
    with open(route_file, "r") as f:
        return json.load(f)


async def run_comparison():
    """Run the POI search comparison."""
    print("=" * 60)
    print("TESTE COMPARATIVO DE BUSCA DE POIs")
    print("Overpass vs Mapbox vs HERE")
    print("=" * 60)
    print()
    
    # Load route data
    route = await load_route_data()
    print(f"Rota: {route['origin']} -> {route['destination']}")
    print(f"Comprimento: {route['total_length_km']} km")
    print(f"Pontos de teste: {len(route['search_points'])}")
    print()
    
    # Initialize providers
    providers = {}
    errors = []
    
    # Always add Overpass (free, no key needed)
    print("Inicializando provedores...")
    providers["Overpass"] = OverpassProvider()
    
    # Add Mapbox if token is available
    if MAPBOX_TOKEN:
        try:
            providers["Mapbox"] = MapboxProvider(MAPBOX_TOKEN)
            print("  - Mapbox: OK")
        except Exception as e:
            errors.append(f"Mapbox: {e}")
            print(f"  - Mapbox: ERRO - {e}")
    else:
        print("  - Mapbox: NÃO CONFIGURADO (defina MAPBOX_ACCESS_TOKEN)")
    
    # Add HERE if API key is available
    if HERE_API_KEY:
        try:
            providers["HERE"] = HereProvider(HERE_API_KEY)
            print("  - HERE: OK")
        except Exception as e:
            errors.append(f"HERE: {e}")
            print(f"  - HERE: ERRO - {e}")
    else:
        print("  - HERE: NÃO CONFIGURADO (defina HERE_API_KEY)")
    
    if not providers:
        print("\nERRO: Nenhum provider disponível!")
        return None
    
    print(f"\nProvedores ativos: {list(providers.keys())}")
    print()
    
    # Run searches
    search_points = route["search_points"]
    results_by_provider = {name: [] for name in providers.keys()}
    timing_stats = {}
    
    print("Iniciando buscas de POIs...")
    print("-" * 60)
    
    for i, point in enumerate(search_points, 1):
        print(f"\nPonto {i}/{len(search_points)}: {point['distance_km']}km ({point['lat']}, {point['lon']})")
        
        for provider_name, provider in providers.items():
            try:
                pois = await provider.search_pois(
                    latitude=point["lat"],
                    longitude=point["lon"],
                    radius=SEARCH_RADIUS_METERS,
                    categories=POI_CATEGORIES,
                )
                results_by_provider[provider_name].extend(pois)
                print(f"  {provider_name}: {len(pois)} POIs")
            except Exception as e:
                print(f"  {provider_name}: ERRO - {e}")
    
    # Get timing stats
    for name, provider in providers.items():
        timing_stats[name] = provider.get_stats()
    
    print("\n" + "=" * 60)
    print("RESULTADOS")
    print("=" * 60)
    
    # Calculate comparison
    comparison = compare_results(results_by_provider)
    category_stats = calculate_category_stats(results_by_provider)
    
    # Print summary
    print("\n## Resumo Geral")
    print("-" * 40)
    print(generate_summary(results_by_provider, timing_stats))
    
    # Print category breakdown
    print("\n## POIs por Categoria")
    print("-" * 40)
    print("| Categoria |", end="")
    for provider in results_by_provider.keys():
        print(f" {provider[:8]:8} |", end="")
    print()
    print("|", end="")
    for _ in range(len(results_by_provider) + 1):
        print("-" * 11 + "|", end="")
    print()
    
    all_categories = set()
    for stats in category_stats.values():
        all_categories.update(stats.keys())
    
    for cat in sorted(all_categories):
        print(f"| {cat:10} |", end="")
        for provider in results_by_provider.keys():
            count = category_stats[provider].get(cat, 0)
            print(f" {count:10} |", end="")
        print()
    
    # Data quality
    print("\n## Qualidade dos Dados")
    print("-" * 40)
    for provider, results in results_by_provider.items():
        quality = calculate_data_quality_score(results)
        with_phone = sum(1 for r in results if r.phone)
        with_website = sum(1 for r in results if r.website)
        with_address = sum(1 for r in results if r.address)
        
        print(f"\n{provider}:")
        print(f"  - Total: {len(results)} POIs")
        print(f"  - Qualidade: {quality:.1f}%")
        print(f"  - Com telefone: {with_phone} ({100*with_phone/len(results):.1f}%)" if results else "  - Com telefone: 0")
        print(f"  - Com website: {with_website} ({100*with_website/len(results):.1f}%)" if results else "  - Com website: 0")
        print(f"  - Com endereço: {with_address} ({100*with_address/len(results):.1f}%)" if results else "  - Com endereço: 0")
    
    # Save raw data to JSON for detailed analysis
    raw_data = {
        "route": route,
        "providers": {},
        "timing_stats": timing_stats,
        "category_stats": category_stats,
    }
    
    for provider_name, results in results_by_provider.items():
        raw_data["providers"][provider_name] = {
            "total": len(results),
            "pois": [
                {
                    "id": poi.id,
                    "name": poi.name,
                    "category": poi.category,
                    "latitude": poi.latitude,
                    "longitude": poi.longitude,
                    "address": poi.address,
                    "phone": poi.phone,
                    "website": poi.website,
                    "rating": poi.rating,
                    "raw_data": poi.raw_data,
                }
                for poi in results
            ]
        }
    
    # Generate timestamp for filename
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_filename = f"resultados_{timestamp}.json"
    data_path = Path(__file__).parent / "data" / data_filename
    
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nDados brutos salvos em: {data_path}")
    
    # Generate markdown report
    report = generate_markdown_report(
        route=route,
        results_by_provider=results_by_provider,
        timing_stats=timing_stats,
        category_stats=category_stats,
    )
    
    # Save report
    report_path = Path(__file__).parent / REPORT_FILE
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"Relatório salvo em: {report_path}")
    
    # Close providers
    for provider in providers.values():
        await provider.close()
    
    return {
        "route": route,
        "results": results_by_provider,
        "timing": timing_stats,
        "category_stats": category_stats,
    }


def generate_markdown_report(
    route: dict,
    results_by_provider: dict,
    timing_stats: dict,
    category_stats: dict,
) -> str:
    """Generate markdown report."""
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report = f"""# Relatório Comparativo: Busca de POIs

**Data:** {now}  
**Rota:** {route['origin']} → {route['destination']}  
**Comprimento:** {route['total_length_km']} km  
**Pontos de busca:** {len(route['search_points'])}  
**Raio de busca:** {SEARCH_RADIUS_METERS} m  

---

## Resumo Executivo

| Provider | Total POIs | Tempo Médio/Req | Requests |
|----------|------------|-----------------|----------|
"""
    
    for provider, results in results_by_provider.items():
        stats = timing_stats.get(provider, {})
        avg_time = stats.get("avg_time_per_request_seconds", 0)
        total_req = stats.get("total_requests", 0)
        report += f"| {provider} | {len(results)} | {avg_time:.3f}s | {total_req} |\n"
    
    # Category table
    all_categories = set()
    for stats in category_stats.values():
        all_categories.update(stats.keys())
    
    report += "\n## POIs por Categoria\n\n"
    report += "| Categoria |"
    for provider in results_by_provider.keys():
        report += f" {provider} |"
    report += "\n"
    report += "|" + "---|" * (len(results_by_provider) + 1) + "\n"
    
    for cat in sorted(all_categories):
        report += f"| {cat} |"
        for provider in results_by_provider.keys():
            count = category_stats[provider].get(cat, 0)
            report += f" {count} |"
        report += "\n"
    
    # Detailed results per provider
    report += "\n## Detalhamento por Provider\n\n"
    
    for provider, results in results_by_provider.items():
        report += f"### {provider}\n\n"
        
        if not results:
            report += "_Nenhum resultado_\n\n"
            continue
        
        # Group by category
        by_cat = {}
        for poi in results:
            if poi.category not in by_cat:
                by_cat[poi.category] = []
            by_cat[poi.category].append(poi)
        
        for cat, pois in sorted(by_cat.items()):
            report += f"**{cat}** ({len(pois)} resultados):\n"
            for poi in pois[:5]:  # Show first 5
                report += f"- {poi.name}\n"
            if len(pois) > 5:
                report += f"- ... e mais {len(pois) - 5}\n"
            report += "\n"
    
    # Analysis
    report += """## Análise

### Overpass (OpenStreetMap)
- **Vantagens:**
  - Dados abertos e gratuitos
  - Grande base de dados de POIs
  - Não requer API key
- **Desvantagens:**
  - Rate limiting (1 req/s)
  - API pode estar instável
  - Dados menos estruturados

### Mapbox
- **Vantagens:**
  - API rápida e confiável
  - Dados bem estruturados
  - Boa cobertura em áreas urbanas
- **Desvantagens:**
  - Custo após limite gratuito
  - Menor cobertura que OSM em áreas remotas

### HERE
- **Vantagens:**
  - API robusta e confiável
  - Dados de alta qualidade
  - Bom para Brasil
- **Desvantagens:**
  - Custo por requisição
  - Requer API key

### Recomendação
Para o MapaLinear, considerando o custo-benefício:
1. **Overpass** para desenvolvimento e testes (gratuito)
2. **HERE** para produção (melhor qualidade de dados para rotas brasileiras)

---

*Relatório gerado automaticamente em {now}*
""".format(now=now)
    
    return report


if __name__ == "__main__":
    asyncio.run(run_comparison())
