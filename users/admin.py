from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

class ProfileInline(admin.StackedInline):
    model        = Profile
    can_delete   = False
    verbose_name = 'Profile'
    fields       = ('avatar',)

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display        = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_avatar')
    list_display_links  = ('username',)
    search_fields       = ('username', 'email', 'first_name', 'last_name')

    def get_avatar(self, obj):
        try:
            return '✓' if obj.profile.avatar else '–'
        except Profile.DoesNotExist:
            return '–'
    get_avatar.short_description = 'Avatar'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'avatar')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)