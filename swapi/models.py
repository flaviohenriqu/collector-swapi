import uuid

from django.conf import settings
from django.db import models


class Collection(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=settings.COLLECTIONS_BASE)
    created_at = models.DateTimeField(auto_now_add=True)
