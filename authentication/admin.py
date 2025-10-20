# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import CustomUser
# from django.utils import timezone

# @admin.register(CustomUser)
# class CustomUserAdmin(UserAdmin):
#     list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_email_verified', 'last_activity', 'is_active', 'deleted_at')
#     list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_email_verified', 'deleted_at')
#     search_fields = ('username', 'email', 'first_name', 'last_name')
#     readonly_fields = ('last_activity', 'deleted_at', 'date_joined')
    
#     fieldsets = UserAdmin.fieldsets + (
#         ('Email Verification', {
#             'fields': ('is_email_verified', 'email_verification_token', 'email_verification_expires')
#         }),
#         ('Audit', {
#             'fields': ('last_login_ip', 'last_activity', 'deleted_at'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     actions = ['soft_delete_users', 'reactivate_users']
    
#     def soft_delete_users(self, request, queryset):
#         updated = queryset.update(is_active=False, deleted_at=timezone.now())
#         self.message_user(request, f'Soft deleted {updated} users.')
#     soft_delete_users.short_description = "Soft delete selected users"
    
#     def reactivate_users(self, request, queryset):
#         updated = queryset.update(is_active=True, deleted_at=None)
#         self.message_user(request, f'Reactivated {updated} users.')
#     reactivate_users.short_description = "Reactivate selected users"
    
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         if not request.user.is_superuser:
#             return qs.filter(deleted_at__isnull=True)
#         return qs

# authentication/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import CustomUser, Attorney


@admin.register(CustomUser)
class HiddenUserAdmin(DjangoUserAdmin):
    model = CustomUser
    # Needed so autocomplete can search:
    search_fields = ("email", "username", "first_name", "last_name")
    list_display = ("id", "email", "username", "is_staff", "is_superuser", "is_active")

    # Hide from the admin app index, but keep it registered for autocomplete
    def get_model_perms(self, request):
        return {}  # hides "Users" from the sidebar/app index


@admin.register(Attorney)
class AttorneyAdmin(DjangoUserAdmin):
    model = Attorney
    list_display = ("id", "email", "username", "first_name", "last_name",
                    "is_staff", "is_superuser", "is_email_verified", "is_active")
    list_filter  = ("is_email_verified", "is_active", "is_superuser")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("id",)

    fieldsets = (
        ("Login", {"fields": ("email", "password")}),
        ("Profile", {"fields": ("username", "first_name", "last_name")}),
        ("Status & Roles", {"fields": ("is_active", "is_superuser", "is_email_verified")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "last_activity")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2",
                       "first_name", "last_name",
                       "is_superuser", "is_active"),
        }),
    )
    readonly_fields = ("last_activity",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show active staff users as "Attorneys"
        return qs.filter(is_staff=True)

    def save_model(self, request, obj, form, change):
        # Ensure anyone added here is flagged as staff (attorney)
        obj.is_staff = True
        if not change:
            obj.is_email_verified = True
        super().save_model(request, obj, form, change)