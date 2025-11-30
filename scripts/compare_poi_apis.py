#!/usr/bin/env python3
"""
Script para comparar cobertura de avaliações entre Google Places API e HERE Places API.

Uso:
    python scripts/compare_poi_apis.py --google-key YOUR_KEY --here-key YOUR_KEY

O script carrega POIs do arquivo pois_for_comparison.json e consulta ambas as APIs
para comparar a quantidade e qualidade das informações retornadas.
"""

import asyncio
import json
import argparse
import httpx
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import time
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()


@dataclass
class APIResult:
    """Resultado de uma consulta a uma API."""
    found: bool = False
    name: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    has_photos: bool = False
    photo_count: int = 0
    has_opening_hours: bool = False
    has_phone: bool = False
    has_website: bool = False
    price_level: Optional[int] = None
    categories: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """Resultado da comparação para um POI."""
    poi_id: str
    poi_name: str
    poi_category: str
    latitude: float
    longitude: float
    google: APIResult = field(default_factory=APIResult)
    here: APIResult = field(default_factory=APIResult)


class GooglePlacesClient:
    """Cliente para Google Places API."""

    BASE_URL = "https://maps.googleapis.com/maps/api/place"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_nearby(self, lat: float, lng: float, name: str, radius: int = 100) -> APIResult:
        """Busca POI próximo às coordenadas."""
        result = APIResult()

        try:
            # Primeiro, busca por texto com localização
            search_url = f"{self.BASE_URL}/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "keyword": name,
                "key": self.api_key
            }

            response = await self.client.get(search_url, params=params)
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                place = data["results"][0]
                place_id = place.get("place_id")

                # Busca detalhes do lugar
                if place_id:
                    details = await self._get_place_details(place_id)
                    if details:
                        result.found = True
                        result.name = details.get("name")
                        result.rating = details.get("rating")
                        result.review_count = details.get("user_ratings_total")
                        result.has_photos = bool(details.get("photos"))
                        result.photo_count = len(details.get("photos", []))
                        result.has_opening_hours = bool(details.get("opening_hours"))
                        result.has_phone = bool(details.get("formatted_phone_number"))
                        result.has_website = bool(details.get("website"))
                        result.price_level = details.get("price_level")
                        result.categories = details.get("types", [])
                        result.raw_data = details
                else:
                    # Usa dados básicos do resultado de busca
                    result.found = True
                    result.name = place.get("name")
                    result.rating = place.get("rating")
                    result.review_count = place.get("user_ratings_total")
                    result.has_photos = bool(place.get("photos"))
                    result.photo_count = len(place.get("photos", []))
                    result.has_opening_hours = bool(place.get("opening_hours"))
                    result.categories = place.get("types", [])
                    result.raw_data = place

            elif data.get("status") == "ZERO_RESULTS":
                result.found = False
            else:
                console.print(f"[yellow]Google API status: {data.get('status')}[/yellow]")

        except Exception as e:
            console.print(f"[red]Erro Google API: {e}[/red]")

        return result

    async def _get_place_details(self, place_id: str) -> Optional[Dict]:
        """Busca detalhes de um lugar específico."""
        try:
            details_url = f"{self.BASE_URL}/details/json"
            params = {
                "place_id": place_id,
                "fields": "name,rating,user_ratings_total,photos,opening_hours,formatted_phone_number,website,price_level,types,reviews",
                "key": self.api_key
            }

            response = await self.client.get(details_url, params=params)
            data = response.json()

            if data.get("status") == "OK":
                return data.get("result")
        except Exception as e:
            console.print(f"[red]Erro Google Details: {e}[/red]")

        return None

    async def close(self):
        await self.client.aclose()


