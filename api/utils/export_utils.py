"""
Utilidades para exportar dados de rotas e POIs para visualização em ferramentas web de mapas.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from api.models.road_models import LinearMapResponse


def export_to_geojson(
    route_response: LinearMapResponse,
    output_file: str = None
) -> Dict[str, Any]:
    """
    Exporta rota e POIs para formato GeoJSON para visualização em ferramentas web de mapas.
    
    Args:
        route_response: Resposta completa da rota linear
        output_file: Caminho opcional para salvar o arquivo
        
    Returns:
        Dicionário GeoJSON
        
    Ferramentas compatíveis:
    - uMap (umap.openstreetmap.fr)
    - Overpass Turbo (overpass-turbo.eu)
    - QGIS, OpenLayers, Leaflet, etc.
    """
    
    # Estrutura base do GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "title": f"Rota Linear: {route_response.origin} → {route_response.destination}",
            "description": f"Rota de {route_response.total_length_km:.1f}km com {len(route_response.milestones)} POIs",
            "generated_at": datetime.now().isoformat(),
            "total_distance_km": route_response.total_length_km
        }
    }
    
    # 1. Adicionar linha da rota (LineString)
    route_coordinates = []
    for segment in route_response.segments:
        for coord in segment.geometry:
            route_coordinates.append([coord.longitude, coord.latitude])  # GeoJSON usa [lon, lat]
    
    if route_coordinates:
        route_feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": route_coordinates
            },
            "properties": {
                "name": f"Rota {route_response.origin} → {route_response.destination}",
                "stroke": "#2563eb",  # Azul
                "stroke-width": 4,
                "stroke-opacity": 0.8,
                "type": "route",
                "distance_km": route_response.total_length_km
            }
        }
        geojson["features"].append(route_feature)
    
    # 2. Adicionar POIs como pontos
    poi_colors = {
        "gas_station": "#dc2626",     # Vermelho
        "restaurant": "#16a34a",      # Verde  
        "toll_booth": "#ca8a04",      # Amarelo/Laranja
        "city": "#7c3aed",            # Roxo
        "town": "#7c3aed",
        "village": "#7c3aed",
        "other": "#6b7280"            # Cinza
    }
    
    for poi in route_response.milestones:
        poi_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [poi.coordinates.longitude, poi.coordinates.latitude]
            },
            "properties": {
                "name": poi.name,
                "type": poi.type,
                "marker-color": poi_colors.get(str(poi.type), poi_colors["other"]),
                "marker-size": "medium",
                "marker-symbol": _get_poi_symbol(str(poi.type)),
                "distance_from_origin_km": round(poi.distance_from_origin_km, 2),
                "description": f"{poi.name} ({poi.type}) - {poi.distance_from_origin_km:.1f}km do início"
            }
        }
        
        # Adicionar propriedades específicas do POI se disponíveis
        if hasattr(poi, 'brand') and poi.brand:
            poi_feature["properties"]["brand"] = poi.brand
        if hasattr(poi, 'operator') and poi.operator:
            poi_feature["properties"]["operator"] = poi.operator
        if hasattr(poi, 'opening_hours') and poi.opening_hours:
            poi_feature["properties"]["opening_hours"] = poi.opening_hours
            
        geojson["features"].append(poi_feature)
    
    # 3. Salvar arquivo se especificado
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
            
        print(f"GeoJSON exportado para: {output_path}")
        print(f"✅ Abra em: https://umap.openstreetmap.fr/ (criar mapa → importar dados)")
    
    return geojson


def export_to_gpx(
    route_response: LinearMapResponse,
    output_file: str = None
) -> str:
    """
    Exporta rota e POIs para formato GPX para visualização em aplicativos GPS e ferramentas web.
    
    Args:
        route_response: Resposta completa da rota linear
        output_file: Caminho opcional para salvar o arquivo
        
    Returns:
        String XML do GPX
        
    Ferramentas compatíveis:
    - OSRM Map (map.project-osrm.org)
    - OpenRouteService (maps.openrouteservice.org)
    - Garmin, Strava, aplicativos GPS móveis
    """
    
    # Criar elemento raiz GPX
    gpx = ET.Element("gpx", {
        "version": "1.1",
        "creator": "MapaLinear",
        "xmlns": "http://www.topografix.com/GPX/1/1",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd"
    })
    
    # Metadados
    metadata = ET.SubElement(gpx, "metadata")
    ET.SubElement(metadata, "name").text = f"Rota {route_response.origin} → {route_response.destination}"
    ET.SubElement(metadata, "desc").text = f"Rota linear de {route_response.total_length_km:.1f}km com {len(route_response.milestones)} POIs"
    ET.SubElement(metadata, "time").text = datetime.now().isoformat()
    
    # 1. Adicionar POIs como waypoints
    for poi in route_response.milestones:
        wpt = ET.SubElement(gpx, "wpt", {
            "lat": str(poi.coordinates.latitude),
            "lon": str(poi.coordinates.longitude)
        })
        ET.SubElement(wpt, "name").text = poi.name
        ET.SubElement(wpt, "desc").text = f"{str(poi.type)} - {poi.distance_from_origin_km:.1f}km do início"
        ET.SubElement(wpt, "type").text = str(poi.type)
        
        # Símbolo específico por tipo
        ET.SubElement(wpt, "sym").text = _get_gpx_symbol(str(poi.type))
    
    # 2. Adicionar rota como track
    trk = ET.SubElement(gpx, "trk")
    ET.SubElement(trk, "name").text = f"Rota {route_response.origin} → {route_response.destination}"
    ET.SubElement(trk, "desc").text = f"Rota completa de {route_response.total_length_km:.1f}km"
    
    trkseg = ET.SubElement(trk, "trkseg")
    
    for segment in route_response.segments:
        for coord in segment.geometry:
            trkpt = ET.SubElement(trkseg, "trkpt", {
                "lat": str(coord.latitude),
                "lon": str(coord.longitude)
            })
    
    # Converter para string XML
    ET.indent(gpx, space="  ")
    xml_string = ET.tostring(gpx, encoding='unicode')
    
    # 3. Salvar arquivo se especificado
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml_string)
            
        print(f"GPX exportado para: {output_path}")
        print(f"✅ Abra em: https://map.project-osrm.org/ (arrastar arquivo GPX)")
    
    return xml_string


def export_umap_url(route_response: LinearMapResponse) -> str:
    """
    Gera URL para visualização rápida no uMap com coordenadas da rota.
    
    Args:
        route_response: Resposta completa da rota linear
        
    Returns:
        URL do uMap centralizada na rota
    """
    
    # Calcular centro da rota
    if route_response.segments and route_response.segments[0].geometry:
        first_coord = route_response.segments[0].geometry[0]
        last_coord = route_response.segments[-1].geometry[-1]
        
        center_lat = (first_coord.latitude + last_coord.latitude) / 2
        center_lon = (first_coord.longitude + last_coord.longitude) / 2
        
        # Estimar zoom baseado na distância
        if route_response.total_length_km > 300:
            zoom = 8
        elif route_response.total_length_km > 100:
            zoom = 10
        else:
            zoom = 12
            
        url = f"https://umap.openstreetmap.fr/pt/map/new/#{zoom}/{center_lat:.4f}/{center_lon:.4f}"
        
        print(f"🗺️  URL do uMap: {url}")
        print(f"   1. Abra o link")
        print(f"   2. Clique em 'Importar dados'")
        print(f"   3. Carregue o arquivo GeoJSON gerado")
        
        return url
    
    return "https://umap.openstreetmap.fr/"


def _get_poi_symbol(poi_type: str) -> str:
    """Retorna símbolo apropriado para cada tipo de POI (GeoJSON/Maki icons)."""
    symbols = {
        "gas_station": "fuel",
        "restaurant": "restaurant", 
        "toll_booth": "toll",
        "city": "city",
        "town": "town",
        "village": "village",
        "other": "marker"
    }
    return symbols.get(poi_type, "marker")


def _get_gpx_symbol(poi_type: str) -> str:
    """Retorna símbolo apropriado para cada tipo de POI (formato GPX)."""
    symbols = {
        "gas_station": "Gas Station",
        "restaurant": "Restaurant",
        "toll_booth": "Toll Booth", 
        "city": "City",
        "town": "City",
        "village": "City",
        "other": "Waypoint"
    }
    return symbols.get(poi_type, "Waypoint")


def export_to_overpass_turbo_url(
    route_response: LinearMapResponse,
    poi_types: List[str] = None
) -> str:
    """
    Gera URL do Overpass Turbo para validar POIs na região da rota.
    
    Args:
        route_response: Resposta da rota
        poi_types: Tipos de POI para buscar (opcional)
        
    Returns:
        URL do Overpass Turbo com query personalizada
    """
    
    if not route_response.segments:
        return "https://overpass-turbo.eu/"
    
    # Calcular bounding box da rota
    lats = []
    lons = []
    
    for segment in route_response.segments:
        for coord in segment.geometry:
            lats.append(coord.latitude)
            lons.append(coord.longitude)
    
    if not lats:
        return "https://overpass-turbo.eu/"
    
    min_lat = min(lats) - 0.01  # Pequena margem
    max_lat = max(lats) + 0.01
    min_lon = min(lons) - 0.01  
    max_lon = max(lons) + 0.01
    
    # Query Overpass para POIs relevantes
    poi_types = poi_types or ["fuel", "restaurant", "toll_booth"]
    
    overpass_query = f"""[out:json][timeout:25];
