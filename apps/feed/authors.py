"""Resolução dos dados de exibição do autor (nome/foto) via auth-service.

O feed guarda só o `author_id`. Para devolver o cabeçalho do post já pronto
(nome + foto), resolvemos o perfil no auth-service por HTTP.

O CACHE persistente mora no auth (fonte da verdade), que invalida a entrada
quando o usuário muda. Aqui fazemos apenas **dedupe por request**: se o mesmo
autor aparece em vários posts/comentários da mesma resposta, o auth é chamado
uma vez só — sem guardar nada entre requests, então uma mudança de perfil já
aparece na requisição seguinte.

Tudo é *fail-soft*: se o auth estiver fora/lento, devolvemos o que der (nome/
foto vazios) e o cliente cai para as iniciais — o feed nunca quebra por isto.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Rótulos de exibição derivados do papel snapshot no post (não do perfil).
_ROLE_LABELS = {
    "SYSTEM": ("Sistema", "ATLAS"),
    "TEACHER": ("Docente", "Professor"),
    "STUDENT": ("Estudante", None),
}


def _fetch_profile(author_id, token):
    """Busca {name, image, role} no auth-service. Retorna None em qualquer falha."""
    url = f"{settings.AUTH_INTERNAL_URL}/api/auth/users/{author_id}/"
    # O auth valida ALLOWED_HOSTS pelo header Host; 'localhost' está sempre
    # liberado, então forçamos isso na chamada interna (o host real seria
    # 'auth-service', que não está em ALLOWED_HOSTS).
    headers = {"Authorization": token or "", "Host": "localhost"}
    try:
        resp = requests.get(url, headers=headers, timeout=settings.AUTH_REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.warning("Falha ao resolver autor %s: %s", author_id, exc)
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    return {
        "name": data.get("full_name") or data.get("first_name") or "",
        "image": data.get("image") or None,
        "role": (data.get("role") or "STUDENT"),
        # Matrícula é a chave usada na rota de perfil (/perfil/{matricula}).
        "matricula": data.get("registration_number") or None,
    }


def _request_memo(request):
    """Cache efêmero por request (evita resolver o mesmo autor N vezes)."""
    if request is None:
        return {}
    memo = getattr(request, "_feed_author_memo", None)
    if memo is None:
        memo = {}
        setattr(request, "_feed_author_memo", memo)
    return memo


def resolve_profile(author_id, request):
    """{name, image, role} do autor. Dedupe por request; frescor vem do auth."""
    memo = _request_memo(request)
    key = str(author_id)
    if key in memo:
        return memo[key]
    token = request.META.get("HTTP_AUTHORIZATION", "") if request is not None else ""
    profile = _fetch_profile(author_id, token)
    memo[key] = profile  # guarda até None p/ não refazer a chamada no mesmo request
    return profile


def _role_key(role):
    normalized = (role or "").upper()
    if normalized == "SYSTEM":
        return "SYSTEM"
    if normalized in ("TEACHER", "PROFESSOR"):
        return "TEACHER"
    return "STUDENT"


def build_author(author_id, request, author_role=None):
    """Objeto de autor pronto para o cliente: {id, name, image, role, badge}.

    Em posts, `author_role` é o snapshot gravado no post. Em comentários (sem
    snapshot), passa-se None e o papel é derivado do perfil vivo do auth.
    `name`/`image` sempre vêm do auth.
    """
    profile = resolve_profile(author_id, request) or {}
    key = _role_key(author_role or profile.get("role"))
    role_label, badge = _ROLE_LABELS[key]
    name = profile.get("name") or ("ATLAS" if key == "SYSTEM" else "Membro do ATLAS")
    return {
        "id": str(author_id),
        "matricula": profile.get("matricula"),
        "name": name,
        "image": profile.get("image"),
        "role": role_label,
        "badge": badge,
    }
