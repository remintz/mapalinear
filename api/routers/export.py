"""
Router para funcionalidades de exportação de dados de rotas e POIs.
"""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from typing import Optional, List
import json
from datetime import datetime

from api.models.export_models import ExportRouteData
from api.utils.export_utils import (
    export_to_geojson,
    export_to_gpx,
    export_umap_url,
    export_to_overpass_turbo_url
)

router = APIRouter(prefix="/export", tags=["Export"])


def create_linear_map_from_export_data(export_data: ExportRouteData):
    """Cria um objeto compatível com LinearMapResponse a partir dos dados de exportação."""
    from api.models.road_models import LinearMapResponse, LinearRoadSegment, RoadMilestone, MilestoneType
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
            opening_hours=poi.opening_hours
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
            end_distance_km=sum(s.length_km for s in export_data.segments[:i+1]),
            length_km=seg.length_km,
            geometry=geometry,
            milestones=[]  # Não vamos associar milestones específicos aos segmentos
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
        osm_road_id="export-temp"
    )


@router.post("/geojson")
async def export_route_geojson(route_data: ExportRouteData):
    """
    Exporta rota e POIs para formato GeoJSON.
    
    Retorna o GeoJSON para download direto ou visualização em ferramentas web como uMap.
    """
    try:
        # Criar um objeto temporário compatível com export_to_geojson
        linear_map_data = create_linear_map_from_export_data(route_data)
        geojson_data = export_to_geojson(linear_map_data)
        
        # Retornar JSON simples para o frontend processar
        return JSONResponse(content=geojson_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao exportar GeoJSON: {str(e)}")


@router.post("/gpx")
async def export_route_gpx(route_data: ExportRouteData):
    """
    Exporta rota e POIs para formato GPX.
    
    Retorna o GPX para download direto ou carregamento em aplicativos GPS.
    """
    try:
        linear_map_data = create_linear_map_from_export_data(route_data)
        gpx_content = export_to_gpx(linear_map_data)
        
        filename = f"rota_{route_data.origin.replace(' ', '_')}_{route_data.destination.replace(' ', '_')}.gpx"
        
        return Response(
            content=f'<?xml version="1.0" encoding="UTF-8"?>\n{gpx_content}',
            media_type="application/gpx+xml",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/gpx+xml"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao exportar GPX: {str(e)}")


@router.post("/web-urls")
async def get_web_visualization_urls(route_data: ExportRouteData):
    """
    Gera URLs para visualização da rota em ferramentas web baseadas em OSM.
    
    Retorna URLs para uMap, Overpass Turbo e outras ferramentas.
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
                "gpx_tools": "Baixe o arquivo GPX e carregue em map.project-osrm.org ou outros visualizadores GPS"
            }
        }
        
        return JSONResponse(content=urls)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar URLs: {str(e)}")


@router.post("/summary")
async def get_export_summary(route_data: ExportRouteData):
    """
    Retorna resumo da rota para exibição antes da exportação.
    """
    try:
        # Calcular estatísticas
        poi_counts = {}
        for poi in route_data.pois:
            poi_type = poi.type
            poi_counts[poi_type] = poi_counts.get(poi_type, 0) + 1
        
        # Calcular bounding box
        all_coords = []
        for segment in route_data.segments:
            for coord in segment.geometry:
                all_coords.append((coord.lat, coord.lon))
        
        if all_coords:
            min_lat = min(coord[0] for coord in all_coords)
            max_lat = max(coord[0] for coord in all_coords)
            min_lon = min(coord[1] for coord in all_coords)
            max_lon = max(coord[1] for coord in all_coords)
        else:
            min_lat = max_lat = min_lon = max_lon = 0
        
        summary = {
            "route_info": {
                "origin": route_data.origin,
                "destination": route_data.destination,
                "total_distance_km": route_data.total_distance_km,
                "total_segments": len(route_data.segments),
                "total_pois": len(route_data.pois)
            },
            "poi_breakdown": poi_counts,
            "bounding_box": {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon
            },
            "export_formats": [
                {
                    "format": "GeoJSON",
                    "description": "Para uMap, QGIS, OpenLayers",
                    "file_extension": ".geojson",
                    "use_case": "Visualização web interativa"
                },
                {
                    "format": "GPX",
                    "description": "Para GPS, Strava, aplicativos móveis",
                    "file_extension": ".gpx", 
                    "use_case": "Navegação GPS e análise de rota"
                }
            ]
        }
        
        return JSONResponse(content=summary)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resumo: {str(e)}")