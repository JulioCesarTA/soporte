from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import (
    DimensionSerializer,
    DistrictPolygonSerializer,
    DistrictSerializer,
    FilterSetsSerializer,
    HeatPointSerializer,
    ZoneSerializer,
)


@api_view(["GET"])
def health_check(_request):
    return Response({"status": "ok"}, status=status.HTTP_200_OK)


class DimensionListView(APIView):
    def get(self, request):
        filters = request.query_params.dict()
        try:
            items = services.fetch_dimensions(filters)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = DimensionSerializer(items, many=True)
        return Response({"data": serializer.data})


class ZoneSummaryView(APIView):
    def get(self, request):
        filters = request.query_params.dict()
        try:
            items = services.fetch_dimensions(filters)
            payload = services.summarize_by_zone(items)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ZoneSerializer(payload, many=True)
        return Response({"data": serializer.data})


class DistrictSummaryView(APIView):
    def get(self, request):
        filters = request.query_params.dict()
        try:
            items = services.fetch_dimensions(filters)
            payload = services.summarize_by_district(items)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = DistrictSerializer(payload, many=True)
        return Response({"data": serializer.data})


class DistrictPolygonsView(APIView):
    def get(self, request):
        try:
            payload = services.fetch_district_polygons()
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = DistrictPolygonSerializer(payload, many=True)
        return Response({"data": serializer.data})


class HeatmapView(APIView):
    def get(self, request):
        filters = request.query_params.dict()
        try:
            payload = services.fetch_heatmap(filters)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = HeatPointSerializer(payload, many=True)
        return Response({"data": serializer.data})


class FilterOptionsView(APIView):
    def get(self, _request):
        data = services.fetch_filter_options()
        serializer = FilterSetsSerializer(data)
        return Response({"data": serializer.data})
