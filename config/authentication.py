"""
Autenticação stateless via JWT no cabeçalho Authorization.

O token é assinado pelo auth-service e validado localmente (mesma SIGNING_KEY,
compartilhada via DJANGO_SECRET_KEY no .env) — sem nenhuma chamada de rede ao
auth. Os claims `role`/`email` viajam dentro do próprio token.

Usa o fluxo tradicional do DRF: popula `request.user` com um usuário derivado
do token, de modo que `request.user.is_authenticated` e `request.user.role`
funcionam nas views e permissions.
"""
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.models import TokenUser


class AtlasTokenUser(TokenUser):
    """TokenUser estendido para expor os claims usados pela aplicação."""

    @property
    def user_id(self):
        return str(self.id)

    @property
    def role(self):
        return self.token.get("role", "")

    @property
    def email(self):
        return self.token.get("email", "")


class AtlasJWTAuthentication(JWTStatelessUserAuthentication):
    """Autenticação JWT stateless — não consulta banco nem o auth-service."""
