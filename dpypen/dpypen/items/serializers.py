from rest_framework.serializers import ModelSerializer

from dpypen.items import models


class PenSerializer(ModelSerializer):
    class Meta:
        model = models.Pen
        fields = "__all__"
