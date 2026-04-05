import hmac

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.config import settings


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if hmac.compare_digest(username or "", settings.ADMIN_USERNAME) and hmac.compare_digest(password or "", settings.ADMIN_PASSWORD):
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("authenticated", False)
