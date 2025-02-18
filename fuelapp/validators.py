import os

from django.core.exceptions import ValidationError
from django.db.models import FileField, ImageField
from django.forms import forms
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _

IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
DOCUMENT_TYPES = ['.pdf', '.doc', '.docx']
VIDEO_TYPES = ['.mp4']


def validate_file_extension(value, valid_extensions=[]):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    if ext.lower() not in valid_extensions:
        raise ValidationError('Unsupported file extension.')


def validate_document(value):
    allowed_types = DOCUMENT_TYPES
    validate_file_extension(value, allowed_types)


def validate_video(value):
    allowed_types = VIDEO_TYPES
    validate_file_extension(value, allowed_types)


def validate_images(value):
    allowed_types = IMAGE_TYPES
    validate_file_extension(value, allowed_types)


def validate_materials(value):
    allowed_types = IMAGE_TYPES + DOCUMENT_TYPES
    validate_file_extension(value, allowed_types)


def validate_file_size(value):
    limit = 2 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('File too large. Size should not exceed 2 MiB.')


class RestrictedFileField(FileField):
    """
    Same as FileField, but you can specify:
        * max_upload_size - a number indicating the maximum
        file size allowed for upload.
            2.5MB - 2621440
            5MB - 5242880
            10MB - 10485760
            20MB - 20971520
            50MB - 5242880
            100MB - 104857600
            250MB - 214958080
            500MB - 429916160
    """

    def __init__(self, *args, **kwargs):

        self.max_upload_size = kwargs.pop("max_upload_size", 0)

        super(RestrictedFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(RestrictedFileField,
                     self).clean(*args, **kwargs)

        file = data.file
        try:
            if file._size > self.max_upload_size:
                raise forms.ValidationError(
                    _('Please keep filesize under %s. Current filesize %s') % (
                        filesizeformat(self.max_upload_size),
                        filesizeformat(file._size)))
        except AttributeError:
            pass

        return data


class RestrictedImageField(ImageField):
    """
    Same as ImageField, but you can specify:
        * max_upload_size - a number indicating the maximum file size
        allowed for upload.
            2.5MB - 2621440
            3MB - 3145728
            5MB - 5242880
            10MB - 10485760
            20MB - 20971520
            50MB - 5242880
            100MB - 104857600
            250MB - 214958080
            500MB - 429916160
    """

    def __init__(self, *args, **kwargs):

        self.max_upload_size = kwargs.pop("max_upload_size", 0)

        super(RestrictedImageField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(RestrictedImageField,
                     self).clean(*args, **kwargs)

        file = data.file
        try:
            if file._size > self.max_upload_size:
                raise forms.ValidationError(
                    _('Please keep filesize under %s. Current filesize %s') % (
                        filesizeformat(self.max_upload_size),
                        filesizeformat(file._size)))
        except AttributeError:
            pass

        return data
