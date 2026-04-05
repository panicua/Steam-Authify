from fastapi import FastAPI
from sqladmin import Admin, ModelView
from starlette.middleware.sessions import SessionMiddleware

from app.admin.auth import AdminAuth
from app.config import settings
from app.database import engine
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.steam_account import SteamAccount
from app.models.user import User


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.telegram_id, User.role, User.is_active, User.created_at]
    column_searchable_list = [User.username]
    column_sortable_list = [User.id, User.username, User.created_at]
    form_excluded_columns = [User.steam_accounts]
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"


class SteamAccountAdmin(ModelView, model=SteamAccount):
    column_list = [SteamAccount.id, SteamAccount.account_name, SteamAccount.user, SteamAccount.steam_id, SteamAccount.created_at]
    column_searchable_list = [SteamAccount.account_name]
    column_sortable_list = [SteamAccount.id, SteamAccount.account_name, SteamAccount.created_at]
    form_excluded_columns = [
        SteamAccount.shared_secret_encrypted,
        SteamAccount.identity_secret_encrypted,
        SteamAccount.revocation_code_encrypted,
    ]
    column_details_exclude_list = [
        SteamAccount.shared_secret_encrypted,
        SteamAccount.identity_secret_encrypted,
        SteamAccount.revocation_code_encrypted,
    ]
    name = "Steam Account"
    name_plural = "Steam Accounts"
    icon = "fa-solid fa-shield-halved"


class ApiKeyAdmin(ModelView, model=ApiKey):
    column_list = [ApiKey.id, ApiKey.label, ApiKey.key_prefix, ApiKey.is_active, ApiKey.created_at]
    column_details_exclude_list = [ApiKey.key_hash]
    form_excluded_columns = [ApiKey.key_hash, ApiKey.key_prefix]
    can_create = False
    name = "API Key"
    name_plural = "API Keys"
    icon = "fa-solid fa-key"


class AuditLogAdmin(ModelView, model=AuditLog):
    column_list = [AuditLog.id, AuditLog.actor_type, AuditLog.actor_id, AuditLog.entity_type, AuditLog.action, AuditLog.created_at]
    column_sortable_list = [AuditLog.id, AuditLog.created_at]
    can_create = False
    can_edit = False
    can_delete = False
    name = "Audit Log"
    name_plural = "Audit Logs"
    icon = "fa-solid fa-clipboard-list"


def setup_admin(app: FastAPI) -> Admin:
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    auth_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        engine,
        authentication_backend=auth_backend,
        title="Steam Auth Admin",
    )

    admin.add_view(UserAdmin)
    admin.add_view(SteamAccountAdmin)
    admin.add_view(ApiKeyAdmin)
    admin.add_view(AuditLogAdmin)

    return admin
