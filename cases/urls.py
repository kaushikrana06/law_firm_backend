from django.contrib import admin
from django.urls import path, include
from .views import (
    ClientLookupView,
    AttorneyBootstrapView,
    CasePartialUpdateView,
    ClientCallRequestView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/auth/', include('authentication.urls', namespace='auth')),
    path("client/lookup", ClientLookupView.as_view(), name="client-lookup"),
    path("attorney/bootstrap", AttorneyBootstrapView.as_view(), name="attorney-bootstrap"),
    path("attorney/cases/<uuid:pk>", CasePartialUpdateView.as_view(), name="case-partial-update"),
    path("client-call-request/", ClientCallRequestView.as_view(), name="client-call-request"),
]
