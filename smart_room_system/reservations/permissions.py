from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (getattr(request.user, 'role', '') == 'admin' or request.user.is_staff or request.user.is_superuser)
        )

class IsStaffOrAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (getattr(request.user, 'role', '') in ['admin', 'staff'] or request.user.is_staff or request.user.is_superuser)
        )

class IsOwnerOrAdminOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'role', '') in ['admin', 'staff'] or request.user.is_staff or request.user.is_superuser:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False
