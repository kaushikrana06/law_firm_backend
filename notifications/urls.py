# notifications/urls.py
from django.urls import path

from .views import AttorneyDeviceRegisterView, ClientDeviceRegisterView

urlpatterns = [
    path(
        "attorney/device/",
        AttorneyDeviceRegisterView.as_view(),
        name="attorney-device-register",
    ),
    path(
        "client/device/",
        ClientDeviceRegisterView.as_view(),
        name="client-device-register",
    ),
]
