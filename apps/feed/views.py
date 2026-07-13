from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch
from rest_framework import filters, mixins, pagination, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Comment, CommentLike, Post, PostLike
from .notifications import (
    notify_comment_liked,
    notify_comment_replied,
    notify_post_commented,
    notify_post_liked,
)
from .permissions import IsAuthorOrReadOnly
from .serializers import CommentSerializer, PostSerializer


def annotate_comments(queryset, user_id):
    """Anota `likes_count` e `liked` (para o usuário atual) num queryset de comentários."""
    return queryset.annotate(
        likes_count=Count('likes', distinct=True),
        liked=Exists(CommentLike.objects.filter(comment=OuterRef('pk'), user_id=user_id)),
    )


class FeedPagination(pagination.PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class PostViewSet(viewsets.ModelViewSet):
    """
    CRUD de postagens do feed + ações de curtir e comentar.

    - list/retrieve: qualquer autenticado.
    - create: autor = usuário do token.
    - update/destroy: apenas o autor do post (IsAuthorOrReadOnly).
    - like (POST/DELETE), comments (GET/POST): qualquer autenticado.
    """

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
    pagination_class = FeedPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['content']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user_id = self.request.user.id
        queryset = Post.objects.annotate(
            likes_count=Count('likes', distinct=True),
            comments_count=Count('comments', distinct=True),
            liked=Exists(PostLike.objects.filter(post=OuterRef('pk'), user_id=user_id)),
        )
        author_id = self.request.query_params.get('author_id')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(author_id=self.request.user.id)

    def _serialized_post(self, pk):
        """Recarrega o post já anotado para devolver contadores atualizados."""
        post = self.get_queryset().get(pk=pk)
        return PostSerializer(post, context=self.get_serializer_context()).data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        data = self._serialized_post(serializer.instance.pk)
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post', 'delete'])
    def like(self, request, pk=None):
        post = self.get_object()
        if request.method == 'POST':
            # Idempotente: o UniqueConstraint (post, user_id) garante 1 like.
            _, created = PostLike.objects.get_or_create(post=post, user_id=request.user.id)
            if created:
                # Notifica só numa curtida nova (não a cada clique repetido).
                transaction.on_commit(lambda: notify_post_liked(post, request.user.id))
        else:
            PostLike.objects.filter(post=post, user_id=request.user.id).delete()
        return Response(self._serialized_post(post.pk), status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        post = self.get_object()
        user_id = request.user.id

        if request.method == 'POST':
            serializer = CommentSerializer(
                data=request.data,
                context={'request': request, 'post': post},
            )
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(post=post, author_id=user_id)
            # Reply notifica o autor do comentário pai; comentário de topo
            # notifica o autor do post.
            if comment.parent_id:
                transaction.on_commit(lambda: notify_comment_replied(comment.parent, user_id))
            else:
                transaction.on_commit(lambda: notify_post_commented(post, user_id))
            out = annotate_comments(Comment.objects.filter(pk=comment.pk), user_id).first()
            return Response(
                CommentSerializer(out, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )

        # GET — comentários de topo com replies aninhados (ambos anotados).
        replies_qs = annotate_comments(Comment.objects.all(), user_id).order_by('created_at')
        top_level = (
            annotate_comments(post.comments.filter(parent__isnull=True), user_id)
            .order_by('created_at')
            .prefetch_related(Prefetch('replies', queryset=replies_qs))
        )
        page = self.paginate_queryset(top_level)
        serializer = CommentSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class CommentViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Recupera/edita/apaga um comentário e permite curtir/descurtir.

    A CRIAÇÃO de comentários é feita pela rota aninhada
    `posts/{id}/comments/` (o post é fixado pela URL).
    """

    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]

    def get_queryset(self):
        return annotate_comments(Comment.objects.all(), self.request.user.id)

    def _serialized_comment(self, pk):
        comment = self.get_queryset().get(pk=pk)
        return CommentSerializer(comment, context=self.get_serializer_context()).data

    @action(detail=True, methods=['post', 'delete'])
    def like(self, request, pk=None):
        comment = self.get_object()
        if request.method == 'POST':
            _, created = CommentLike.objects.get_or_create(comment=comment, user_id=request.user.id)
            if created:
                transaction.on_commit(lambda: notify_comment_liked(comment, request.user.id))
        else:
            CommentLike.objects.filter(comment=comment, user_id=request.user.id).delete()
        return Response(self._serialized_comment(comment.pk), status=status.HTTP_200_OK)
