from rest_framework import permissions
from rest_framework import viewsets

from dpypen.items import models
from dpypen.items import serializers


class PenViewset(viewsets.ModelViewSet):
    queryset = models.Pen.objects.all()
    serializer_class = serializers.PenSerializer
    permission_classes = [permissions.IsAuthenticated]
