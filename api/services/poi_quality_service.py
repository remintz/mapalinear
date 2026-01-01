"""
POI Quality Service - Quality assessment, filtering, and amenity extraction for POIs.

This service provides stateless methods for:
- Detecting abandoned/closed POIs
- Calculating quality scores based on data completeness
- Checking quality thresholds
- Extracting amenities from OSM tags
- Formatting opening hours
- Filtering POIs by city
"""

from typing import Any, Dict, List, Optional

from api.models.road_models import RoadMilestone


class POIQualityService:
    """
    Service for POI quality assessment and filtering.

    All methods are stateless and can be used without instantiation
    via class methods or by creating an instance.
    """

    def is_poi_abandoned(self, tags: Dict[str, Any]) -> bool:
        """
        Check if a POI is abandoned or out of use.

        Args:
            tags: Tags from geographic provider

        Returns:
            True if the POI should be excluded as abandoned
        """
        abandonment_indicators = [
            "abandoned",
            "disused",
            "demolished",
            "razed",
            "removed",
            "ruins",
            "former",
            "closed",
            "destroyed",
        ]

        # Check direct abandonment tags
        for indicator in abandonment_indicators:
            if tags.get(indicator) in ["yes", "true", "1"]:
                return True
            # Check prefixes (e.g., abandoned:amenity=fuel)
            for key in tags.keys():
                if key.startswith(f"{indicator}:"):
                    return True

        # Check specific status
        if tags.get("opening_hours") in ["closed", "no"]:
            return True

        return False

    def calculate_quality_score(self, tags: Dict[str, Any]) -> float:
        """
        Calculate a quality score for a POI based on data completeness.

        Args:
            tags: Tags from geographic provider

        Returns:
            Score from 0.0 to 1.0, where 1.0 is best quality
        """
        score = 0.0
        max_score = 7.0  # Number of quality criteria

        # Criterion 1: Has name
        if tags.get("name"):
            score += 1.0

        # Criterion 2: Has operator or brand
        if tags.get("operator") or tags.get("brand"):
            score += 1.0

        # Criterion 3: Has phone
        if tags.get("phone") or tags.get("contact:phone"):
            score += 1.0

        # Criterion 4: Has opening hours
        if tags.get("opening_hours"):
            score += 1.0

        # Criterion 5: Has website
        if tags.get("website") or tags.get("contact:website"):
            score += 1.0

        # Criterion 6: For restaurants, has cuisine type
        if tags.get("amenity") == "restaurant" and tags.get("cuisine"):
            score += 1.0
        elif tags.get("amenity") != "restaurant":
            score += 1.0  # Don't penalize non-restaurants

        # Criterion 7: Has structured address
        if any(
            tags.get(f"addr:{field}")
            for field in ["street", "housenumber", "city"]
        ):
            score += 1.0

        return score / max_score

    def meets_quality_threshold(
        self, tags: Dict[str, Any], quality_score: float
    ) -> bool:
        """
        Check if a POI meets the minimum quality threshold.

        Args:
            tags: Tags from geographic provider
            quality_score: Pre-calculated quality score

        Returns:
            True if the POI should be included
        """
        amenity = tags.get("amenity")
        barrier = tags.get("barrier")

        # For gas stations, require name OR brand OR operator
        if amenity == "fuel":
            if not (
                tags.get("name") or tags.get("brand") or tags.get("operator")
            ):
                return False
            return quality_score >= 0.3  # Lower threshold for gas stations

        # For food establishments, require name
        food_amenities = [
            "restaurant",
            "fast_food",
            "cafe",
            "bar",
            "pub",
            "food_court",
            "ice_cream",
        ]
        food_shops = ["bakery"]

        if amenity in food_amenities or tags.get("shop") in food_shops:
            if not tags.get("name"):
                return False
            return quality_score >= 0.4  # Medium threshold for food

        # For toll booths, always include (even without name)
        if barrier == "toll_booth":
            return True

        # For other types, default threshold
        return quality_score >= 0.3

    def extract_amenities(self, tags: Dict[str, Any]) -> List[str]:
        """
        Extract list of amenities from POI tags.

        Args:
            tags: Tags from geographic provider

        Returns:
            List of amenities found
        """
        amenities = []

        # Mapping of tags to readable amenities
        amenity_mappings = {
            # Connectivity
            "internet_access": {"wifi", "internet"},
            "wifi": {"wifi"},
            # Parking
            "parking": {"estacionamento"},
            "parking:fee": {"estacionamento pago"},
            # Accessibility
            "wheelchair": {"acessível"},
            # Payment
            "payment:cash": {"dinheiro"},
            "payment:cards": {"cartão"},
            "payment:contactless": {"contactless"},
            "payment:credit_cards": {"cartão de crédito"},
            "payment:debit_cards": {"cartão de débito"},
            # Specific fuel
            "fuel:diesel": {"diesel"},
            "fuel:octane_91": {"gasolina comum"},
            "fuel:octane_95": {"gasolina aditivada"},
            "fuel:lpg": {"GNV"},
            "fuel:ethanol": {"etanol"},
            # Services
            "toilets": {"banheiro"},
            "shower": {"chuveiro"},
            "restaurant": {"restaurante"},
            "cafe": {"café"},
            "shop": {"loja"},
            "atm": {"caixa eletrônico"},
            "car_wash": {"lava-jato"},
            "compressed_air": {"calibragem"},
            "vacuum_cleaner": {"aspirador"},
            # Other
            "outdoor_seating": {"área externa"},
            "air_conditioning": {"ar condicionado"},
            "takeaway": {"delivery"},
            "delivery": {"delivery"},
            "drive_through": {"drive-thru"},
        }

        # Check each tag and add corresponding amenities
        for tag_key, tag_value in tags.items():
            # Normalize tag value
            if isinstance(tag_value, str):
                tag_value = tag_value.lower()

            # Check if tag indicates presence of amenity
            if tag_value in ["yes", "true", "1", "available"]:
                if tag_key in amenity_mappings:
                    amenities.extend(amenity_mappings[tag_key])
                elif (
                    tag_key.startswith("payment:")
                    and tag_key in amenity_mappings
                ):
                    amenities.extend(amenity_mappings[tag_key])

        # Special amenities based on type
        amenity_type = tags.get("amenity")
        if amenity_type == "fuel":
            # For gas stations, assume basic amenities if not specified
            if not any("banheiro" in a for a in amenities) and tags.get(
                "toilets"
            ) != "no":
                amenities.append("banheiro")

        # Amenities based on hours
        opening_hours = tags.get("opening_hours", "")
        if "24/7" in opening_hours or "Mo-Su 00:00-24:00" in opening_hours:
            amenities.append("24h")

        # Remove duplicates and sort
        amenities = sorted(list(set(amenities)))

        return amenities

    def format_opening_hours(
        self, opening_hours: Optional[Dict[str, str]]
    ) -> Optional[str]:
        """
        Format opening hours dict to string.

        Args:
            opening_hours: Dictionary mapping days to hours

        Returns:
            Formatted string like "Mon-Fri: 8:00-18:00, Sat: 9:00-17:00"
        """
        if not opening_hours:
            return None

        formatted = []
        for day, hours in opening_hours.items():
            formatted.append(f"{day}: {hours}")

        return ", ".join(formatted)

    def filter_by_excluded_cities(
        self,
        milestones: List[RoadMilestone],
        excluded_cities: List[str],
    ) -> List[RoadMilestone]:
        """
        Filter out milestones in excluded cities.

        Args:
            milestones: List of milestones to filter
            excluded_cities: List of city names to exclude (case-insensitive)

        Returns:
            Filtered list of milestones
        """
        if not excluded_cities:
            return milestones

        # Normalize excluded cities
        excluded_normalized = [city.strip().lower() for city in excluded_cities if city]

        if not excluded_normalized:
            return milestones

        # Filter
        return [
            m
            for m in milestones
            if not m.city or m.city.strip().lower() not in excluded_normalized
        ]


# Module-level instance for convenience
_default_service = POIQualityService()


# Convenience functions for direct use without instantiation
def is_poi_abandoned(tags: Dict[str, Any]) -> bool:
    """Check if a POI is abandoned."""
    return _default_service.is_poi_abandoned(tags)


def calculate_quality_score(tags: Dict[str, Any]) -> float:
    """Calculate quality score for a POI."""
    return _default_service.calculate_quality_score(tags)


def meets_quality_threshold(tags: Dict[str, Any], quality_score: float) -> bool:
    """Check if POI meets quality threshold."""
    return _default_service.meets_quality_threshold(tags, quality_score)


def extract_amenities(tags: Dict[str, Any]) -> List[str]:
    """Extract amenities from POI tags."""
    return _default_service.extract_amenities(tags)


def format_opening_hours(
    opening_hours: Optional[Dict[str, str]]
) -> Optional[str]:
    """Format opening hours to string."""
    return _default_service.format_opening_hours(opening_hours)


def filter_by_excluded_cities(
    milestones: List[RoadMilestone], excluded_cities: List[str]
) -> List[RoadMilestone]:
    """Filter milestones by excluded cities."""
    return _default_service.filter_by_excluded_cities(milestones, excluded_cities)
