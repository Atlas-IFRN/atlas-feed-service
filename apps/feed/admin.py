from django.contrib import admin

from .models import Comment, CommentLike, Post, PostLike


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author_id', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('id', 'author_id', 'content')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'author_id', 'parent', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('id', 'author_id', 'content')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user_id', 'created_at')
    search_fields = ('post__id', 'user_id')


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'comment', 'user_id', 'created_at')
    search_fields = ('comment__id', 'user_id')
