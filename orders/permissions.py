from rest_framework import permissions

class IsClientOrReadOnly(permissions.BasePermission):
    """
    Faqat client o'z orderlarini yaratishi mumkin.
    """
    def has_permission(self, request, view):
        if request.method == 'POST':
            return request.user and request.user.is_authenticated
        return True
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.client == request.user

class IsManagerOrAdmin(permissions.BasePermission):
    """
    Faqat manager yoki admin orderlarni qabul qilishi mumkin.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'manager' or request.user.role == 'admin'

class IsAdminUser(permissions.BasePermission):
    """
    Faqat admin uchun
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'