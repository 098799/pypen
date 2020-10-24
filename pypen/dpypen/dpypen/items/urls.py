from django.conf.urls import include, url
from rest_framework import routers

from dpypen.items import views


router = routers.DefaultRouter()
router.register(r'pens', views.PenViewset)


urlpatterns = [
    url('', include(router.urls)),
]