(
  nwr["amenity"="fuel"]({min_lat},{min_lon},{max_lat},{max_lon});
  nwr["amenity"="restaurant"]({min_lat},{min_lon},{max_lat},{max_lon});
  nwr["barrier"="toll_booth"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out geom;"""

    # Codificar query para URL
    import urllib.parse
    encoded_query = urllib.parse.quote(overpass_query)
    
    url = f"https://overpass-turbo.eu/?Q={encoded_query}"
    
    print(f"🔍 URL do Overpass Turbo: {url}")
    print(f"   Use para validar se os POIs encontrados existem na região")
    
    return url



def export_to_pdf(
    route_response: LinearMapResponse,
    output_file: str = None,
    poi_types_filter: List[str] = None
) -> bytes:
    """
    Exporta lista de POIs para formato PDF.
    
    Args:
        route_response: Resposta completa da rota linear
        output_file: Caminho opcional para salvar o arquivo
        poi_types_filter: Lista opcional de tipos de POI para incluir no PDF
        
    Returns:
        Bytes do arquivo PDF gerado
        
    O PDF contém uma lista formatada de todos os POIs da rota com:
    - Nome do POI
    - Tipo
    - Distância da origem
    - Marca/Operador (quando disponível)
    - Horário de funcionamento (quando disponível)
    """
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )
    
    # Criar buffer de memória para o PDF
    buffer = BytesIO()
    
    # Configurar documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Estilo para cabeçalhos de seção
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    # Elementos do documento
    elements = []
    
    # Título
    title = Paragraph(
        f"Lista de Pontos de Interesse",
        title_style
    )
    elements.append(title)
    
    # Subtítulo com informações da rota
    subtitle = Paragraph(
        f"{route_response.origin} → {route_response.destination}<br/>"
        f"Distância total: {route_response.total_length_km:.1f} km",
        subtitle_style
    )
    elements.append(subtitle)
    elements.append(Spacer(1, 0.5*cm))
    
    # Filtrar POIs se necessário
    milestones = route_response.milestones
    if poi_types_filter:
        milestones = [m for m in milestones if str(m.type) in poi_types_filter]
    
    # Informação sobre POIs
    info_text = Paragraph(
        f"Total de POIs: {len(milestones)}<br/>"
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        styles['Normal']
    )
    elements.append(info_text)
    elements.append(Spacer(1, 0.8*cm))

    # Mapear tipos de POI para nomes em português (igual à tabela da página)
    type_display = {
        "gas_station": "Posto",
        "restaurant": "Restaurante",
        "fast_food": "Fast Food",
        "cafe": "Café",
        "toll_booth": "Pedágio",
        "hotel": "Hotel",
        "lodging": "Hospedagem",
        "camping": "Camping",
        "hospital": "Hospital",
        "city": "Cidade",
        "town": "Vila",
        "village": "Povoado",
        "other": "Outro"
    }

    # Criar tabela única com todos os POIs
    table_data = []

    # Cabeçalho da tabela
    table_data.append([
        Paragraph('<b>KM</b>', styles['Normal']),
        Paragraph('<b>Tipo</b>', styles['Normal']),
        Paragraph('<b>Nome</b>', styles['Normal']),
        Paragraph('<b>Detalhes</b>', styles['Normal'])
    ])

    # Ordenar todos os POIs por distância
    milestones_sorted = sorted(milestones, key=lambda p: p.distance_from_origin_km)

    for poi in milestones_sorted:
        # Distância
        distance = Paragraph(
            f"<b>{poi.distance_from_origin_km:.1f}</b>",
            styles['Normal']
        )

        # Tipo do POI - extrair o valor do enum corretamente
        if hasattr(poi.type, 'value'):
            poi_type_str = poi.type.value
        else:
            poi_type_str = str(poi.type).lower()

        type_label = type_display.get(poi_type_str, poi_type_str.replace('_', ' ').title())
        poi_type = Paragraph(type_label, styles['Normal'])

        # Nome do POI
        name = Paragraph(poi.name or 'Sem nome', styles['Normal'])

        # Detalhes adicionais
        details = []
        if hasattr(poi, 'brand') and poi.brand:
            details.append(f"<b>Marca:</b> {poi.brand}")
        if hasattr(poi, 'operator') and poi.operator:
            details.append(f"<b>Operador:</b> {poi.operator}")
        if hasattr(poi, 'opening_hours') and poi.opening_hours:
            details.append(f"<b>Horário:</b> {poi.opening_hours}")

        details_text = '<br/>'.join(details) if details else '-'
        details_para = Paragraph(details_text, styles['Normal'])

        table_data.append([distance, poi_type, name, details_para])

    # Criar e estilizar tabela
    table = Table(table_data, colWidths=[2*cm, 3.5*cm, 5.5*cm, 6*cm])
    table.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),

        # Células de dados
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Centralizar coluna KM
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 1), (-1, -1), 6),
        ('RIGHTPADDING', (0, 1), (-1, -1), 6),

        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),

        # Linhas alternadas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')])
    ]))

    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    
    # Obter bytes do PDF
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    # Salvar arquivo se especificado
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"📄 PDF exportado para: {output_path}")
    
    return pdf_bytes
