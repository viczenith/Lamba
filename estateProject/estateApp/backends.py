from estateApp.models import CustomUser


class MultipleUserMatch:
    """
    Special object returned by EmailBackend when multiple users with the same email
    have the correct password. Contains the list of matching users for role selection.
    """
    def __init__(self, users):
        self.users = users
        self.email = users[0].email if users else None

    def __str__(self):
        return f"Multiple users found for email {self.email}"


class EmailBackend:
    def authenticate(self, request, username=None, password=None, email=None, company=None, **kwargs):
        """Authenticate by email address.

        Supports both `username` and `email` credential keys (to work with
        Django forms + DRF token auth), and supports optional `company` for
        tenant-scoped authentication.
        """
        try:
            identifier = username or email
            if not identifier or not password:
                return None

            # Find all users with this email (handles multi-role scenario)
            users = CustomUser.objects.filter(email=identifier)

            # Optional tenant scoping
            if company is not None:
                users = users.filter(company_profile=company)

            # Check which users have the correct password
            matching_users = [u for u in users if u.check_password(password)]

            # If only one user matches, return that user
            if len(matching_users) == 1:
                return matching_users[0]

            # If multiple users match (multiple roles), return special object for role selection
            if len(matching_users) > 1:
                roles = {u.role for u in matching_users}
                if len(roles) > 1:
                    return MultipleUserMatch(matching_users)

                # Same-role duplicates are unexpected; fall back to first match.
                return matching_users[0]

            # No user with matching password found
            return None

        except Exception:
            return None

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
