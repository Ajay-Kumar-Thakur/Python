from rest_framework import serializers
from .models import Article, Category, Tag, Author, Comment


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'color', 'description']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class AuthorSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'full_name', 'bio', 'avatar_url', 'twitter_handle']

    def get_full_name(self, obj):
        return str(obj)


class ArticleSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    author = AuthorSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content',
            'image_url', 'category', 'author', 'tags',
            'status', 'is_breaking', 'views',
            'published_at', 'created_at', 'url',
        ]

    def get_url(self, obj):
        return obj.get_absolute_url()


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'name', 'content', 'created_at']