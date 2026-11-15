
from rest_framework import serializers

from datasources.soilgrids import TEXTURE_CLASSES


class RotationStepSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=1)
    crop = serializers.CharField(max_length=80)
    sow_month = serializers.IntegerField(min_value=1, max_value=12)
    harvest_month = serializers.IntegerField(min_value=1, max_value=12)
    companion = serializers.BooleanField(required=False, default=False)


class CurrentRotationSerializer(serializers.Serializer):
    cycle_years = serializers.IntegerField(min_value=1, max_value=10)
    steps = RotationStepSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        cycle_years = attrs["cycle_years"]

        for step in attrs["steps"]:
            if step["year"] > cycle_years:
                raise serializers.ValidationError(
                    "A rotation step cannot exceed the cycle_years value."
                )

        return attrs


class PrioritiesSerializer(serializers.Serializer):
    water = serializers.IntegerField(min_value=1, max_value=5)
    soil = serializers.IntegerField(min_value=1, max_value=5)
    income = serializers.IntegerField(min_value=1, max_value=5)
    erosion = serializers.IntegerField(min_value=1, max_value=5)
    pest = serializers.IntegerField(min_value=1, max_value=5)


class ConstraintsSerializer(serializers.Serializer):
    water_availability = serializers.ChoiceField(
        choices=["rainfed", "limited_irrigation", "irrigated"]
    )
    equipment = serializers.ChoiceField(
        choices=["basic", "standard", "specialized"]
    )
    market_pref = serializers.ChoiceField(
        choices=["cash", "forage", "balanced"]
    )


class SoilTextureField(serializers.ChoiceField):
    """USDA texture class, also accepting everyday names from the form ("sandy", "clay")."""

    def to_internal_value(self, data):
        from datasources.soilgrids import normalize_texture

        normalized = normalize_texture(data) if isinstance(data, str) else data
        if normalized is None:
            return None
        return super().to_internal_value(normalized)


class OverridesSerializer(serializers.Serializer):
    # Soil texture from the farmer (e.g. "sandy" or "clay loam"); replaces the SoilGrids texture.
    soil_texture = SoilTextureField(
        choices=TEXTURE_CLASSES,
        allow_null=True,
        allow_blank=True,
        required=False,
    )


class ScenarioSerializer(serializers.Serializer):
    rain_pct = serializers.FloatField(min_value=-50, max_value=30)
    temp_c = serializers.FloatField(min_value=-2, max_value=5)


class AnalyzeRequestSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)

    current_rotation = CurrentRotationSerializer(
        allow_null=True,
        required=True,
    )

    priorities = PrioritiesSerializer()
    constraints = ConstraintsSerializer()

    overrides = OverridesSerializer(required=False, default=dict)
    scenario = ScenarioSerializer(required=False, default=dict)
    lang = serializers.ChoiceField(
        choices=["en", "ur"],
        required=False,
        default="en",
    )
