from rest_framework import permissions

class IsManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        is_authenticated = request.user.is_authenticated
        has_role = hasattr(request.user, 'role') and (request.user.role == "admin" or request.user.role == "manager")
        print(f"User authenticated: {is_authenticated}, Has correct role: {has_role}")
        return is_authenticated and has_role