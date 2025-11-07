from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
import pytz

class RecruiterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    company_description = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.company_name
    
class FreelancerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Basic Info
    full_name = models.CharField(max_length=100)
    professional_title = models.CharField(max_length=200, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    # Location & Timezone
    location = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)  
    
    # ADD THESE FIELDS FOR MAP FUNCTIONALITY
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True, default='IST')
    
    # Skills & Experience
    skills = models.TextField(blank=True, null=True, default="", help_text="Enter skills separated by commas")
    experience_level = models.CharField(
        max_length=50, 
        choices=[
            ('entry', 'Entry Level (0-2 years)'),
            ('intermediate', 'Intermediate (2-5 years)'),
            ('expert', 'Expert (5+ years)')
        ],
        blank=True, null=True
    )
    
    # Availability
    availability_status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('busy', 'Busy'),
            ('offline', 'Offline')
        ],
        default='available'
    )
    
    # Social Links
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    
    # Uploads
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    resume = models.FileField(upload_to="resumes/", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_date = models.DateField(blank=True, null=True)
    login_streak = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    task_completion_rate = models.FloatField(default=0)  # Stores % of approved tasks
    rank_position = models.IntegerField(default=0) 

    def __str__(self):
        return self.full_name or self.user.username

    def get_skills_list(self):
        """Return skills as a list"""
        if self.skills:
            return [skill.strip() for skill in self.skills.split(',')]
        return []

class CertificatePost(models.Model):
    freelancer = models.ForeignKey(
        'FreelancerProfile',
        on_delete=models.CASCADE,
        related_name="certificate_posts"
    )
    certificate = models.ImageField(upload_to="certificates/", blank=True, null=True)
    caption = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.freelancer.full_name} - {self.caption[:30]}"

class Job(models.Model):
    JOB_TYPES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('internship', 'Internship'),
    ]

    recruiter = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    skills_required = models.TextField()
    experience_level = models.CharField(max_length=50)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deadline = models.DateField()
    status = models.CharField(max_length=20, default="Open")
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='full_time')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_job_type_display()})"


class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications', null=True, blank=True)
    freelancer = models.ForeignKey(FreelancerProfile, on_delete=models.CASCADE, related_name='applications', null=True, blank=True)
    candidate_name = models.CharField(max_length=255, default='Unknown Candidate')
    candidate_email = models.EmailField(default='unknown@example.com')
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    status = models.CharField(max_length=50, default='Pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        job_title = self.job.title if self.job else "No Job"
        return f"{self.candidate_name} - {job_title}"

class SavedJob(models.Model):
    freelancer = models.ForeignKey(FreelancerProfile, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('freelancer', 'job')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.freelancer.full_name} saved {self.job.title}"
    

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('application_accepted', 'Application Accepted'),
        ('application_rejected', 'Application Rejected'),
        ('new_job', 'New Job Available'),
        ('new_application', 'New Application Received'),  # Added this line
        ('message', 'New Message'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_job = models.ForeignKey('Job', on_delete=models.CASCADE, null=True, blank=True)
    related_application = models.ForeignKey('Application', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"    

class ChatRoom(models.Model):
    recruiter = models.ForeignKey(
        User, related_name='recruiter_chats', on_delete=models.CASCADE
    )
    freelancer = models.ForeignKey(
        User, related_name='freelancer_chats', on_delete=models.CASCADE
    )
    last_message = models.TextField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Add this line
    recruiter_unread_count = models.IntegerField(default=0)
    freelancer_unread_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('recruiter', 'freelancer')

    def __str__(self):
        return f"Chat: {self.recruiter.username} ↔ {self.freelancer.username}"
    
    def get_other_user(self, user):
        """Return the other participant in this chat"""
        return self.freelancer if self.recruiter == user else self.recruiter
    
class Message(models.Model):
    chat_room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('timestamp',)

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"

class DiscussionComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}"

class AIRequestLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.TextField()
    response = models.TextField()
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"


class Badge(models.Model):
    BADGE_TYPES = [
        ('application', 'Application Based'),
        ('acceptance', 'Acceptance Based'),
        ('profile', 'Profile Based'),
        ('login', 'Login Based'),
    ]

    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    level = models.PositiveIntegerField(default=1)
    icon = models.CharField(max_length=200, blank=True)  # frontend icon path or class name

    def __str__(self):
        return f"{self.name} (Level {self.level})"


class FreelancerBadge(models.Model):
    freelancer = models.ForeignKey('FreelancerProfile', on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('freelancer', 'badge')

    def __str__(self):
        return f"{self.freelancer.full_name} - {self.badge}"

# ==========================
# PROJECT & TASK MANAGEMENT
# ==========================

class Project(models.Model):
    """
    Created automatically when a recruiter accepts a freelancer for a job.
    Links a recruiter and a freelancer to manage tasks & deliverables.
    """
    recruiter = models.ForeignKey(
        'RecruiterProfile', on_delete=models.CASCADE, related_name='projects'
    )
    freelancer = models.ForeignKey(
        'FreelancerProfile', on_delete=models.CASCADE, related_name='projects'
    )
    job = models.ForeignKey(
        'Job', on_delete=models.SET_NULL, null=True, blank=True, related_name='projects'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.recruiter.company_name} ↔ {self.freelancer.full_name})"

    def is_completed(self):
        """Check if all related tasks are approved"""
        total_tasks = self.tasks.count()
        approved_tasks = self.tasks.filter(status='approved').count()
        return total_tasks > 0 and total_tasks == approved_tasks


class Task(models.Model):
    """
    Individual work units under a Project.
    Created by recruiter and assigned to freelancer.
    """
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
    ]
    approval_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('disapproved', 'Disapproved')],
        default='pending'
    )
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tasks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')

    # File handling
    reference_file = models.FileField(
        upload_to='project_references/', blank=True, null=True,
        help_text="Optional file shared by recruiter (brief, guideline, etc.)"
    )
    freelancer_file = models.FileField(
        upload_to='freelancer_uploads/', blank=True, null=True,
        help_text="ZIP file uploaded by freelancer as task deliverable"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def is_done(self):
        return self.status in ['completed', 'approved']


class TaskComment(models.Model):
    """
    Comment thread between recruiter and freelancer inside a task.
    """
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name='comments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_comments'
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.message[:40]}"

class Testimonial(models.Model):
    freelancer = models.ForeignKey(
        'FreelancerProfile',
        on_delete=models.CASCADE,
        related_name='testimonials',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=150, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=5, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.freelancer and self.title:
            return f"{self.freelancer.full_name} - {self.title}"
        elif self.freelancer:
            return f"{self.freelancer.full_name} - Testimonial"
        return "Anonymous Testimonial"
