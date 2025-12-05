from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('dimensions/', views.DimensionListView.as_view(), name='dimensions'),
    path('zones/', views.ZoneSummaryView.as_view(), name='zones'),
    path('districts/', views.DistrictSummaryView.as_view(), name='districts'),
    path('district-polygons/', views.DistrictPolygonsView.as_view(), name='district-polygons'),
    path('heatmap/', views.HeatmapView.as_view(), name='heatmap'),
    path('filters/', views.FilterOptionsView.as_view(), name='filters'),
]
