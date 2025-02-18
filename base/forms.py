from django import forms
from django.apps import apps


class CSVImportForm(forms.Form):
    # model_choice = forms.ChoiceField(
    #     choices=[(model._meta.label, model._meta.verbose_name_plural) for model
    #              in apps.get_models()])
    all_models = [(model._meta.label, model._meta.verbose_name_plural) for
                  app_config in apps.get_app_configs() for model in
                  app_config.get_models()]
    model_choice = forms.ChoiceField(choices=all_models)
    csv_file = forms.FileField()


class CSVExportForm(forms.Form):
    all_models = [(model._meta.label, model._meta.verbose_name_plural) for
                  app_config in apps.get_app_configs() for model in
                  app_config.get_models()]
    model_choice = forms.ChoiceField(choices=all_models)
    condition_field = forms.CharField(
        label='Condition Field',
        required=False,
        help_text='Enter the name of the field to filter on',
    )
    # Add any condition fields you need
