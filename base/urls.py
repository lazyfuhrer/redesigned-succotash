from django.urls import path, include

from .views import import_csv, export_csv

base_urls = [
    path('base/', include([
        path('import-csv/', import_csv, name='import-csv'),
        path('export-csv/', export_csv, name='export_csv'),
    ]))]

urlpatterns = [
    path('admin/', include(base_urls)),
]
