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