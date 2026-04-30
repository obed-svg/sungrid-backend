from rest_framework.permissions import BasePermission

ROLE_RANK = {"viewer": 0, "operator": 1, "superadmin": 2}


class HasRole(BasePermission):
    required_role = "viewer"

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and ROLE_RANK.get(getattr(user, "role", ""), -1) >= ROLE_RANK[self.required_role]
        )


class IsViewer(HasRole):
    required_role = "viewer"


class IsOperator(HasRole):
    required_role = "operator"


class IsSuperAdmin(HasRole):
    required_role = "superadmin"

