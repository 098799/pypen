from django.urls import path

from dpypen.items import views


urlpatterns = [
    path('supen', views.supen, dict(rotation=0, order=2)),
    path('supen/<int:rotation>', views.supen, dict(order=2)),
    path('supen/<int:rotation>/<int:order>', views.supen),
    path('suink', views.suink, dict(rotation=1, order=2)),
    path('suink/<int:rotation>', views.suink, dict(order=2)),
    path('suink/<int:rotation>/<int:order>', views.suink),
]
