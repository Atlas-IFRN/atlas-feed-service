import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # O usuário vive no schema do auth-service; aqui guardamos apenas o UUID
    # (sem FK entre schemas/serviços). Os dados de exibição do autor
    # (nome/role/avatar/badge) são resolvidos via auth-service pelo frontend.
    author_id = models.UUIDField(db_index=True)

    # Texto do post (suporta #hashtags/@menções — o parse fica no cliente).
    content = models.TextField(blank=True)

    # Mídia por URL (sem upload gerenciado): {src, alt, tone, caption}.
    media = models.JSONField(null=True, blank=True)

    # Link externo compartilhado OU embed de conteúdo interno (trilha/módulo/
    # desafio). Bloco livre em JSON; o cliente decide como renderizar a partir
    # do que estiver presente (ex.: `url` p/ link externo, `title`/`meta` p/ embed).
    embed_link = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]

    def clean(self):
        # Um post não pode ser completamente vazio: precisa de ao menos texto,
        # mídia ou um embed/link.
        if not (self.content or '').strip() and not self.media and not self.embed_link:
            raise ValidationError(_('Um post precisa de texto, mídia ou um embed/link.'))

    def __str__(self):
        return f"Post({self.id}) by {self.author_id}"


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    # Reply de no máximo 1 nível (estilo LinkedIn/Twitter). `parent` nulo = comentário de topo.
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
    )
    author_id = models.UUIDField(db_index=True)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def clean(self):
        if not (self.content or '').strip():
            raise ValidationError({'content': _('O comentário não pode ser vazio.')})
        if self.parent_id:
            # Máximo 1 nível: o pai não pode ser, ele próprio, uma reply.
            if self.parent.parent_id is not None:
                raise ValidationError(
                    {'parent': _('Respostas aninhadas além de um nível não são permitidas.')}
                )
            # A reply precisa pertencer ao mesmo post do comentário pai.
            if self.parent.post_id != self.post_id:
                raise ValidationError(
                    {'parent': _('A resposta deve pertencer ao mesmo post do comentário pai.')}
                )

    def __str__(self):
        return f"Comment({self.id}) by {self.author_id}"


class PostLike(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user_id'], name='unique_post_like'),
        ]

    def __str__(self):
        return f"PostLike(post={self.post_id}, user={self.user_id})"


class CommentLike(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['comment', 'user_id'], name='unique_comment_like'),
        ]

    def __str__(self):
        return f"CommentLike(comment={self.comment_id}, user={self.user_id})"
