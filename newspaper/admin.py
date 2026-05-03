from django.contrib import admin
from django.utils.html import format_html
from .models import Article, Category, Tag, Author, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'colored_dot', 'description')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def colored_dot(self, obj):
        return format_html(
            '<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
            'background:{};vertical-align:middle"></span>', obj.color
        )
    colored_dot.short_description = 'Color'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'twitter_handle')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('name', 'email', 'content', 'created_at')
    fields = ('name', 'email', 'content', 'approved', 'created_at')
    show_change_link = True


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'author', 'status', 'is_breaking',
        'views', 'published_at',
    )
    list_filter = ('status', 'is_breaking', 'category')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    filter_horizontal = ('tags',)
    readonly_fields = ('views', 'created_at', 'updated_at')
    date_hierarchy = 'published_at'
    ordering = ('-published_at',)
    list_editable = ('status', 'is_breaking')
    inlines = [CommentInline]

    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'image_url'),
        }),
        ('Taxonomy', {
            'fields': ('category', 'author', 'tags'),
        }),
        ('Publishing', {
            'fields': ('status', 'is_breaking', 'published_at'),
        }),
        ('Stats', {
            'fields': ('views', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_published', 'mark_featured', 'mark_breaking', 'unmark_breaking']

    @admin.action(description='Mark selected as Published')
    def mark_published(self, request, queryset):
        queryset.update(status='published')

    @admin.action(description='Mark selected as Featured')
    def mark_featured(self, request, queryset):
        queryset.update(status='featured')

    @admin.action(description='Set Breaking News flag')
    def mark_breaking(self, request, queryset):
        queryset.update(is_breaking=True)

    @admin.action(description='Remove Breaking News flag')
    def unmark_breaking(self, request, queryset):
        queryset.update(is_breaking=False)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'article', 'approved', 'created_at')
    list_filter = ('approved',)
    search_fields = ('name', 'email', 'content')
    list_editable = ('approved',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    actions = ['approve_comments']

    @admin.action(description='Approve selected comments')
    def approve_comments(self, request, queryset):
        queryset.update(approved=True)