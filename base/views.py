import csv

from django.apps import apps
from django.db import models
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import CSVImportForm, CSVExportForm


def import_csv(request):
    if 'template' in request.GET:
        model_label = request.GET['template']
        model = apps.get_model(model_label)
        response = HttpResponse(content_type='text/csv')
        response[
            'Content-Disposition'] = 'attachment; filename="sample_template.csv"'

        writer = csv.writer(response)
        headers = [field.name for field in model._meta.fields]
        writer.writerow(headers)

        return response

    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            model_label = form.cleaned_data['model_choice']
            model = apps.get_model(model_label)
            csv_file = request.FILES['csv_file']
            content = csv_file.read().decode('utf-8')
            reader = csv.DictReader(content.splitlines())
            for row in reader:
                # Fetch the model's fields and their types
                field_types = {f.name: type(f) for f in model._meta.fields}
                null_fields = [f.name for f in model._meta.fields if f.null]
                # Process each field in the row
                for field, value in row.items():
                    # Check if the field is a ForeignKey
                    if field in null_fields and not value.strip():
                        row[field] = None
                        continue
                    elif field in field_types and value and issubclass(
                        field_types[field], models.ForeignKey):
                        # Get the related model for the ForeignKey
                        related_model = model._meta.get_field(
                            field).related_model

                        # Fetch the related instance
                        try:
                            related_instance = related_model.objects.get(
                                pk=int(value))
                            # Replace the ID in the row with the related instance
                            row[field] = related_instance
                        except related_model.DoesNotExist:
                            # Handle the case where a related instance with the given ID doesn't exist
                            # This could involve setting the field to None, or skipping the row, or raising an error
                            # row[field] = None
                            pass

                    # elif field in field_types and (
                    #         field_types[field] == models.CharField or
                    #         field_types[field] == models.TextField or
                    #         field_types[field] == models.DateTimeField
                    # ) and not value.strip():
                    #     row[field] = None

                # Create the new record using the updated row data
                model.objects.create(**row)

            # for row in reader:
            #     model.objects.create(**row)

            return redirect('/base/import-csv')
    else:
        form = CSVImportForm()

    return render(request, 'admin/csv_import.html', {'form': form})


# ... other imports ...


def export_csv(request):
    if request.method == 'POST':
        form = CSVExportForm(request.POST)
        if form.is_valid():
            model_label = form.cleaned_data['model_choice']
            condition_field = form.cleaned_data['condition_field']
            model = apps.get_model(model_label)
            response = HttpResponse(content_type='text/csv')
            response[
                'Content-Disposition'] = f'attachment; filename="{model_label}_export.csv"'

            writer = csv.writer(response)
            headers = [field.name for field in model._meta.fields]
            writer.writerow(headers)

            # Add your condition fields here and modify the filter accordingly
            queryset = model.objects.filter()

            if condition_field:
                query = condition_field.split('&')
                for q in query:
                    field, value = q.split('=')
                    queryset = queryset.filter(**{field: value})
                # queryset = queryset.filter(**{})

            for obj in queryset:
                row = [str(getattr(obj, field)) for field in headers]
                writer.writerow(row)

            return response
    else:
        form = CSVExportForm()

    return render(request, 'admin/csv_export.html', {'form': form})
