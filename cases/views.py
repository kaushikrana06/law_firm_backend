from django.utils import timezone
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Client, Case
from .serializers import (
    ClientPublicSerializer,
    AttorneyItemSerializer,
    CaseUpdateSerializer,
)

from rest_framework.permissions import BasePermission

class IsAttorneyCaseOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        # obj is a Case
        return getattr(obj.client, "attorney_id", None) == getattr(request.user, "id", None)



class ClientCodeThrottle(ScopedRateThrottle):
    scope = "client_code_lookup"

class ClientLookupView(APIView):
    
    permission_classes = [AllowAny]
    throttle_classes = [ClientCodeThrottle]

    def get(self, request):
        code = (request.query_params.get("code") or "").strip()
        if not code:
            return Response({"detail": "Missing 'code' query parameter."}, status=status.HTTP_400_BAD_REQUEST)
        return self._lookup(code)

    def post(self, request):
        code = (request.data.get("code") or "").strip()
        if not code:
            return Response({"detail": "Missing 'code' in request body."}, status=status.HTTP_400_BAD_REQUEST)
        return self._lookup(code)

    def _lookup(self, code: str):
        client = Client.objects.filter(code=code).first()
        if not client:
            # keep message generic; don't leak existence info
            return Response({"detail": "Client not found."}, status=status.HTTP_404_NOT_FOUND)
        data = ClientPublicSerializer(client).data
        return Response(data, status=status.HTTP_200_OK)



class AttorneyBootstrapView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 50))
            limit = max(1, min(limit, 500))
        except ValueError:
            return Response({"detail": "limit must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        qs = (
            Case.objects
            .select_related("client", "firm")
            .filter(client__attorney=request.user)
            .order_by("-last_update")
        )

        data = AttorneyItemSerializer(qs[:limit], many=True).data
        return Response(data, status=status.HTTP_200_OK)


class CasePartialUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsAttorneyCaseOwner]
    serializer_class = CaseUpdateSerializer
    queryset = Case.objects.select_related("client", "firm")
    http_method_names = ["patch", "options","post", "head"]
    def post(self, request, *args, **kwargs):
            return self.partial_update(request, *args, **kwargs)
    def perform_update(self, serializer):
        instance = serializer.save()
        instance.last_update = timezone.now()
        instance.save(update_fields=["last_update"])
