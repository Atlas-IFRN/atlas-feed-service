from rest_framework import serializers

from .models import Comment, Post


def _current_user_id(context):
    request = context.get('request') if context else None
    if request and request.user and request.user.is_authenticated:
        return request.user.id
    return None


class _CountsMixin(serializers.ModelSerializer):
    """
    Expõe `likes_count` e `liked` lendo primeiro os campos anotados no queryset
    (evita N+1 na listagem) e caindo para uma query pontual quando o objeto não
    foi anotado (ex.: resposta de create/update de um único registro).
    """

    likes_count = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()

    def get_likes_count(self, obj):
        annotated = getattr(obj, 'likes_count', None)
        if annotated is not None:
            return annotated
        return obj.likes.count()

    def get_liked(self, obj):
        annotated = getattr(obj, 'liked', None)
        if annotated is not None:
            return bool(annotated)
        user_id = _current_user_id(self.context)
        if user_id is None:
            return False
        return obj.likes.filter(user_id=user_id).exists()


class CommentReplySerializer(_CountsMixin):
    """Reply de 1 nível — nunca serializa `replies` (não há aninhamento além disso)."""

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'parent', 'author_id', 'content',
            'likes_count', 'liked', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'post', 'parent', 'author_id', 'created_at', 'updated_at']


class CommentSerializer(_CountsMixin):
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'parent', 'author_id', 'content',
            'likes_count', 'liked', 'replies', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'post', 'author_id', 'created_at', 'updated_at']

    def get_replies(self, obj):
        # Só comentários de topo carregam replies.
        if obj.parent_id is not None:
            return []
        replies = obj.replies.all()
        return CommentReplySerializer(replies, many=True, context=self.context).data

    def validate_parent(self, parent):
        if parent is None:
            return parent
        # Máximo 1 nível: não se responde a uma resposta.
        if parent.parent_id is not None:
            raise serializers.ValidationError(
                'Respostas aninhadas além de um nível não são permitidas.'
            )
        # O post do comentário é fixado pela rota (posts/{id}/comments/); a reply
        # precisa pertencer ao mesmo post do pai.
        post = self.context.get('post')
        if post is not None and parent.post_id != post.id:
            raise serializers.ValidationError(
                'A resposta deve pertencer ao mesmo post do comentário pai.'
            )
        return parent


class PostSerializer(_CountsMixin):
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author_id', 'content', 'media', 'embed_link',
            'likes_count', 'comments_count', 'liked',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'author_id', 'created_at', 'updated_at']

    def get_comments_count(self, obj):
        annotated = getattr(obj, 'comments_count', None)
        if annotated is not None:
            return annotated
        return obj.comments.count()

    def validate(self, attrs):
        # Um post não pode ser vazio. Em PATCH parcial, mescla com a instância.
        instance = getattr(self, 'instance', None)

        def resolve(field):
            if field in attrs:
                return attrs[field]
            return getattr(instance, field, None)

        content = resolve('content')
        media = resolve('media')
        embed_link = resolve('embed_link')

        if not (content or '').strip() and not media and not embed_link:
            raise serializers.ValidationError(
                'Um post precisa de texto, mídia ou um embed/link.'
            )
        return attrs
