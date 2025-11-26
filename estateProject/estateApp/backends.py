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
    def authenticate(self, request, username=None, password=None):
        try:
            # Find all users with this email (handles multi-role scenario)
            users = CustomUser.objects.filter(email=username)

            # Check which users have the correct password
            matching_users = []
            for user in users:
                if user.check_password(password):
                    matching_users.append(user)

            # If only one user matches, return that user
            if len(matching_users) == 1:
                return matching_users[0]

            # If multiple users match (multiple roles), return special object for role selection
            elif len(matching_users) > 1:
                # Verify they have distinct roles (should always be true due to constraints)
                roles = set(user.role for user in matching_users)
                if len(roles) > 1:
                    return MultipleUserMatch(matching_users)

            # No user with matching password found
            return None

        except Exception:
            return None

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