class HEREPlacesClient:
    """Cliente para HERE Places API."""

    BASE_URL = "https://discover.search.hereapi.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_nearby(self, lat: float, lng: float, name: str, radius: int = 100) -> APIResult:
        """Busca POI próximo às coordenadas."""
        result = APIResult()

        try:
            # Busca por texto com localização
            search_url = f"{self.BASE_URL}/discover"
            params = {
                "at": f"{lat},{lng}",
                "q": name,
                "limit": 5,
                "apiKey": self.api_key
            }

            response = await self.client.get(search_url, params=params)
            data = response.json()

            if data.get("items"):
                place = data["items"][0]

                result.found = True
                result.name = place.get("title")

                # HERE usa diferentes campos para ratings
                if "scoring" in place:
                    scoring = place["scoring"]
                    # HERE não tem rating direto como Google, mas tem queryScore

                # Contatos
                contacts = place.get("contacts", [])
                for contact in contacts:
                    if contact.get("phone"):
                        result.has_phone = True
                    if contact.get("www"):
                        result.has_website = True

                # Horários
                if place.get("openingHours"):
                    result.has_opening_hours = True

                # Categorias
                categories = place.get("categories", [])
                result.categories = [c.get("name", "") for c in categories]

                result.raw_data = place

                # Buscar detalhes adicionais se disponível
                place_id = place.get("id")
                if place_id:
                    details = await self._get_place_details(place_id)
                    if details:
                        # HERE Places Details pode ter mais info
                        if details.get("extended"):
                            ext = details["extended"]
                            # Verificar se há ratings
                            if ext.get("rating"):
                                result.rating = ext["rating"].get("value")
                                result.review_count = ext["rating"].get("count")

        except Exception as e:
            console.print(f"[red]Erro HERE API: {e}[/red]")

        return result

    async def _get_place_details(self, place_id: str) -> Optional[Dict]:
        """Busca detalhes de um lugar específico usando Lookup API."""
        try:
            lookup_url = "https://lookup.search.hereapi.com/v1/lookup"
            params = {
                "id": place_id,
                "apiKey": self.api_key
            }

            response = await self.client.get(lookup_url, params=params)
            data = response.json()
            return data

        except Exception as e:
            console.print(f"[red]Erro HERE Lookup: {e}[/red]")

        return None

    async def close(self):
        await self.client.aclose()


async def compare_apis(
    pois: List[Dict],
    google_key: Optional[str],
    here_key: Optional[str],
    sample_size: Optional[int] = None,
    delay: float = 0.5
) -> List[ComparisonResult]:
    """Compara APIs para uma lista de POIs."""

    results = []

    google_client = GooglePlacesClient(google_key) if google_key else None
    here_client = HEREPlacesClient(here_key) if here_key else None

    # Limitar amostra se especificado
    if sample_size:
        pois = pois[:sample_size]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task(f"Comparando {len(pois)} POIs...", total=len(pois))

        for poi in pois:
            location = poi.get("location", {})
            lat = location.get("latitude")
            lng = location.get("longitude")
            name = poi.get("name", "")

            if not lat or not lng:
                progress.advance(task)
                continue

            comparison = ComparisonResult(
                poi_id=poi.get("id", ""),
                poi_name=name,
                poi_category=poi.get("category", ""),
                latitude=lat,
                longitude=lng
            )

            # Consultar Google
            if google_client:
                comparison.google = await google_client.search_nearby(lat, lng, name)
                await asyncio.sleep(delay)  # Rate limiting

            # Consultar HERE
            if here_client:
                comparison.here = await here_client.search_nearby(lat, lng, name)
                await asyncio.sleep(delay)  # Rate limiting

            results.append(comparison)
            progress.advance(task)

    # Fechar clientes
    if google_client:
        await google_client.close()
    if here_client:
        await here_client.close()

    return results


