import uuid
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime
import osmnx as ox
import geopy.distance

from api.models.road_models import (
    LinearMapResponse,
    LinearRoadSegment,
    RoadMilestone,
    RoadMilestoneResponse,
    SavedMapResponse,
    MilestoneType,
)
from api.services.osm_service import OSMService
from api.models.osm_models import Coordinates

logger = logging.getLogger(__name__)

class RoadService:
    def __init__(self):
        self.osm_service = OSMService()
        # In a real implementation, you would have a database connection here
        self.saved_maps = {}  # Simple in-memory storage for now
    
    def generate_linear_map(
        self,
        origin: str,
        destination: str,
        road_id: Optional[str] = None,
        include_cities: bool = True,
        include_gas_stations: bool = True,
        include_restaurants: bool = False,
        include_toll_booths: bool = True,
        max_distance_from_road: float = 1000
    ) -> LinearMapResponse:
        """
        Gera um mapa linear de uma estrada entre os pontos de origem e destino.
        """
        # Step 1: Get road data from OSM
        if road_id is None:
            # Search for road data if not provided
            osm_response = self.osm_service.search_road_data(origin, destination)
            road_id = osm_response.road_id
        else:
            # TODO: Retrieve road data from database
            # For now, search again
            osm_response = self.osm_service.search_road_data(origin, destination)
        
        # Step 2: Process road segments into linear segments
        linear_segments = self._process_road_segments(osm_response.road_segments)
        
        # Step 3: Find milestones along the road
        milestone_types = []
        if include_cities:
            milestone_types.extend(["city", "town", "village"])
        if include_gas_stations:
            milestone_types.append("gas_station")
        if include_restaurants:
            milestone_types.append("restaurant")
        if include_toll_booths:
            milestone_types.append("toll_booth")
        
        # In a real implementation, this would query OSM for POIs near the road
        # For now, we'll add some placeholder milestones
        all_milestones = self._find_milestones_along_road(
            osm_response.road_segments,
            milestone_types,
            max_distance_from_road
        )
        
        # Step 4: Assign milestones to segments
        for segment in linear_segments:
            segment.milestones = [
                milestone for milestone in all_milestones
                if segment.start_distance_km <= milestone.distance_from_origin_km <= segment.end_distance_km
            ]
        
        # Create linear map response
        linear_map = LinearMapResponse(
            origin=origin,
            destination=destination,
            total_length_km=osm_response.total_length_km,
            segments=linear_segments,
            milestones=all_milestones,
            osm_road_id=road_id
        )
        
        # Save the map for later retrieval
        self.saved_maps[linear_map.id] = linear_map
        
        return linear_map
    
    def _process_road_segments(self, osm_segments: List[Any]) -> List[LinearRoadSegment]:
        """
        Process OSM road segments into linear road segments.
        """
        linear_segments = []
        current_distance = 0
        
        for i, segment in enumerate(osm_segments):
            start_distance = current_distance
            length_km = segment.length_meters / 1000
            end_distance = start_distance + length_km
            
            linear_segment = LinearRoadSegment(
                id=str(uuid.uuid4()),
                start_distance_km=start_distance,
                end_distance_km=end_distance,
                length_km=length_km,
                name=segment.name,
                ref=segment.ref,
                start_milestone=None,
                end_milestone=None,
                milestones=[]
            )
            
            linear_segments.append(linear_segment)
            current_distance = end_distance
        
        return linear_segments
    
    def _find_milestones_along_road(
        self, 
        road_segments: List[Any], 
        milestone_types: List[str], 
        max_distance: float
    ) -> List[RoadMilestone]:
        """
        Find milestones along a road.
        In a real implementation, this would use Overpass API to find POIs.
        """
        # This is a placeholder implementation
        # In a real implementation, you would query Overpass API for POIs near the road
        
        milestones = []
        
        # Create some placeholder milestones for demonstration
        # In a real implementation, these would come from OSM data
        
        # Example city milestone at the beginning of the road
        if "city" in milestone_types:
            start_milestone = RoadMilestone(
                id=str(uuid.uuid4()),
                name="Cidade Inicial",
                type=MilestoneType.CITY,
                coordinates=road_segments[0].geometry[0],
                distance_from_origin_km=0.0,
                distance_from_road_meters=0.0,
                side="center",
                tags={}
            )
            milestones.append(start_milestone)
            
            # Example city milestone in the middle of the road
            if len(road_segments) > 3:
                middle_segment = road_segments[len(road_segments) // 2]
                middle_point = middle_segment.geometry[len(middle_segment.geometry) // 2]
                
                middle_milestone = RoadMilestone(
                    id=str(uuid.uuid4()),
                    name="Cidade Intermediária",
                    type=MilestoneType.CITY,
                    coordinates=middle_point,
                    distance_from_origin_km=sum(segment.length_meters for segment in road_segments[:len(road_segments) // 2]) / 1000,
                    distance_from_road_meters=0.0,
                    side="right",
                    tags={}
                )
                milestones.append(middle_milestone)
            
            # Example city milestone at the end of the road
            end_milestone = RoadMilestone(
                id=str(uuid.uuid4()),
                name="Cidade Final",
                type=MilestoneType.CITY,
                coordinates=road_segments[-1].geometry[-1],
                distance_from_origin_km=sum(segment.length_meters for segment in road_segments) / 1000,
                distance_from_road_meters=0.0,
                side="center",
                tags={}
            )
            milestones.append(end_milestone)
        
        # Example gas station milestones
        if "gas_station" in milestone_types and len(road_segments) > 2:
            # Place gas stations at regular intervals
            total_length_km = sum(segment.length_meters for segment in road_segments) / 1000
            num_gas_stations = max(1, int(total_length_km / 50))  # One gas station every 50 km
            
            for i in range(num_gas_stations):
                target_distance_km = (i + 1) * (total_length_km / (num_gas_stations + 1))
                
                # Find the segment that contains this distance
                current_distance = 0
                for segment in road_segments:
                    next_distance = current_distance + segment.length_meters / 1000
                    if current_distance <= target_distance_km <= next_distance:
                        # Found the segment, now interpolate the position
                        fraction = (target_distance_km - current_distance) / (next_distance - current_distance)
                        
                        # Simple linear interpolation of geometry
                        if len(segment.geometry) > 1:
                            idx = int(fraction * (len(segment.geometry) - 1))
                            point = segment.geometry[idx]
                        else:
                            point = segment.geometry[0]
                        
                        gas_station = RoadMilestone(
                            id=str(uuid.uuid4()),
                            name=f"Posto de Gasolina {i+1}",
                            type=MilestoneType.GAS_STATION,
                            coordinates=point,
                            distance_from_origin_km=target_distance_km,
                            distance_from_road_meters=50.0,  # Arbitrary distance from road
                            side="right" if i % 2 == 0 else "left",  # Alternate sides
                            tags={}
                        )
                        milestones.append(gas_station)
                        break
                    
                    current_distance = next_distance
        
        # Similarly, add toll booths and restaurants if requested
        if "toll_booth" in milestone_types and len(road_segments) > 4:
            # Place toll booths at regular intervals
            total_length_km = sum(segment.length_meters for segment in road_segments) / 1000
            num_toll_booths = max(1, int(total_length_km / 100))  # One toll booth every 100 km
            
            for i in range(num_toll_booths):
                target_distance_km = (i + 1) * (total_length_km / (num_toll_booths + 1))
                
                # Find the segment that contains this distance
                current_distance = 0
                for segment in road_segments:
                    next_distance = current_distance + segment.length_meters / 1000
                    if current_distance <= target_distance_km <= next_distance:
                        # Found the segment, now interpolate the position
                        fraction = (target_distance_km - current_distance) / (next_distance - current_distance)
                        
                        # Simple linear interpolation of geometry
                        if len(segment.geometry) > 1:
                            idx = int(fraction * (len(segment.geometry) - 1))
                            point = segment.geometry[idx]
                        else:
                            point = segment.geometry[0]
                        
                        toll_booth = RoadMilestone(
                            id=str(uuid.uuid4()),
                            name=f"Pedágio {i+1}",
                            type=MilestoneType.TOLL_BOOTH,
                            coordinates=point,
                            distance_from_origin_km=target_distance_km,
                            distance_from_road_meters=0.0,  # On the road
                            side="center",
                            tags={}
                        )
                        milestones.append(toll_booth)
                        break
                    
                    current_distance = next_distance
        
        return milestones
    
    def get_road_milestones(
        self, 
        road_id: str, 
        origin: Optional[str] = None, 
        destination: Optional[str] = None, 
        milestone_type: Optional[str] = None
    ) -> List[RoadMilestoneResponse]:
        """
        Obtém marcos importantes ao longo de uma estrada.
        """
        # In a real implementation, this would query the database for milestones
        # For now, we'll generate some milestones if we have the road in memory
        
        # Look for the road in saved maps
        for map_id, map_data in self.saved_maps.items():
            if map_data.osm_road_id == road_id:
                # Filter milestones by type if requested
                milestones = map_data.milestones
                if milestone_type:
                    milestones = [m for m in milestones if m.type.value == milestone_type]
                
                # Convert to response format
                return [
                    RoadMilestoneResponse(
                        id=milestone.id,
                        name=milestone.name,
                        type=milestone.type,
                        coordinates=milestone.coordinates,
                        distance_from_origin_km=milestone.distance_from_origin_km,
                        road_id=road_id,
                        road_name=None,  # Would come from database in real implementation
                        road_ref=None  # Would come from database in real implementation
                    )
                    for milestone in milestones
                ]
        
        # If road not found in saved maps, return empty list
        return []
    
    def get_saved_maps(self) -> List[SavedMapResponse]:
        """
        Obtém todos os mapas salvos anteriormente.
        """
        return [
            SavedMapResponse(
                id=map_id,
                name=None,  # User-provided names would be stored in a real implementation
                origin=map_data.origin,
                destination=map_data.destination,
                total_length_km=map_data.total_length_km,
                creation_date=map_data.creation_date,
                road_refs=[segment.ref for segment in map_data.segments if segment.ref],
                milestone_count=len(map_data.milestones)
            )
            for map_id, map_data in self.saved_maps.items()
        ]
    
    def get_saved_map(self, map_id: str) -> Optional[SavedMapResponse]:
        """
        Obtém um mapa salvo pelo seu ID.
        """
        if map_id in self.saved_maps:
            map_data = self.saved_maps[map_id]
            return SavedMapResponse(
                id=map_id,
                name=None,  # User-provided names would be stored in a real implementation
                origin=map_data.origin,
                destination=map_data.destination,
                total_length_km=map_data.total_length_km,
                creation_date=map_data.creation_date,
                road_refs=[segment.ref for segment in map_data.segments if segment.ref],
                milestone_count=len(map_data.milestones)
            )
        return None