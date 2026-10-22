from django.contrib import admin
from .models import AdminAuditLog, Report, ReportNote, ReportStatusHistory


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'staff', 'action', 'target_type', 'target_repr')
    list_filter = ('action', 'target_type')
    search_fields = ('staff__username', 'target_repr', 'reason')
    readonly_fields = (
        'timestamp', 'staff', 'action', 'target_type',
        'target_id', 'target_repr', 'reason', 'extra',
    )


class ReportNoteInline(admin.TabularInline):
    model = ReportNote
    extra = 1


class ReportStatusHistoryInline(admin.TabularInline):
    model = ReportStatusHistory
    extra = 0
    readonly_fields = ('changed_by', 'old_status', 'new_status', 'reason', 'timestamp')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'report_type', 'category', 'severity', 'status', 'reporter', 'reported_user', 'created_at')
    list_filter = ('status', 'severity', 'report_type', 'category')
    search_fields = ('reference_number', 'reporter__username', 'reported_user__username', 'description')
    inlines = [ReportNoteInline, ReportStatusHistoryInline]

