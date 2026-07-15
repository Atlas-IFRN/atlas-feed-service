import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuthorRole(models.TextChoices):
    """Papel do autor no momento da publicação — snapshot vindo do JWT.

    Guardado no próprio post (denormalizado) para permitir filtrar o feed por
    origem (docentes, sistema) sem consultar o auth-service a cada listagem.
    """

    STUDENT = 'STUDENT', 'Estudante'
    TEACHER = 'TEACHER', 'Professor'
    SYSTEM = 'SYSTEM', 'Sistema'


def post_image_upload_to(instance, filename):
    # Salvo dentro de MEDIA_ROOT (que fica sob o diretório `static/` do serviço,
    # servido pela rota /api/feed/static/). Namespaced por post para evitar
    # colisão de nomes.
    return f"posts/{instance.id}/{filename}"


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # O usuário vive no schema do auth-service; aqui guardamos apenas o UUID
    # (sem FK entre schemas/serviços). Os dados de exibição do autor
    # (nome/role/avatar/badge) são resolvidos via auth-service pelo frontend.
    author_id = models.UUIDField(db_index=True)

    # Papel do autor no momento da publicação (snapshot do claim `role`/`is_staff`
    # do token). Permite filtrar o feed por "docentes"/"sistema" no servidor.
    author_role = models.CharField(
        max_length=10,
        choices=AuthorRole.choices,
        default=AuthorRole.STUDENT,
        db_index=True,
    )

    # Post fixado por um docente — sobe para o topo do feed "principal".
    # Só professores/staff podem alternar (regra aplicada na view).
    is_fixed = models.BooleanField(default=False, db_index=True)

    # Texto do post (suporta #hashtags/@menções — o parse fica no cliente).
    content = models.TextField(blank=True)

    # Imagem anexada, salva no armazenamento do serviço (sob static/uploads).
    # Opcional: um post pode ter só texto, só link, etc.
    image = models.ImageField(upload_to=post_image_upload_to, null=True, blank=True)

    # Metadados da mídia (alt/tom/legenda): {alt, tone, caption}. Quando há
    # `image`, o cliente monta `src` a partir da URL da imagem; este bloco
    # complementa com texto alternativo e legenda. Também aceita `src` externo.
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
        # imagem, mídia ou um embed/link.
        has_media = bool(self.image) or bool(self.media)
        if not (self.content or '').strip() and not has_media and not self.embed_link:
            raise ValidationError(_('Um post precisa de texto, imagem, mídia ou um embed/link.'))

    def __str__(self):
        return f"Post({self.id}) by {self.author_id}"


class BannerType(models.TextChoices):
    """Origem/categoria do banner — define o tema visual no front."""

    COMUNICADO_IFRN = 'COMUNICADO_IFRN', 'Comunicado IFRN'
    SISTEMA = 'SISTEMA', 'Sistema'


class Banner(models.Model):
    """Banner de destaque no topo do feed (carrossel), gerenciado por docentes.

    O primeiro slide do carrossel (boas-vindas) é estático e vive só no
    front; este model cobre os demais banners (comunicados, avisos etc.),
    que podem ser criados/editados/removidos por professores via API.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    type = models.CharField(max_length=20, choices=BannerType.choices)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    primary_button_text = models.CharField(max_length=60, blank=True)
    primary_button_link = models.CharField(max_length=300, blank=True)
    secondary_button_text = models.CharField(max_length=60, blank=True)
    secondary_button_link = models.CharField(max_length=300, blank=True)

    # Permite ocultar sem apagar (histórico) e controlar a ordem no carrossel.
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    # Professor (ou staff/admin) que criou o banner — snapshot do id do token,
    # sem FK entre schemas/serviços (mesmo padrão de `Post.author_id`).
    created_by = models.UUIDField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return f"Banner({self.id}) {self.title}"


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


class AuditAction(models.TextChoices):
    CREATE = 'CREATE', _('Create')
    UPDATE = 'UPDATE', _('Update')
    DELETE = 'DELETE', _('Delete')


class AuditLogTable(models.TextChoices):
    POST = 'post', _('Post')
    BANNER = 'banner', _('Banner')
    COMMENT = 'comment', _('Comment')
    POST_LIKE = 'post_like', _('Post Like')
    COMMENT_LIKE = 'comment_like', _('Comment Like')


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_name = models.CharField(max_length=100, choices=AuditLogTable.choices)
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    record_id = models.UUIDField(help_text='PK do registro afetado')
    user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text='UUID do usuário responsável pela operação',
    )
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['user_id', '-created_at'], name='feed_audit_user_time_idx'),
            models.Index(fields=['-created_at'], name='feed_audit_created_idx'),
        ]

    def __str__(self):
        return f'[{self.action}] {self.table_name} ({self.record_id})'
