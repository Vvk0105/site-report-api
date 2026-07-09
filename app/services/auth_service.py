from app.core.security import (
    verify_password,
    create_access_token,
)


class AuthService:

    def __init__(self, repo):

        self.repo = repo

    async def admin_login(
        self,
        email: str,
        password: str,
    ):

        user = await self.repo.get_by_email(email)

        if not user:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "is_admin": user.is_admin,
            }
        )

        return token