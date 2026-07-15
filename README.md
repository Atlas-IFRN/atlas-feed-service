# Atlas · Feed Service 📣

> Parte do **Projeto Atlas** — plataforma acadêmica desenvolvida para o **IFRN Campus Pau dos Ferros** como Projeto Integrador de Sistemas Distribuídos. O Atlas conecta alunos a trilhas de conhecimento e bolsas, com avaliação automática de código por IA.

Microsserviço responsável pelo **feed institucional**: publicações, comentários, curtidas e banners. É o mural social da plataforma.

## O que este serviço faz

- **Posts:** publicações com autor e papel (`AuthorRole`), incluindo upload de imagens.
- **Interações:** comentários (`Comment`) e curtidas em posts e comentários (`PostLike`, `CommentLike`).
- **Banners:** banners tipados para destaques na interface (`Banner`, `BannerType`).
- **Notificações:** ao ocorrer interações (curtidas/comentários), **publica** o evento `notifications.create` no RabbitMQ (produtor apenas — não roda worker).
- **Auditoria:** modelo `AuditLog` com registro automático e endpoint de consulta.

## Stack

- Python · Django · Django REST Framework
- PostgreSQL 16 (schema `feed`) · Redis · RabbitMQ (Celery, apenas produtor)
- Armazenamento de mídia em `static/uploads`
- Gunicorn · Docker · drf-spectacular (Swagger)

## Como se encaixa no Atlas

| Repositório | Responsabilidade |
|---|---|
| atlas-auth-service | Identidade: SUAP OAuth2, JWT, perfis de usuário |
| atlas-track-service | Trilhas, módulos, conteúdos, progresso e submissão de desafios |
| atlas-scholarship-service | Bolsas, candidaturas, banco de talentos e notas |
| **atlas-feed-service** | **Feed institucional: posts, comentários, curtidas e banners** |
| atlas-notification-service | Notificações (consumidor central via RabbitMQ) |
| atlas-ai-service | Avaliação de repositórios GitHub por LLM local (Ollama) |
| atlas-frontend | SPA React + TypeScript (aluno e professor) |
| atlas-infra | Docker Compose, Nginx (gateway), Postgres/Redis/RabbitMQ, deploy e backup |
| atlas-observability | Prometheus + Grafana (métricas dos serviços) |

**Autenticação:** o Nginx valida o JWT na borda e injeta `X-User-Id` / `X-User-Role`; o serviço também valida o token localmente (SimpleJWT *stateless*). Dados de perfil vêm da API HTTP interna do auth-service — sem acesso direto a schema alheio.

## Domínio (models principais)

`Post` · `Banner` · `Comment` · `PostLike` · `CommentLike` · `AuditLog`

## Principais endpoints (`/api/feed/`)

Router DRF: `posts/` · `comments/` · `banners/` · `audit-logs/`. Documentação em `api/feed/docs/`.

## Estrutura

```
apps/feed/   models, views (ViewSets), serializers, services, tasks, audit
config/      settings (base/local/production), urls, celery, authentication
static/uploads/   mídia dos posts
```

## Executando localmente

> Orquestrado pelo repositório central: **[Atlas-IFRN/atlas-infra](https://github.com/Atlas-IFRN/atlas-infra)**.

```bash
git clone https://github.com/Atlas-IFRN/atlas-infra
cd atlas-infra && docker compose -f docker-compose.dev.yml up -d

cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

## Variáveis de ambiente

Baseie seu `.env` no `.env.example`. Principais: `DJANGO_SECRET_KEY` (compartilhada — valida o JWT), `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `AUTH_SERVICE_URL`.

## Observabilidade & Auditoria

- **Métricas:** `/metrics` (django-prometheus), coletado pelo [atlas-observability](https://github.com/Atlas-IFRN/atlas-observability).
- **Auditoria:** `AuditLog` registra operações com `user_id` e timestamp, consultáveis em `audit-logs/`.

## CI/CD

Workflows de GitHub Actions em `.github/workflows/`.