def generate_report(results: List[ComparisonResult]) -> Dict[str, Any]:
    """Gera relatório de comparação."""

    report = {
        "total_pois": len(results),
        "google": {
            "found": 0,
            "with_rating": 0,
            "with_reviews": 0,
            "with_photos": 0,
            "with_hours": 0,
            "with_phone": 0,
            "with_website": 0,
            "total_reviews": 0,
            "avg_rating": 0.0,
            "ratings": []
        },
        "here": {
            "found": 0,
            "with_rating": 0,
            "with_reviews": 0,
            "with_photos": 0,
            "with_hours": 0,
            "with_phone": 0,
            "with_website": 0,
            "total_reviews": 0,
            "avg_rating": 0.0,
            "ratings": []
        },
        "by_category": {}
    }

    for r in results:
        # Google stats
        if r.google.found:
            report["google"]["found"] += 1
            if r.google.rating:
                report["google"]["with_rating"] += 1
                report["google"]["ratings"].append(r.google.rating)
            if r.google.review_count:
                report["google"]["with_reviews"] += 1
                report["google"]["total_reviews"] += r.google.review_count
            if r.google.has_photos:
                report["google"]["with_photos"] += 1
            if r.google.has_opening_hours:
                report["google"]["with_hours"] += 1
            if r.google.has_phone:
                report["google"]["with_phone"] += 1
            if r.google.has_website:
                report["google"]["with_website"] += 1

        # HERE stats
        if r.here.found:
            report["here"]["found"] += 1
            if r.here.rating:
                report["here"]["with_rating"] += 1
                report["here"]["ratings"].append(r.here.rating)
            if r.here.review_count:
                report["here"]["with_reviews"] += 1
                report["here"]["total_reviews"] += r.here.review_count
            if r.here.has_photos:
                report["here"]["with_photos"] += 1
            if r.here.has_opening_hours:
                report["here"]["with_hours"] += 1
            if r.here.has_phone:
                report["here"]["with_phone"] += 1
            if r.here.has_website:
                report["here"]["with_website"] += 1

        # Por categoria
        cat = r.poi_category
        if cat not in report["by_category"]:
            report["by_category"][cat] = {
                "total": 0,
                "google_found": 0,
                "google_with_rating": 0,
                "here_found": 0,
                "here_with_rating": 0
            }

        report["by_category"][cat]["total"] += 1
        if r.google.found:
            report["by_category"][cat]["google_found"] += 1
            if r.google.rating:
                report["by_category"][cat]["google_with_rating"] += 1
        if r.here.found:
            report["by_category"][cat]["here_found"] += 1
            if r.here.rating:
                report["by_category"][cat]["here_with_rating"] += 1

    # Calcular médias
    if report["google"]["ratings"]:
        report["google"]["avg_rating"] = sum(report["google"]["ratings"]) / len(report["google"]["ratings"])
    if report["here"]["ratings"]:
        report["here"]["avg_rating"] = sum(report["here"]["ratings"]) / len(report["here"]["ratings"])

    # Remover lista de ratings do relatório final
    del report["google"]["ratings"]
    del report["here"]["ratings"]

    return report


