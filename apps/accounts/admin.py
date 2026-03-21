from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.action(description='Mark selected accounts as Test')
def mark_as_test_account(modeladmin, request, queryset):
	updated = queryset.update(is_test_account=True)
	modeladmin.message_user(request, f'{updated} account(s) marked as test data.')


@admin.action(description='Mark selected accounts as Real')
def mark_as_real_account(modeladmin, request, queryset):
	updated = queryset.update(is_test_account=False)
	modeladmin.message_user(request, f'{updated} account(s) marked as real data.')


@admin.register(User)
class ClairbookUserAdmin(UserAdmin):
	list_display = ('username', 'email', 'role', 'is_test_account', 'is_staff', 'is_active')
	list_filter = ('role', 'is_test_account', 'is_staff', 'is_active')
	fieldsets = UserAdmin.fieldsets + (
		('clairbook', {'fields': ('role', 'display_name', 'is_test_account')}),
	)
	add_fieldsets = UserAdmin.add_fieldsets + (
		('clairbook', {'fields': ('email', 'display_name', 'role', 'is_test_account')}),
	)
	actions = (mark_as_test_account, mark_as_real_account)
