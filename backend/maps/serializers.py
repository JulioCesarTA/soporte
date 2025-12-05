from rest_framework import serializers


class DimensionSerializer(serializers.Serializer):
    name = serializers.CharField(allow_blank=True, allow_null=True)
    zone = serializers.CharField(allow_blank=True, allow_null=True)
    district = serializers.CharField(allow_blank=True, allow_null=True)
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)
    value = serializers.FloatField(allow_null=True)
    color = serializers.CharField()


class ZoneSerializer(serializers.Serializer):
    zone = serializers.CharField()
    color = serializers.CharField()
    count = serializers.IntegerField()
    district_count = serializers.IntegerField()
    sample = DimensionSerializer(many=True)


class DistrictSerializer(serializers.Serializer):
    district = serializers.CharField()
    color = serializers.CharField()
    count = serializers.IntegerField()


class DistrictPolygonSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    color = serializers.CharField()
    polygons = serializers.ListField(
        child=serializers.ListField(
            child=serializers.DictField(child=serializers.FloatField())
        )
    )


class HeatPointSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    count = serializers.IntegerField()
    device_id = serializers.IntegerField()


class FilterOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class FilterSetsSerializer(serializers.Serializer):
    moments = FilterOptionSerializer(many=True)
    altitude_levels = FilterOptionSerializer(many=True)
    signal_levels = FilterOptionSerializer(many=True)
    speed_levels = FilterOptionSerializer(many=True)
    operators = FilterOptionSerializer(many=True)
    networks = FilterOptionSerializer(many=True)
