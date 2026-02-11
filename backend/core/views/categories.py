# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from ..models import Category
from ..permissions import IsAdminRole


class CategoriesView(APIView):
    permission_classes = [IsAdminRole]
    
    def get(self, request):
        """Listar todas las categorías disponibles"""
        cats = Category.objects.all().order_by('name')
        data = [{"id": c.id, "name": c.name} for c in cats]
        return Response(data)
