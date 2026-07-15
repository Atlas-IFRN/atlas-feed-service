from django.contrib import admin

from .models import AuditLog, Banner, Comment, CommentLike, Post, PostLike


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'table_name', 'action', 'record_id', 'user_id', 'created_at')
    list_filter = ('table_name', 'action', 'created_at')
    search_fields = ('record_id', 'user_id')
    readonly_fields = ('id', 'table_name', 'action', 'record_id', 'user_id', 'payload', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'type', 'is_active', 'order', 'created_by', 'created_at')
    list_filter = ('type', 'is_active')
    search_fields = ('id', 'title', 'created_by')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user_id', 'created_at')
    search_fields = ('post__id', 'user_id')


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'comment', 'user_id', 'created_at')
    search_fields = ('comment__id', 'user_id')
