from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch
from rest_framework import filters, mixins, pagination, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .authors import actor_display_name, resolve_user_id
from .models import AuthorRole, Banner, Comment, CommentLike, Post, PostLike
from .notifications import (
    notify_comment_liked,
    notify_comment_replied,
    notify_post_commented,
    notify_post_liked,
)
from .permissions import IsAuthorOrReadOnly, IsTeacherOrReadOnly, is_teacher
from .serializers import BannerSerializer, CommentSerializer, PostSerializer


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
    # A ordenação é resolvida em get_queryset (param `sort` + fixados no topo);
    # não usamos OrderingFilter porque ele sobrescreveria esse order_by.
    filter_backends = [filters.SearchFilter]
    search_fields = ['content']

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

        # Filtro por origem do post (feed "docentes" / "sistema").
        author_role = self.request.query_params.get('author_role')
        if author_role:
            queryset = queryset.filter(author_role=author_role.upper())

        # Ordenação:
        #   - sort=likes  → "mais curtidos" (mais likes primeiro).
        #   - padrão      → "principal": posts fixados no topo, depois recentes.
        sort = self.request.query_params.get('sort')
        if sort == 'likes':
            queryset = queryset.order_by('-likes_count', '-created_at')
        else:
            queryset = queryset.order_by('-is_fixed', '-created_at')
        return queryset

    def _resolve_author_role(self):
        """Deriva o papel do autor a partir dos claims do token.

        Staff/admin publica em nome do sistema (ATLAS); professores e alunos
        publicam com seu próprio papel. É um snapshot: mudanças posteriores no
        auth-service não reescrevem posts já publicados.
        """
        user = self.request.user
        if getattr(user, 'is_staff', False):
            return AuthorRole.SYSTEM
        if (getattr(user, 'role', '') or '').upper() == AuthorRole.TEACHER:
            return AuthorRole.TEACHER
        return AuthorRole.STUDENT

    def perform_create(self, serializer):
        serializer.save(
            author_id=self.request.user.id,
            author_role=self._resolve_author_role(),
        )

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

    @action(detail=False, methods=['get'], url_path=r'by-user/(?P<matricula>[^/]+)')
    def by_user(self, request, matricula=None):
        """Lista os posts de um usuário específico, resolvido pela matrícula.

        Mesmo formato/paginação/ordenação da listagem do feed (home) — reusa
        `get_queryset` e o `PostSerializer`. A matrícula é resolvida para o UUID
        do autor no auth-service; responde 404 se o usuário não existir.
        Aceita os mesmos params opcionais da listagem (ex.: `sort=likes`, `page`).
        """
        author_id = resolve_user_id(matricula, request)
        if not author_id:
            return Response(
                {'detail': 'Usuário não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        queryset = self.filter_queryset(self.get_queryset()).filter(author_id=author_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'])
    def fix(self, request, pk=None):
        """Fixa (POST) ou desafixa (DELETE) um post. Exclusivo de docentes."""
        if not is_teacher(request.user):
            return Response(
                {'detail': 'Apenas docentes podem fixar publicações.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        post = self.get_object()
        post.is_fixed = request.method == 'POST'
        post.save(update_fields=['is_fixed', 'updated_at'])
        return Response(self._serialized_post(post.pk), status=status.HTTP_200_OK)

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
            # notifica o autor do post. Resolve o nome do ator aqui (com a
            # request disponível) para a mensagem "Fulano comentou…".
            actor_name = actor_display_name(request)
            content = comment.content
            if comment.parent_id:
                parent = comment.parent
                transaction.on_commit(
                    lambda: notify_comment_replied(parent, user_id, actor_name, content)
                )
            else:
                transaction.on_commit(
                    lambda: notify_post_commented(post, user_id, actor_name, content)
                )
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


class BannerViewSet(viewsets.ModelViewSet):
    """
    CRUD de banners do carrossel do feed.

    - list/retrieve: qualquer autenticado vê os banners ativos, ordenados.
      Docentes/staff podem passar `?all=true` para ver também os inativos
      (usado pelo modal de gestão).
    - create/update/destroy: exclusivo de docentes/staff (IsTeacherOrReadOnly).
    """

    serializer_class = BannerSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        queryset = Banner.objects.all()
        # O filtro de "só ativos" vale para a listagem pública do carrossel.
        # Ações de detalhe (retrieve/update/destroy) sempre enxergam qualquer
        # banner — senão um professor não conseguiria reativar/editar/excluir
        # um banner que ele mesmo desativou.
        if self.action != 'list':
            return queryset
        show_all = self.request.query_params.get('all') == 'true'
        if not (show_all and is_teacher(self.request.user)):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)


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
