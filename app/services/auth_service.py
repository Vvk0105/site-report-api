from app.core.security import verify_password


class AuthService:

    def __init__(self, repo):
        self.repo = repo

    async def login(self, email, password):

        user = await self.repo.get_by_email(email)

        if not user:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        return user