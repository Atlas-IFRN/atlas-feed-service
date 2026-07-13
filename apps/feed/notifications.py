"""
Publicação de notificações do feed (produtor de eventos).

Quando há interações (curtir/comentar/responder), o feed-service PUBLICA o
evento `notifications.create` na fila do RabbitMQ — sem HTTP e sem conhecer a
API/DB do notification-service, que é o dono do consumo. Mesmo padrão do
auth-service.

A publicação é best-effort: qualquer falha (broker fora, etc.) é apenas logada,
nunca propagada, para não interromper a interação do usuário. Cada evento leva
um `event_id` para idempotência no consumidor.

Obs.: o feed guarda apenas UUIDs (sem nomes), então as mensagens são genéricas.
O `type` é consumido pelo notification-service e usado pelo frontend para
escolher o ícone: `feed_like` (curtidas) e `feed_comment` (comentários/respostas).
"""
import logging
import uuid

from django.conf import settings

from config.celery import app as celery_app

logger = logging.getLogger(__name__)

# Tipos de notificação (devem existir no enum NotificationType do
# notification-service; o frontend mapeia cada um para um ícone).
TYPE_FEED_LIKE = "feed_like"
TYPE_FEED_COMMENT = "feed_comment"


def _publish(user_id, title, message, notification_type):
    """Publica o evento na fila (fire-and-forget)."""
    try:
        celery_app.send_task(
            "notifications.create",
            kwargs={
                "user_id": str(user_id),
                "title": title,
                "message": message,
                "type": notification_type,
                "event_id": str(uuid.uuid4()),
            },
            queue=settings.NOTIFICATIONS_QUEUE,
            retry=False,
        )
    except Exception:
        logger.exception("Falha ao publicar notificação de feed para %s", user_id)


def _notify(recipient_id, actor_id, title, message, notification_type):
    # Não notifica quando o autor da interação é o próprio destinatário
    # (ex.: curtir/comentar a própria publicação).
    if str(recipient_id) == str(actor_id):
        return
    _publish(recipient_id, title, message, notification_type)


def notify_post_liked(post, actor_id):
    _notify(post.author_id, actor_id, "Nova curtida", "Curtiram a sua publicação.", TYPE_FEED_LIKE)


def notify_post_commented(post, actor_id):
    _notify(post.author_id, actor_id, "Novo comentário", "Comentaram na sua publicação.", TYPE_FEED_COMMENT)


def notify_comment_replied(parent_comment, actor_id):
    _notify(parent_comment.author_id, actor_id, "Nova resposta", "Responderam ao seu comentário.", TYPE_FEED_COMMENT)


def notify_comment_liked(comment, actor_id):
    _notify(comment.author_id, actor_id, "Nova curtida", "Curtiram o seu comentário.", TYPE_FEED_LIKE)
