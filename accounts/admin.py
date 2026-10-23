from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Profile

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Verification & Role Info", {'fields': ('role', 'is_verified', 'verified_by', 'verified_at', 'verification_notes')}),
    )
    readonly_fields = ('verified_at',)
    list_display = ('username', 'email', 'role', 'is_verified', 'is_staff', 'is_active')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_active')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'certificates_earned')
    search_fields = ('user__username', 'skills')
