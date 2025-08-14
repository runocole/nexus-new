import os
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_image_file_extension(value):
    """
    Validate that the uploaded file is an acceptable image format.
    """
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            _('Unsupported file extension. Allowed extensions are: %(allowed)s.'),
            params={'allowed': ', '.join(allowed_extensions)},
        )

def validate_file_size(value):
    """
    Validate that the file size doesn't exceed 5MB.
    """
    # 5MB in bytes
    max_size = 5 * 1024 * 1024
    
    if value.size > max_size:
        raise ValidationError(
            _('File size must not exceed 5MB.')
        )