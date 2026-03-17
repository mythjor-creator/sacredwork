from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SacredWorkUserAdmin(UserAdmin):
	list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
	list_filter = ('role', 'is_staff', 'is_active')
	fieldsets = UserAdmin.fieldsets + (
		('Sacred Work', {'fields': ('role', 'display_name')}),
	)
