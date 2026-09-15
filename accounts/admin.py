from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile, ContactMessage

admin.site.register(User, UserAdmin)
admin.site.register(Profile)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role", "created_at", "is_resolved")
    list_filter = ("role", "is_resolved", "created_at")
    search_fields = ("name", "email", "message")
