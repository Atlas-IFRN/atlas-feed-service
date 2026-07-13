# atlas-feed-service

Microsserviço de **feed**: postagens de usuários, comentários (1 nível de reply) e curtidas. Django + DRF, mesmo esqueleto dos demais serviços Atlas. Exposto sob `/api/feed/` com barreira JWT no gateway.

## Escopo (MVP)

- **Posts** — CRUD. Campos: `content` (texto), `media` (JSON `{src, alt, tone, caption}`, mídia **por URL**) e `embed_link` (JSON — link externo compartilhado OU embed de conteúdo interno). O post não pode ser totalmente vazio (precisa de texto, mídia ou embed/link).
- **Comentários** — em posts, com **replies de 1 nível** (estilo LinkedIn/Twitter).
- **Curtidas** — em posts e comentários, idempotentes (`UniqueConstraint(alvo, user_id)`).
- **Autor** — guardamos só `author_id` (UUID do auth-service). Nome/avatar/role/badge são resolvidos pelo frontend via auth-service (sem FK cross-schema).
- **Notificações** — ao curtir/comentar/responder, o feed **publica** o evento `notifications.create` na fila do notification-service (produtor-only, sem worker; best-effort). Não notifica o próprio autor da interação; curtida repetida não duplica evento. Tipos enviados (para o front mapear o ícone): `feed_like` (curtidas) e `feed_comment` (comentários/respostas). O enum completo do notification-service é `feed_like | feed_comment | track | scholarship | system`.

Contadores (`likes_count`, `comments_count`) e o flag `liked` do usuário atual são **derivados** por anotação no queryset (não há colunas denormalizadas).

## Endpoints (`/api/feed/`)

| Método | Rota | Descrição |
|---|---|---|
| GET/POST | `posts/` | Listar (paginado, `-created_at`, filtro `?author_id=`, busca `?search=`) / criar |
| GET/PATCH/DELETE | `posts/{id}/` | Detalhe / editar / apagar (apenas o autor) |
| POST/DELETE | `posts/{id}/like/` | Curtir / descurtir |
| GET/POST | `posts/{id}/comments/` | Listar comentários (com `replies`) / comentar (aceita `parent`) |
| POST/DELETE | `comments/{id}/like/` | Curtir / descurtir comentário |
| GET/PATCH/DELETE | `comments/{id}/` | Detalhe / editar / apagar (apenas o autor) |
| — | `health/`, `schema/`, `docs/`, `admin/` | Saúde, OpenAPI, Swagger, admin |

## Banco

Schema **`feed`** no Postgres compartilhado `atlas` (isolamento por `search_path`). Tabelas: `post`, `comment` (self-FK `parent`), `post_like`, `comment_like`.

## Rodar local

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # ajuste DATABASE_URL (ou deixe cair no SQLite de dev)
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Em Docker, o `entrypoint.sh` cria o schema `feed` e migra automaticamente no boot.
