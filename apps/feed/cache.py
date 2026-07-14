"""Cache da listagem pública de banners do carrossel + invalidação.

A visão pública (só banners ativos) é idêntica para todos os usuários e muda
pouco — só quando um docente cria/edita/remove um banner. Guardamos a resposta
já serializada num cache local e a invalidamos em QUALQUER escrita no model
`Banner` (via signals). O TTL é só uma rede de segurança: o caminho normal de
atualização é a invalidação, não a expiração.

A visão de gestão (`?all=true`, que inclui inativos) NÃO é cacheada — o docente
precisa ver o efeito imediato das próprias edições no modal.
"""
from django.core.cache import cache

# Chave única: a lista pública não varia por usuário.
BANNERS_ACTIVE_CACHE_KEY = 'feed:banners:active'

# Rede de segurança caso alguma escrita escape dos signals (ex.: bulk update):
# mesmo assim o carrossel se atualiza sozinho depois desse tempo.
BANNERS_ACTIVE_CACHE_TTL = 60 * 5  # 5 minutos


def get_cached_active_banners():
    """Devolve a resposta cacheada (lista serializada) ou None em cache miss."""
    return cache.get(BANNERS_ACTIVE_CACHE_KEY)


def set_cached_active_banners(data):
    """Guarda a resposta já serializada da listagem pública de banners ativos."""
    cache.set(BANNERS_ACTIVE_CACHE_KEY, data, BANNERS_ACTIVE_CACHE_TTL)


def invalidate_active_banners_cache():
    """Descarta o cache da listagem pública. Chamada a cada escrita em Banner."""
    cache.delete(BANNERS_ACTIVE_CACHE_KEY)
