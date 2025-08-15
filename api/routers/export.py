"""
Router para funcionalidades de exportação de dados de rotas e POIs.
"""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from datetime import datetime

from api.models.export_models import ExportRouteData
from api.utils.export_utils import (
    export_to_geojson,
    export_to_gpx,
    export_umap_url,
    export_to_overpass_turbo_url,
)

router = APIRouter(prefix="/export", tags=["Export"])


def create_linear_map_from_export_data(export_data: ExportRouteData):
    """Cria um objeto compatível com LinearMapResponse a partir dos dados de exportação."""
    from api.models.road_models import (
        LinearMapResponse,
        LinearRoadSegment,
        RoadMilestone,
        MilestoneType,
    )
    from api.models.osm_models import Coordinates

    # Converter POIs para milestones
    milestones = []
    for poi in export_data.pois:
        # Mapear tipos de POI para MilestoneType
        milestone_type = MilestoneType.OTHER
        if poi.type == "gas_station":
            milestone_type = MilestoneType.GAS_STATION
        elif poi.type == "restaurant":
            milestone_type = MilestoneType.RESTAURANT
        elif poi.type == "toll_booth":
            milestone_type = MilestoneType.TOLL_BOOTH
        elif poi.type in ["city", "town", "village"]:
            milestone_type = MilestoneType.CITY

        milestone = RoadMilestone(
            id=poi.id,
            name=poi.name,
            type=milestone_type,
            coordinates=Coordinates(lat=poi.coordinates.lat, lon=poi.coordinates.lon),
            distance_from_origin_km=poi.distance_from_origin_km,
            distance_from_road_meters=0.0,
            side="right",
            tags={},
            operator=poi.operator,
            brand=poi.brand,
            opening_hours=poi.opening_hours,
        )
        milestones.append(milestone)

    # Converter segmentos
    segments = []
    for i, seg in enumerate(export_data.segments):
        geometry = [Coordinates(lat=coord.lat, lon=coord.lon) for coord in seg.geometry]
        segment = LinearRoadSegment(
            id=seg.id,
            name=seg.name or f"Segmento {i+1}",
            ref=None,
            start_distance_km=sum(s.length_km for s in export_data.segments[:i]),
            end_distance_km=sum(s.length_km for s in export_data.segments[: i + 1]),
            length_km=seg.length_km,
            geometry=geometry,
            milestones=[],
        )
        segments.append(segment)

    return LinearMapResponse(
        id="export-temp",
        origin=export_data.origin,
        destination=export_data.destination,
        total_length_km=export_data.total_distance_km,
        segments=segments,
        milestones=milestones,
        creation_date=datetime.now(),
        osm_road_id="export-temp",
    )


@router.post("/geojson")
async def export_route_geojson(route_data: ExportRouteData):
    """
    Exporta rota e POIs para formato GeoJSON.
    """
    try:
        linear_map_data = create_linear_map_from_export_data(route_data)
        geojson_data = export_to_geojson(linear_map_data)
        return JSONResponse(content=geojson_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao exportar GeoJSON: {str(e)}"
        )


@router.post("/gpx")
async def export_route_gpx(route_data: ExportRouteData):
    """
    Exporta rota e POIs para formato GPX.
    """
    try:
        import re
        import unicodedata

        def sanitize_filename(text: str) -> str:
            """
            Sanitiza um texto para ser usado como nome de arquivo.
            Remove ou substitui caracteres problemáticos.
            """
            # Normaliza unicode e remove acentos
            text = unicodedata.normalize("NFD", text)
            text = "".join(c for c in text if unicodedata.category(c) != "Mn")

            # Remove caracteres especiais e substitui espaços por underscore
            text = re.sub(r"[^\w\s-]", "", text).strip()
            text = re.sub(r"[-\s]+", "_", text)

            return text

        linear_map_data = create_linear_map_from_export_data(route_data)
        gpx_content = export_to_gpx(linear_map_data)

        # Gera filename sanitizado
        origin_clean = sanitize_filename(route_data.origin)
        destination_clean = sanitize_filename(route_data.destination)
        filename = f"rota_{origin_clean}_{destination_clean}.gpx"

        # Cria filename para o header Content-Disposition com encoding adequado
        filename_encoded = filename.encode("ascii", "ignore").decode("ascii")

        return Response(
            content=f'<?xml version="1.0" encoding="UTF-8"?>\n{gpx_content}',
            media_type="application/gpx+xml",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_encoded}"',
                "Content-Type": "application/gpx+xml",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao exportar GPX: {str(e)}")


@router.post("/web-urls")
async def get_web_visualization_urls(route_data: ExportRouteData):
    """
    Gera URLs para visualização da rota em ferramentas web baseadas em OSM.
    """
    try:
        linear_map_data = create_linear_map_from_export_data(route_data)
        urls = {
            "umap_url": export_umap_url(linear_map_data),
            "overpass_turbo_url": export_to_overpass_turbo_url(linear_map_data),
            "openrouteservice_url": "https://maps.openrouteservice.org/",
            "osrm_map_url": "https://map.project-osrm.org/",
            "instructions": {
                "umap": "1. Clique no link do uMap\n2. Crie um novo mapa\n3. Clique em 'Importar dados'\n4. Carregue o arquivo GeoJSON baixado",
                "overpass_turbo": "Visualize POIs existentes na região da rota para validação",
                "gpx_tools": "Baixe o arquivo GPX e carregue em map.project-osrm.org ou outros visualizadores GPS",
            },
        }
        return JSONResponse(content=urls)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar URLs: {str(e)}")