def print_report(report: Dict[str, Any]):
    """Imprime relatório formatado."""

    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]           RELATÓRIO DE COMPARAÇÃO: GOOGLE vs HERE              [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")

    console.print(f"[bold]Total de POIs analisados:[/bold] {report['total_pois']}\n")

    # Tabela principal
    table = Table(title="Comparação Geral", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Google Places", justify="right", style="green")
    table.add_column("HERE Places", justify="right", style="blue")
    table.add_column("Vencedor", justify="center")

    metrics = [
        ("POIs encontrados", "found", True),
        ("Com rating", "with_rating", True),
        ("Com reviews", "with_reviews", True),
        ("Total de reviews", "total_reviews", True),
        ("Rating médio", "avg_rating", True),
        ("Com fotos", "with_photos", True),
        ("Com horários", "with_hours", True),
        ("Com telefone", "with_phone", True),
        ("Com website", "with_website", True),
    ]

    for label, key, higher_better in metrics:
        g_val = report["google"][key]
        h_val = report["here"][key]

        if isinstance(g_val, float):
            g_str = f"{g_val:.2f}"
            h_str = f"{h_val:.2f}"
        else:
            g_str = str(g_val)
            h_str = str(h_val)

        if higher_better:
            if g_val > h_val:
                winner = "[green]Google[/green]"
            elif h_val > g_val:
                winner = "[blue]HERE[/blue]"
            else:
                winner = "Empate"
        else:
            winner = "-"

        table.add_row(label, g_str, h_str, winner)

    console.print(table)

    # Tabela por categoria
    console.print("\n")
    cat_table = Table(title="Comparação por Categoria", show_header=True, header_style="bold magenta")
    cat_table.add_column("Categoria", style="cyan")
    cat_table.add_column("Total", justify="right")
    cat_table.add_column("Google Found", justify="right", style="green")
    cat_table.add_column("Google Rating", justify="right", style="green")
    cat_table.add_column("HERE Found", justify="right", style="blue")
    cat_table.add_column("HERE Rating", justify="right", style="blue")

    for cat, stats in sorted(report["by_category"].items(), key=lambda x: -x[1]["total"]):
        cat_table.add_row(
            cat,
            str(stats["total"]),
            f"{stats['google_found']} ({stats['google_found']*100//stats['total']}%)",
            f"{stats['google_with_rating']} ({stats['google_with_rating']*100//stats['total']}%)",
            f"{stats['here_found']} ({stats['here_found']*100//stats['total']}%)",
            f"{stats['here_with_rating']} ({stats['here_with_rating']*100//stats['total']}%)"
        )

    console.print(cat_table)

    # Conclusão
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold]CONCLUSÃO:[/bold]")

    g_score = 0
    h_score = 0

    for key in ["found", "with_rating", "with_reviews", "total_reviews"]:
        if report["google"][key] > report["here"][key]:
            g_score += 1
        elif report["here"][key] > report["google"][key]:
            h_score += 1

    if g_score > h_score:
        console.print("[green]→ Google Places API tem melhor cobertura de avaliações para estes POIs[/green]")
    elif h_score > g_score:
        console.print("[blue]→ HERE Places API tem melhor cobertura de avaliações para estes POIs[/blue]")
    else:
        console.print("[yellow]→ Ambas APIs têm cobertura similar para estes POIs[/yellow]")

    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")


def print_sample_results(results: List[ComparisonResult], n: int = 10):
    """Imprime amostra de resultados detalhados."""

    console.print("\n[bold]Amostra de Resultados Detalhados:[/bold]\n")

    # Filtrar POIs que têm dados em pelo menos uma API
    interesting = [r for r in results if r.google.found or r.here.found][:n]

    for r in interesting:
        console.print(f"[bold cyan]{r.poi_name}[/bold cyan] ({r.poi_category})")
        console.print(f"  Coordenadas: {r.latitude}, {r.longitude}")

        if r.google.found:
            console.print(f"  [green]Google:[/green] {r.google.name}")
            console.print(f"    Rating: {r.google.rating or 'N/A'} ({r.google.review_count or 0} reviews)")
            console.print(f"    Fotos: {r.google.photo_count}, Horários: {r.google.has_opening_hours}")
        else:
            console.print(f"  [green]Google:[/green] Não encontrado")

        if r.here.found:
            console.print(f"  [blue]HERE:[/blue] {r.here.name}")
            console.print(f"    Rating: {r.here.rating or 'N/A'} ({r.here.review_count or 0} reviews)")
            console.print(f"    Horários: {r.here.has_opening_hours}, Tel: {r.here.has_phone}")
        else:
            console.print(f"  [blue]HERE:[/blue] Não encontrado")

        console.print()


async def main():
    parser = argparse.ArgumentParser(description="Compara Google Places API vs HERE Places API")
    parser.add_argument("--google-key", help="Chave da Google Places API")
    parser.add_argument("--here-key", help="Chave da HERE API")
    parser.add_argument("--pois-file", default="pois_for_comparison.json", help="Arquivo JSON com POIs")
    parser.add_argument("--sample", type=int, help="Número de POIs para amostrar (default: todos)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay entre requisições (segundos)")
    parser.add_argument("--output", help="Arquivo para salvar resultados JSON")

    args = parser.parse_args()

    if not args.google_key and not args.here_key:
        console.print("[red]Erro: Forneça pelo menos uma chave de API (--google-key ou --here-key)[/red]")
        return

    # Carregar POIs
    pois_path = Path(args.pois_file)
    if not pois_path.exists():
        console.print(f"[red]Erro: Arquivo {args.pois_file} não encontrado[/red]")
        console.print("[yellow]Execute primeiro o script de extração de POIs do cache[/yellow]")
        return

    with open(pois_path) as f:
        pois = json.load(f)

    console.print(f"[bold]Carregados {len(pois)} POIs de {args.pois_file}[/bold]")

    if args.sample:
        console.print(f"[yellow]Usando amostra de {args.sample} POIs[/yellow]")

    # Executar comparação
    results = await compare_apis(
        pois=pois,
        google_key=args.google_key,
        here_key=args.here_key,
        sample_size=args.sample,
        delay=args.delay
    )

    # Gerar e imprimir relatório
    report = generate_report(results)
    print_report(report)
    print_sample_results(results)

    # Salvar resultados se especificado
    if args.output:
        output_data = {
            "report": report,
            "results": [
                {
                    "poi_id": r.poi_id,
                    "poi_name": r.poi_name,
                    "poi_category": r.poi_category,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "google": {
                        "found": r.google.found,
                        "name": r.google.name,
                        "rating": r.google.rating,
                        "review_count": r.google.review_count,
                        "has_photos": r.google.has_photos,
                        "photo_count": r.google.photo_count,
                        "has_opening_hours": r.google.has_opening_hours,
                        "has_phone": r.google.has_phone,
                        "has_website": r.google.has_website
                    },
                    "here": {
                        "found": r.here.found,
                        "name": r.here.name,
                        "rating": r.here.rating,
                        "review_count": r.here.review_count,
                        "has_photos": r.here.has_photos,
                        "has_opening_hours": r.here.has_opening_hours,
                        "has_phone": r.here.has_phone,
                        "has_website": r.here.has_website
                    }
                }
                for r in results
            ]
        }

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        console.print(f"\n[green]Resultados salvos em {args.output}[/green]")


if __name__ == "__main__":
    asyncio.run(main())
