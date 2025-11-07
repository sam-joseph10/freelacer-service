from django.contrib import admin
from .models import *

@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "user", "phone", "location")
    search_fields = ("company_name", "user__username", "location")
    list_filter = ("location",)

@admin.register(FreelancerProfile)
class FreelancerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "professional_title",
        "experience_level",
        "location",
        "created_at",
        "last_login_date",
        "login_streak"
    )
    list_filter = ("experience_level", "location", "created_at")
    search_fields = ("full_name", "professional_title", "skills", "location")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    

@admin.register(CertificatePost)
class CertificatePostAdmin(admin.ModelAdmin):
    list_display = ("freelancer", "short_caption", "created_at")
    list_filter = ("created_at",)
    search_fields = ("freelancer__full_name", "caption")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    def short_caption(self, obj):
        return (obj.caption[:50] + "...") if obj.caption and len(obj.caption) > 50 else obj.caption
    short_caption.short_description = "Caption"

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "recruiter", "experience_level", "salary", "status", "deadline")
    search_fields = ("title", "skills_required", "recruiter__company_name")
    list_filter = ("status", "experience_level", "deadline")
    ordering = ("-created_at",)

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'candidate_email', 'job', 'status', 'applied_at')
    list_filter = ('status', 'applied_at', 'job')
    search_fields = ('candidate_name', 'candidate_email', 'job__title')
    readonly_fields = ('applied_at',)  # applied_at should not be editable

@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ('freelancer', 'job', 'saved_at')
    list_filter = ('saved_at', 'freelancer')
    search_fields = ('freelancer__full_name', 'job__title')
    ordering = ('-saved_at',)

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'freelancer', 'recruiter', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('freelancer__full_name', 'recruiter__company_name')
    readonly_fields = ('created_at',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chat_room', 'sender', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('chat_room__id', 'sender__username', 'content')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)

admin.site.register(AIRequestLog)
admin.site.register(Project)
admin.site.register(Task)
admin.site.register(TaskComment)
admin.site.register(Testimonial)