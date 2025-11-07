from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import *
from .forms import *
from decimal import Decimal
from django.db.models import Count, Q, F
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
import json
import random
import hashlib
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime
from django.contrib.auth import login as auth_login
from django.utils import timezone
from datetime import timedelta
from .models import *
from datetime import date

def calculate_login_streak(freelancer):
    """Simple streak logic - can be improved with a login history model."""
    user = freelancer.user
    last_login = user.last_login.date() if user.last_login else None
    today = timezone.now().date()

    # Store a simple streak count in session or extended model if needed
    if last_login and (today - last_login) == timedelta(days=1):
        streak = getattr(user, 'login_streak', 1) + 1
    else:
        streak = 1
    setattr(user, 'login_streak', streak)
    return streak

def assign_login_badges(freelancer):
    """Award badges for daily login streaks."""
    streak = calculate_login_streak(freelancer)
    
    if streak >= 30:
        level = 3
    elif streak >= 7:
        level = 2
    elif streak >= 1:
        level = 1
    else:
        level = 0

    if level > 0:
        badge, _ = Badge.objects.get_or_create(
            badge_type='login',
            level=level,
            defaults={
                'name': f'Login Streak Level {level}',
                'description': f'Logged in for {streak} consecutive days',
                'icon': 'fa-solid fa-fire'
            }
        )
        FreelancerBadge.objects.get_or_create(freelancer=freelancer, badge=badge)

def home(request):
    # Count active jobs
    total_jobs = Job.objects.filter(status="Open").count()

    # Count freelancers
    total_freelancers = FreelancerProfile.objects.count()

    # Calculate success rate
    completed_apps = Application.objects.filter(status="Accepted").count()
    total_apps = Application.objects.count()

    success_rate = round((completed_apps / total_apps) * 100, 1) if total_apps > 0 else 0

    t = Testimonial.objects.all()
    context = {
        "total_jobs": total_jobs,
        "total_freelancers": total_freelancers,
        "success_rate": success_rate,
        "t":t,
    }
    return render(request, "freelancer/index.html", context)


def login_page(request):
    if request.method == "POST":
        em = request.POST.get("email")
        pas = request.POST.get("password")
        user_type = request.POST.get("user_type")  # freelancer or admin

        user = authenticate(request, username=em, password=pas)

        if user is not None:
            login(request, user)

            if user_type == "freelancer":
                try:
                    free = FreelancerProfile.objects.get(user=user)

                    # ✅ Update last login date
                    
                    if free.last_login_date == date.today() - timedelta(days=1):
                        # Logged in yesterday → continue streak
                        free.login_streak += 1
                    elif free.last_login_date != date.today():
                        # Missed a day or first login → reset streak
                        free.login_streak = 1

                    # Always update last login date
                    free.last_login_date = date.today()
                    free.save(update_fields=["last_login_date", "login_streak"])

                    # ✅ (Optional) Assign login badge later here
                    # assign_login_badges(free)

                    return redirect("freelancer_dashboard")

                except FreelancerProfile.DoesNotExist:
                    return redirect("create_profile")

            elif user_type == "admin":
                return redirect("admin_dashboard")

            else:
                messages.error(request, "Invalid user type selected.")
        else:
            messages.error(request, "Invalid email or password")

    return render(request, "freelancer/login.html")

@login_required
def admin_dashboard(request):
    recruiter = RecruiterProfile.objects.get(user=request.user)

    total_jobs = Job.objects.filter(recruiter=recruiter).count()
    open_jobs = Job.objects.filter(recruiter=recruiter, status='Open').count()
    total_applications = Application.objects.filter(job__recruiter=recruiter).count()
    accepted_candidates = Application.objects.filter(job__recruiter=recruiter, status='Accepted').count()
    
    # Notifications for recruiter - new applications and other recruiter-specific notifications
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    unread_notifications_count = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).count()

    context = {
        'total_jobs': total_jobs,
        'open_jobs': open_jobs,
        'total_applications': total_applications,
        'accepted_candidates': accepted_candidates,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }

    return render(request, 'recruiter/dash.html', context)

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("register")

        user = User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Account created successfully! Please login.")
        return redirect("login")

    return render(request, "freelancer/register.html")

@login_required
def create_profile(request):
    if request.method == "POST":
        # Basic Info
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        full_name = f"{first_name} {last_name}"
        professional_title = request.POST.get("professional_title")
        bio = request.POST.get("bio")
        city = request.POST.get("city")
        location = request.POST.get("location")
        linkedin = request.POST.get("linkedin_url")
        github = request.POST.get("github_url")
        
        # Skills & Experience
        skills = request.POST.get("skills")  # Should be comma-separated string
        experience_level = request.POST.get("experience_level")
        
        # Documents
        profile_picture = request.FILES.get("profile_picture")
        resume = request.FILES.get("resume")
        
        # Create the FreelancerProfile
        FreelancerProfile.objects.create(
            user=request.user,
            full_name=full_name,
            professional_title=professional_title,
            bio=bio,
            city=city,
            location=location,
            linkedin=linkedin,
            github=github,
            skills=skills,
            experience_level=experience_level,
            profile_picture=profile_picture,
            resume=resume,
        )
        
        return redirect("freelancer_dashboard")
    
    return render(request, "freelancer/create_profile.html")

def profile_completion(self):
    """
    Calculate how much of the freelancer's profile is filled (in %)
    """
    fields_to_check = [
        'full_name', 'professional_title', 'bio',
        'location', 'city', 'skills', 'experience_level',
        'availability_status', 'linkedin', 'github',
        'profile_picture', 'resume'
    ]

    filled_fields = 0
    total_fields = len(fields_to_check)

    for field_name in fields_to_check:
        value = getattr(self, field_name)

        # Special handling for skills
        if field_name == 'skills':
            if value and any(s.strip() for s in value.split(',')):
                filled_fields += 1

        # Special handling for file fields
        elif field_name in ['profile_picture', 'resume']:
            if value and hasattr(value, 'name') and value.name != '':
                filled_fields += 1

        # Normal fields
        else:
            if value not in [None, '', []]:
                filled_fields += 1

    completion_percentage = round((filled_fields / total_fields) * 100, 2)
    return completion_percentage

@login_required
def freelancer_dashboard(request):
    freelancer = get_object_or_404(FreelancerProfile, user=request.user)
    
    # Applications
    applications = Application.objects.filter(freelancer=freelancer)
    applications_sent_count = applications.count()
    applications_accepted_count = applications.filter(status='Accepted').count()
    
    # Get application dates for the calendar
    application_dates = []
    for application in applications:
        if application.applied_at:
            # Format as YYYY-MM-DD for JavaScript
            date_str = application.applied_at.strftime('%Y-%m-%d')
            application_dates.append(date_str)
    
    # Jobs matching skills
    freelancer_skills = [skill.strip().lower() for skill in freelancer.skills.split(",") if skill]
    if freelancer_skills:
        jobs_matching_skills = Job.objects.filter(
            status='Open'
        ).filter(
            Q(skills_required__iregex=r'(' + '|'.join(freelancer_skills) + ')')
        ).distinct()
    else:
        jobs_matching_skills = Job.objects.filter(status='Open')
    
    my_interests_count = jobs_matching_skills.count()

    # Latest 5 jobs notifications
    jobs_notifications = Job.objects.filter(status='Open').order_by('-created_at')[:5]
    saved_job_ids = freelancer.saved_jobs.values_list('job_id', flat=True)

    # Flag if freelancer has applied
    for job in jobs_notifications:
        job.applied = job.applications.filter(freelancer=freelancer).exists()
        job.saved = job.id in saved_job_ids

    # Saved jobs count
    saved_jobs_count = freelancer.saved_jobs.count()
    
    # Notifications
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    ai_history = AIRequestLog.objects.filter(user=request.user)[:20] 
    ai_history = json.dumps(list(ai_history.values('prompt', 'response')), cls=DjangoJSONEncoder) # latest 20

    profile = FreelancerProfile.objects.get(user=request.user)

    today = date.today()

    # ---------------- LOGIN STREAK ----------------
    if profile.last_login_date == today - timedelta(days=1):
        profile.login_streak += 1
    elif profile.last_login_date != today:
        profile.login_streak = 1

    profile.last_login_date = today
    profile.save(update_fields=['last_login_date', 'login_streak'])

    # ---------------- APPLICATION BADGE ----------------
    total_applied = Application.objects.filter(freelancer=profile).count()
    app_level = total_applied // 10
    app_next_target = (app_level + 1) * 10
    has_app_badge = total_applied >= 10

    # ---------------- ACCEPTANCE BADGE ----------------
    total_accepted = Application.objects.filter(freelancer=profile, status='Accepted').count()
    acc_level = total_accepted // 5
    acc_next_target = (acc_level + 1) * 5
    has_acc_badge = total_accepted >= 5

    # ---------------- PROFILE BADGE ----------------
    profile_complete = profile_completion(profile)
    has_profile_badge = profile_complete == 100

    # ---------------- LOGIN BADGE ----------------
    login_streak = profile.login_streak
    login_level = login_streak // 5  # 1 level per 5 days
    has_login_badge = login_streak >= 5

    # ---------------- COLLECT BADGES ----------------
    badges = {}

    if total_applied > 0:
        badges['application'] = {
            'has_badge': has_app_badge,
            'level': app_level if has_app_badge else 0,
            'completed': total_applied,
            'next_target': app_next_target,
        }

    if total_accepted > 0:
        badges['acceptance'] = {
            'has_badge': has_acc_badge,
            'level': acc_level if has_acc_badge else 0,
            'completed': total_accepted,
            'next_target': acc_next_target,
        }

    if profile_complete > 0:
        if profile_complete == 100:
            badges['profile'] = {
                'has_badge': True,
                'completed': 100,   # show 100% completed
                'next_target': None,
            }
        else:
            badges['profile'] = {
                'has_badge': False,
                'completed': int(profile_complete),  # show % completed
                'next_target': 100,
            }

    if login_streak > 0:
        badges['login'] = {
            'has_badge': has_login_badge,
            'level': login_level if has_login_badge else 0,
            'streak': login_streak,
        }
    print(total_applied)
    print(total_accepted)
    print(profile_complete)
    print(login_streak)

    # Count projects for a freelancer where all tasks are approved and project status is 'completed'
    projects_completed = Task.objects.filter(
        project__freelancer=profile,
        approval_status='approved'
    ).count()


    return render(request, 'freelancer/freelancer_dashboard.html', {
        "profile": freelancer,
        "applications_sent_count": applications_sent_count,
        "applications_accepted_count": applications_accepted_count,
        "my_interests_count": my_interests_count,
        "jobs_notifications": jobs_notifications,
        "saved_jobs_count": saved_jobs_count,
        "notifications": notifications,
        "unread_notifications_count": unread_notifications_count,
        "ai_history": ai_history,
        "application_dates": json.dumps(application_dates),  # Add application dates for calendar
        'badges': badges,
        "projects_completed":projects_completed,
        "total_earnings": profile.total_earnings or 0,
    })

@login_required
def view_profile(request):
    profile = get_object_or_404(FreelancerProfile, user=request.user)

    # Skills list
    skills_list = []
    if profile.skills:
        skills_list = [skill.strip() for skill in profile.skills.split(",")]

    # Profile completion
    fields_to_check = [
        profile.full_name,
        profile.professional_title,
        profile.bio,
        profile.skills,
        profile.experience_level,
        profile.profile_picture,
        profile.resume,
        profile.location,
        profile.linkedin,
        profile.github,
    ]
    completed_fields = sum(1 for field in fields_to_check if field)
    total_fields = len(fields_to_check)
    completion_percentage = int((completed_fields / total_fields) * 100)

    # Certificates linked to this profile
    posts = CertificatePost.objects.filter(freelancer=profile)

    applications = Application.objects.filter(freelancer=profile)
    applications_sent_count = applications.count()
    applications_accepted_count = applications.filter(status='Accepted').count()
    saved_jobs_count = profile.saved_jobs.count()
    
    # Notifications for the profile page
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    profile = FreelancerProfile.objects.get(user=request.user)

    today = date.today()

    # ---------------- LOGIN STREAK ----------------
    if profile.last_login_date == today - timedelta(days=1):
        profile.login_streak += 1
    elif profile.last_login_date != today:
        profile.login_streak = 1

    profile.last_login_date = today
    profile.save(update_fields=['last_login_date', 'login_streak'])

    # ---------------- APPLICATION BADGE ----------------
    total_applied = Application.objects.filter(freelancer=profile).count()
    app_level = total_applied // 10
    app_next_target = (app_level + 1) * 10
    has_app_badge = total_applied >= 10

    # ---------------- ACCEPTANCE BADGE ----------------
    total_accepted = Application.objects.filter(freelancer=profile, status='Accepted').count()
    acc_level = total_accepted // 5
    acc_next_target = (acc_level + 1) * 5
    has_acc_badge = total_accepted >= 5

    # ---------------- PROFILE BADGE ----------------
    profile_complete = profile_completion(profile)
    has_profile_badge = profile_complete == 100

    # ---------------- LOGIN BADGE ----------------
    login_streak = profile.login_streak
    login_level = login_streak // 5  # 1 level per 5 days
    has_login_badge = login_streak >= 5

    # ---------------- COLLECT BADGES ----------------
    badges = {}

    if total_applied > 0:
        badges['application'] = {
            'has_badge': has_app_badge,
            'level': app_level if has_app_badge else 0,
            'completed': total_applied,
            'next_target': app_next_target,
        }

    if total_accepted > 0:
        badges['acceptance'] = {
            'has_badge': has_acc_badge,
            'level': acc_level if has_acc_badge else 0,
            'completed': total_accepted,
            'next_target': acc_next_target,
        }

    if profile_complete > 0:
        if profile_complete == 100:
            badges['profile'] = {
                'has_badge': True,
                'completed': 100,   # show 100% completed
                'next_target': None,
            }
        else:
            badges['profile'] = {
                'has_badge': False,
                'completed': int(profile_complete),  # show % completed
                'next_target': 100,
            }

    if login_streak > 0:
        badges['login'] = {
            'has_badge': has_login_badge,
            'level': login_level if has_login_badge else 0,
            'streak': login_streak,
        }

    return render(request, "freelancer/view_profile.html", {
        "profile": profile,
        "skills_list": skills_list,
        "completion_percentage": completion_percentage,
        "applications_sent_count": applications_sent_count,
        "saved_jobs_count": saved_jobs_count,
        "applications_accepted_count": applications_accepted_count,
        "posts": posts,
        "notifications": notifications,
        "unread_notifications_count": unread_notifications_count,
        "badges":badges,
    })

@login_required
def edit_profile(request):
    profile = get_object_or_404(FreelancerProfile, user=request.user)
    certificates = CertificatePost.objects.filter(freelancer=profile)  # fetch user certificates

    if request.method == "POST":
        # Update basic info
        profile.full_name = request.POST.get("full_name")
        profile.bio = request.POST.get("bio")
        profile.skills = request.POST.get("skills")

        # Update social links with proper URLs
        linkedin = request.POST.get("linkedin")
        github = request.POST.get("github")

        if linkedin and not linkedin.startswith("http"):
            linkedin = "https://" + linkedin
        if github and not github.startswith("http"):
            github = "https://" + github

        profile.linkedin = linkedin
        profile.github = github

        # Update files if uploaded
        if request.FILES.get("profile_picture"):
            profile.profile_picture = request.FILES.get("profile_picture")
        if request.FILES.get("resume"):
            profile.resume = request.FILES.get("resume")

        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("view_profile")

    return render(request, "freelancer/edit_profile.html", {
        "profile": profile,
        "certificates": certificates  # pass to template
    })

def logout_view(request):
    logout(request)
    return redirect('home') 

@login_required
def upload_certificate(request):
    profile = FreelancerProfile.objects.get(user=request.user)

    if request.method == "POST":
        form = CertificatePostForm(request.POST, request.FILES)
        if form.is_valid():
            certificate_post = form.save(commit=False)
            certificate_post.freelancer = profile
            certificate_post.save()
            return redirect("view_profile")
    else:
        form = CertificatePostForm()

    return render(request, "freelancer/upload_certificate.html", {"form": form})

@login_required
def edit_post(request, post_id):
    freelancer = FreelancerProfile.objects.get(user=request.user)
    post = get_object_or_404(CertificatePost, id=post_id, freelancer=freelancer)

    if request.method == 'POST':
        post.caption=request.POST.get("caption")
        post.save()
        return redirect('edit_profile')
    
    return render(request, 'freelancer/edit_post.html', {'post': post})

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(CertificatePost, id=post_id, freelancer__user=request.user)

    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Certificate deleted successfully!')
        return redirect('edit_profile')

@login_required
def post_job(request):
    recruiter = RecruiterProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.recruiter = recruiter
            job.save()
            
            # Create notifications for freelancers with matching skills
            if job.skills_required:
                job_skills = [skill.strip().lower() for skill in job.skills_required.split(",") if skill.strip()]
                matching_freelancers = FreelancerProfile.objects.filter(
                    Q(skills__iregex=r'(' + '|'.join(job_skills) + ')')
                )
                
                for freelancer in matching_freelancers:
                    Notification.objects.create(
                        user=freelancer.user,
                        notification_type='new_job',
                        message=f"New job posted: {job.title} - matches your skills!",
                        related_job=job
                    )
            
            messages.success(request, "Job posted successfully!")
            return redirect('my_jobs')
    else:
        form = JobForm()

    return render(request, 'recruiter/post_job.html', {'form': form})

@login_required
def my_jobs(request):
    recruiter = RecruiterProfile.objects.get(user=request.user)
    jobs = Job.objects.filter(recruiter=recruiter)
    
    # Notifications for recruiter
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'recruiter/my_jobs.html', {
        'jobs': jobs,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })

@login_required
def close_job(request, job_id):
    recruiter = RecruiterProfile.objects.get(user=request.user)
    job = get_object_or_404(Job, id=job_id, recruiter=recruiter)
    job.status = "Closed"
    job.save()
    messages.success(request, "Job closed successfully!")
    return redirect('my_jobs')

@login_required
def edit_job(request, job_id):
    recruiter = RecruiterProfile.objects.get(user=request.user)
    job = get_object_or_404(Job, id=job_id, recruiter=recruiter)

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Job updated successfully!")
            return redirect('my_jobs')
    else:
        form = JobForm(instance=job)

    return render(request, 'recruiter/edit_job.html', {'form': form})

@login_required
def view_applications(request, job_id):
    recruiter = RecruiterProfile.objects.get(user=request.user)
    job = get_object_or_404(Job, id=job_id, recruiter=recruiter)
    applications = job.applications.all()
    
    # Notifications for recruiter
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'recruiter/job_applications.html', {
        'job': job, 
        'applications': applications,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })

@login_required
def update_application_status(request, app_id, status):
    """
    Update application status: 'Accepted' or 'Rejected' and send email to freelancer.
    """
    application = get_object_or_404(Application, id=app_id)

    # Ensure the recruiter owns the job
    if application.job.recruiter.user != request.user:
        return redirect('my_jobs')

    if status in ['Accepted', 'Rejected']:
        application.status = status
        application.save()

        # Create notification for freelancer
        if status == 'Accepted':
            notification_type = 'application_accepted'
            message = f"Congratulations! Your application for '{application.job.title}' has been accepted."
            subject = "🎉 Congratulations! Your Application is Accepted"
            email_message = f"""
Hi {application.freelancer.user.first_name},

Congratulations! Your application for the position '{application.job.title}' has been accepted. 

The recruiter will contact you soon with further details.

Best regards,
{application.job.recruiter.user.first_name} 
"""
            # ✅ AUTO-CREATE CHAT ROOM + SEND FIRST MESSAGE
            recruiter_user = application.job.recruiter.user
            freelancer_user = application.freelancer.user

            chat_room, created = ChatRoom.objects.get_or_create(
                recruiter=recruiter_user,
                freelancer=freelancer_user
            )

            # Auto-send a welcome message
            Message.objects.create(
                chat_room=chat_room,
                sender=recruiter_user,
                content=f"Hi {freelancer_user.first_name}, congratulations! I accepted your application for '{application.job.title}'. Let's discuss further here."
            )

            # Update last message field
            chat_room.last_message = f"Hi {freelancer_user.first_name}, congratulations! I accepted your application."
            chat_room.recruiter_unread_count = 0
            chat_room.freelancer_unread_count += 1  # freelancer has unread message
            chat_room.save()

            # =========================
            # AUTO-CREATE PROJECT
            # =========================
            project, created = Project.objects.get_or_create(
                recruiter=application.job.recruiter,
                freelancer=application.freelancer,
                job=application.job,
                defaults={
                    'title': f"{application.job.title} - {application.freelancer.full_name}",
                    'description': f"Project for {application.freelancer.full_name} on job '{application.job.title}'"
                }
            )

        else:
            notification_type = 'application_rejected'
            message = f"Your application for '{application.job.title}' was not selected this time."
            subject = "Application Status Update: Regret"
            email_message = f"""
Hi {application.freelancer.user.first_name},

We appreciate your interest in the position '{application.job.title}'.

Unfortunately, your application has not been selected this time. Keep applying and we wish you all the best for your future opportunities.

Best regards,
{application.job.recruiter.user.first_name} 
"""

        # Create notification
        Notification.objects.create(
            user=application.freelancer.user,
            notification_type=notification_type,
            message=message,
            related_job=application.job,
            related_application=application
        )

        # Send email
        send_mail(
            subject,
            email_message,
            settings.EMAIL_HOST_USER,
            [application.freelancer.user.email],
            fail_silently=False,
        )
        
        messages.success(request, f"Application {status.lower()} successfully!")

    return redirect('view_applications', job_id=application.job.id)

@login_required
def recruiter_profile(request):
    recruiter = RecruiterProfile.objects.get(user=request.user)

    if request.method == 'POST':
        form = RecruiterProfileForm(request.POST, instance=recruiter)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('admin_dashboard')
    else:
        form = RecruiterProfileForm(instance=recruiter)
        
    # Notifications for recruiter
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'recruiter/profile.html', {
        'form': form,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })


def view_freelancer_profile(request, freelancer_id):
    freelancer = get_object_or_404(FreelancerProfile, id=freelancer_id)
    profile = freelancer

    # ---------------- APPLICATION BADGE ----------------
    total_applied = Application.objects.filter(freelancer=profile).count()
    app_level = total_applied // 10
    app_next_target = (app_level + 1) * 10
    has_app_badge = total_applied >= 10

    # ---------------- ACCEPTANCE BADGE ----------------
    total_accepted = Application.objects.filter(freelancer=profile, status='Accepted').count()
    acc_level = total_accepted // 5
    acc_next_target = (acc_level + 1) * 5
    has_acc_badge = total_accepted >= 5

    # ---------------- PROFILE BADGE ----------------
    profile_complete = profile_completion(profile)
    has_profile_badge = profile_complete == 100

    # ---------------- LOGIN BADGE ----------------
    login_streak = profile.login_streak
    login_level = login_streak // 5  # 1 level per 5 days
    has_login_badge = login_streak >= 5

    # ---------------- COLLECT BADGES ----------------
    badges = {}

    if total_applied > 0:
        badges['application'] = {
            'has_badge': has_app_badge,
            'level': app_level if has_app_badge else 0,
            'completed': total_applied,
            'next_target': app_next_target,
        }

    if total_accepted > 0:
        badges['acceptance'] = {
            'has_badge': has_acc_badge,
            'level': acc_level if has_acc_badge else 0,
            'completed': total_accepted,
            'next_target': acc_next_target,
        }

    if profile_complete > 0:
        if profile_complete == 100:
            badges['profile'] = {
                'has_badge': True,
                'completed': 100,   # show 100% completed
                'next_target': None,
            }
        else:
            badges['profile'] = {
                'has_badge': False,
                'completed': int(profile_complete),  # show % completed
                'next_target': 100,
            }

    if login_streak > 0:
        badges['login'] = {
            'has_badge': has_login_badge,
            'level': login_level if has_login_badge else 0,
            'streak': login_streak,
        }
    return render(request, 'recruiter/freelancer_profile.html', 
                  {'freelancer': freelancer,
                   "badges":badges,
                }
                )

@login_required
def jobs_page(request):
    freelancer = get_object_or_404(FreelancerProfile, user=request.user)
    
    # Only Full-time and Part-time jobs (exclude Internships)
    jobs = Job.objects.filter(status='Open').exclude(job_type='internship')
    
    # Get freelancer skills
    freelancer_skills = []
    if freelancer.skills:
        freelancer_skills = [skill.strip().lower() for skill in freelancer.skills.split(",") if skill.strip()]
    
    # Calculate skill matching percentage for each job
    for job in jobs:
        job.applied = job.applications.filter(freelancer=freelancer).exists()
        
        # Calculate skill match percentage
        if freelancer_skills and job.skills_required:
            job_skills = [skill.strip().lower() for skill in job.skills_required.split(",") if skill.strip()]
            
            # Calculate matching skills
            matching_skills = set(freelancer_skills) & set(job_skills)
            
            # Calculate percentage
            if job_skills:
                match_percentage = (len(matching_skills) / len(job_skills)) * 100
                job.skill_match_percentage = round(match_percentage)
                job.matching_skills = list(matching_skills)
            else:
                job.skill_match_percentage = 0
                job.matching_skills = []
        else:
            job.skill_match_percentage = 0
            job.matching_skills = []
    
    # Freshly get saved jobs
    saved_jobs = freelancer.saved_jobs.all().values_list('job_id', flat=True)
    
    # Notifications for the jobs page
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'freelancer/jobs_page.html', {
        'jobs': jobs,
        'saved_jobs': saved_jobs,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'freelancer_skills': freelancer_skills,
    })


@login_required
def apply_job(request, job_id):
    freelancer = get_object_or_404(FreelancerProfile, user=request.user)
    job = get_object_or_404(Job, id=job_id)

    # Check if already applied
    already_applied = Application.objects.filter(job=job, freelancer=freelancer).exists()

    if request.method == 'POST' and not already_applied:
        cover_letter = request.POST.get('cover_letter', '')
        resume = request.FILES.get('resume') or freelancer.resume

        application = Application.objects.create(
            job=job,
            freelancer=freelancer,
            candidate_name=freelancer.full_name,
            candidate_email=freelancer.user.email,
            resume=resume,
            status='Pending'
        )
        
        # Create notification for recruiter when freelancer applies
        Notification.objects.create(
            user=job.recruiter.user,
            notification_type='new_application',
            message=f"New application received for '{job.title}' from {freelancer.full_name}",
            related_job=job,
            related_application=application
        )
        
        # If it's an AJAX request, return the application date for real-time calendar update
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            application_date = application.applied_at.strftime('%Y-%m-%d') if application.applied_at else ''
            return JsonResponse({
                'success': True,
                'application_date': application_date,
                'message': 'Application submitted successfully!'
            })
        
        messages.success(request, "Application submitted successfully!")
        return redirect('jobs_page')

    return render(request, 'freelancer/apply_job.html', {
        'job': job,
        'already_applied': already_applied,
        'freelancer': freelancer,
    })

@login_required
def freelancer_applications(request):
    # Get freelancer profile
    freelancer = get_object_or_404(FreelancerProfile, user=request.user)
    
    # Get all applications of this freelancer, latest first
    applications = Application.objects.filter(freelancer=freelancer).order_by('-applied_at')
    
    # Notifications for the applications page
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'freelancer/freelancer_applications.html', {
        'applications': applications,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })

@login_required
def toggle_save_job(request, job_id):
    freelancer = get_object_or_404(FreelancerProfile, user=request.user)
    job = get_object_or_404(Job, id=job_id)
    
    saved_job, created = SavedJob.objects.get_or_create(freelancer=freelancer, job=job)
    
    if not created:  # Already exists → unsave
        saved_job.delete()
        messages.info(request, "Job removed from saved jobs.")
    else:
        messages.success(request, "Job saved successfully!")
    
    # Stay on the same page
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)

@login_required
def saved_jobs_page(request):
    freelancer = get_object_or_404(FreelancerProfile, user=request.user)
    saved_jobs = SavedJob.objects.filter(freelancer=freelancer).select_related('job')
    
    # Notifications for the saved jobs page
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'freelancer/saved_jobs.html', {
        'saved_jobs': saved_jobs,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })

@login_required
def internship_page(request):
    freelancer = FreelancerProfile.objects.get(user=request.user)
    
    # Only open internships
    internships = Job.objects.filter(status='Open', job_type='internship').order_by('-created_at')
    
    # Flag if the freelancer has already applied
    for job in internships:
        job.applied = job.applications.filter(freelancer=freelancer).exists()
    
    saved_jobs = freelancer.saved_jobs.all().values_list('job_id', flat=True)

    # Notifications for the internship page
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    # Get freelancer skills as a string
    freelancer_skills = freelancer.skills or ""
    
    return render(request, 'freelancer/internship_page.html', {
        'internships': internships,
        'saved_jobs': saved_jobs,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'freelancer_skills': freelancer_skills,  # Pass freelancer skills to template
    })

@login_required
def freelancer_messages(request):
    # Only freelancers can access
    if not hasattr(request.user, 'freelancerprofile'):
        return redirect('login')

    # Get chats where this freelancer is involved
    chat_rooms = ChatRoom.objects.filter(freelancer=request.user)

    # Get list of recruiters who already have a chat with them
    available_recruiters = User.objects.filter(
        id__in=chat_rooms.values_list('recruiter', flat=True)
    )

    return render(request, 'freelancer/freelancer_messages.html', {
        'chat_rooms': chat_rooms,
        'available_recruiters': available_recruiters,
    })

@login_required
def recruiter_messages(request):
    # ✅ Ensure only recruiters can access this page
    if not hasattr(request.user, 'recruiterprofile'):
        return redirect('login')

    # ✅ Fetch all chat rooms for this recruiter
    chat_rooms = ChatRoom.objects.filter(recruiter=request.user)

    # ✅ Optionally list freelancers who don't have a chat yet (for starting new chat)
    available_freelancers = User.objects.filter(
        freelancerprofile__isnull=False
    ).exclude(
        id__in=chat_rooms.values_list('freelancer', flat=True)
    )

    # ✅ Render recruiter's messaging page
    return render(request, 'recruiter/recruiter_messages.html', {
        'chat_rooms': chat_rooms,
        'available_freelancers': available_freelancers,
    })

@login_required
def freelancer_map(request):
    """View for the freelancer geo map"""
    recruiter = RecruiterProfile.objects.get(user=request.user)
    
    # Get all freelancers with location data
    freelancers = FreelancerProfile.objects.exclude(
        Q(location__isnull=True) | Q(location__exact='')
    )
    
    # Count stats for the map view
    total_freelancers = freelancers.count()
    available_freelancers = freelancers.filter(availability_status='available').count()
    
    # Notifications for recruiter
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'total_freelancers': total_freelancers,
        'available_freelancers': available_freelancers,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    
    return render(request, 'recruiter/freelancer_map.html', context)

@login_required
def get_freelancer_data(request):
    """API endpoint to get freelancer data for the map"""
    try:
        freelancers = FreelancerProfile.objects.all().select_related('user')
        
        freelancer_data = []
        
        for freelancer in freelancers:
            # Get coordinates based on location with proper country detection
            lat, lng, country = get_freelancer_coordinates(freelancer)
            
            # Update the freelancer's coordinates in the database
            if lat and lng:
                freelancer.latitude = lat
                freelancer.longitude = lng
                freelancer.save(update_fields=['latitude', 'longitude'])
            
            if lat and lng:
                freelancer_data.append({
                    'id': freelancer.id,
                    'name': freelancer.full_name or 'Unknown',
                    'professional_title': freelancer.professional_title or 'Freelancer',
                    'location': freelancer.location or 'Location not specified',
                    'country': country,
                    'timezone': freelancer.timezone or 'IST',
                    'skills': freelancer.skills or 'No skills specified',
                    'status': freelancer.availability_status or 'offline',
                    'lat': float(lat),
                    'lng': float(lng),
                    'profile_url': f"/freelancer/{freelancer.id}/",
                    'profile_picture': freelancer.profile_picture.url if freelancer.profile_picture else '/static/default-avatar.png',
                    'experience_level': freelancer.get_experience_level_display() if freelancer.experience_level else 'Not specified'
                })
        
        return JsonResponse({'freelancers': freelancer_data})
    
    except Exception as e:
        print(f"Error in get_freelancer_data: {e}")
        return JsonResponse({'freelancers': [], 'error': str(e)})

def get_freelancer_coordinates(freelancer):
    """Get coordinates for a freelancer with proper country detection"""
    # If coordinates are already stored, use them
    if freelancer.latitude and freelancer.longitude:
        return freelancer.latitude, freelancer.longitude, 'India'
    
    location = (freelancer.location or '').lower().strip()
    
    # Comprehensive country detection
    country_mappings = {
        # USA
        'usa': (37.0902, -95.7129, 'USA'),
        'united states': (37.0902, -95.7129, 'USA'),
        'us': (37.0902, -95.7129, 'USA'),
        'new york': (40.7128, -74.0060, 'USA'),
        'california': (36.7783, -119.4179, 'USA'),
        'texas': (31.9686, -99.9018, 'USA'),
        'florida': (27.6648, -81.5158, 'USA'),
        
        # UK
        'uk': (55.3781, -3.4360, 'UK'),
        'united kingdom': (55.3781, -3.4360, 'UK'),
        'london': (51.5074, -0.1278, 'UK'),
        'england': (52.3555, -1.1743, 'UK'),
        
        # Canada
        'canada': (56.1304, -106.3468, 'Canada'),
        'toronto': (43.6532, -79.3832, 'Canada'),
        'vancouver': (49.2827, -123.1207, 'Canada'),
        
        # Australia
        'australia': (-25.2744, 133.7751, 'Australia'),
        'sydney': (-33.8688, 151.2093, 'Australia'),
        'melbourne': (-37.8136, 144.9631, 'Australia'),
        
        # Europe
        'germany': (51.1657, 10.4515, 'Germany'),
        'france': (46.6034, 1.8883, 'France'),
        'spain': (40.4637, -3.7492, 'Spain'),
        'italy': (41.8719, 12.5674, 'Italy'),
        
        # Asia (excluding India)
        'japan': (36.2048, 138.2529, 'Japan'),
        'china': (35.8617, 104.1954, 'China'),
        'singapore': (1.3521, 103.8198, 'Singapore'),
        'uae': (23.4241, 53.8478, 'UAE'),
        'dubai': (25.2048, 55.2708, 'UAE'),
    }
    
    # Check if location contains any specific country names (non-India)
    for country_name, coords in country_mappings.items():
        if country_name in location:
            return coords[0], coords[1], coords[2]
    
    # INDIAN CITIES MAPPING - Comprehensive list
    indian_cities = {
        # Major Metropolitan Cities
        'mumbai': (19.0760, 72.8777),
        'delhi': (28.7041, 77.1025),
        'new delhi': (28.6139, 77.2090),
        'bangalore': (12.9716, 77.5946),
        'bengaluru': (12.9716, 77.5946),
        'chennai': (13.0827, 80.2707),
        'madras': (13.0827, 80.2707),
        'kolkata': (22.5726, 88.3639),
        'calcutta': (22.5726, 88.3639),
        'hyderabad': (17.3850, 78.4867),
        'pune': (18.5204, 73.8567),
        'ahmedabad': (23.0225, 72.5714),
        'surat': (21.1702, 72.8311),
        
        # IT Hubs
        'gurgaon': (28.4595, 77.0266),
        'gurugram': (28.4595, 77.0266),
        'noida': (28.5355, 77.3910),
        'greater noida': (28.4744, 77.5040),
        'ghaziabad': (28.6692, 77.4538),
        'faridabad': (28.4089, 77.3178),
        
        # Other Major Cities
        'jaipur': (26.9124, 75.7873),
        'lucknow': (26.8467, 80.9462),
        'kanpur': (26.4499, 80.3319),
        'nagpur': (21.1458, 79.0882),
        'indore': (22.7196, 75.8577),
        'thane': (19.2183, 72.9781),
        'bhopal': (23.2599, 77.4126),
        'visakhapatnam': (17.6868, 83.2185),
        'vizag': (17.6868, 83.2185),
        'patna': (25.5941, 85.1376),
        'vadodara': (22.3072, 73.1812),
        'kochi': (9.9312, 76.2673),
        'cochin': (9.9312, 76.2673),
        'kozhikode': (11.2588, 75.7804),
        'calicut': (11.2588, 75.7804),
        'bhubaneswar': (20.2961, 85.8245),
        'dehradun': (30.3165, 78.0322),
        'mangalore': (12.9141, 74.8560),
        'mysore': (12.2958, 76.6394),
        'tiruchirappalli': (10.7905, 78.7047),
        'trichy': (10.7905, 78.7047),
        'guwahati': (26.1445, 91.7362),
        'chandigarh': (30.7333, 76.7794),
        'amritsar': (31.6340, 74.8723),
        'jodhpur': (26.2389, 73.0243),
        'raipur': (21.2514, 81.6296),
        'ranchi': (23.3441, 85.3096),
        'jabalpur': (23.1815, 79.9864),
        'allahabad': (25.4358, 81.8463),
        'prayagraj': (25.4358, 81.8463),
        'varanasi': (25.3176, 82.9739),
        'srinagar': (34.0837, 74.7973),
        
        # States and regions as fallback
        'maharashtra': (19.7515, 75.7139),
        'karnataka': (15.3173, 75.7139),
        'tamil nadu': (11.1271, 78.6569),
        'kerala': (10.8505, 76.2711),
        'andhra pradesh': (15.9129, 79.7400),
        'telangana': (17.1232, 79.2088),
        'uttar pradesh': (26.8467, 80.9462),
        'rajasthan': (27.0238, 74.2179),
        'gujarat': (22.2587, 71.1924),
        'punjab': (31.1471, 75.3412),
        'haryana': (29.0588, 76.0856),
        'madhya pradesh': (22.9734, 78.6569),
        'bihar': (25.0961, 85.3131),
        'west bengal': (22.9868, 87.8550),
        'odisha': (20.9517, 85.0985),
        'assam': (26.2006, 92.9376),
    }
    
    # First, try to find exact city match in India
    for city, coords in indian_cities.items():
        if city in location:
            return coords[0], coords[1], 'India'
    
    # If no specific city found but location contains "india" or looks Indian
    if any(indicator in location for indicator in ['india', 'indian', 'in-', '.in', 'maharash', 'karnatak', 'tamil', 'kerala', 'bihar', 'punjab', 'gujarat']):
        # Use a hash of the freelancer ID to consistently place them across India
        if freelancer.id:
            hash_obj = hashlib.md5(str(freelancer.id).encode())
            hash_int = int(hash_obj.hexdigest(), 16)
            
            # Create a list of major Indian city coordinates
            major_indian_cities = list(indian_cities.values())
            index = hash_int % len(major_indian_cities)
            coords = major_indian_cities[index]
            return coords[0], coords[1], 'India'
    
    # Final fallback - assume India and place in center
    return 20.5937, 78.9629, 'India'

@login_required
def get_candidate_location(request, freelancer_id):
    """API endpoint to get candidate country and skills data"""
    try:
        freelancer = FreelancerProfile.objects.get(id=freelancer_id)
        
        # Get country from location or use default
        location = freelancer.location or ''
        country = extract_country_from_location(location) or 'India'  # Default to India
        
        # Get coordinates for the country
        lat, lng = get_country_coordinates(country)
        
        location_data = {
            'country': country,
            'skills': freelancer.skills or 'Skills not specified',
            'lat': lat,
            'lng': lng,
        }
        return JsonResponse(location_data)
    except FreelancerProfile.DoesNotExist:
        return JsonResponse({'error': 'Candidate not found'}, status=404)

def extract_country_from_location(location):
    """Extract country from location string"""
    if not location:
        return None
    
    location_lower = location.lower()
    
    country_mappings = {
        'usa': 'USA',
        'united states': 'USA',
        'us': 'USA',
        'uk': 'UK',
        'united kingdom': 'UK',
        'canada': 'Canada',
        'australia': 'Australia',
        'germany': 'Germany',
        'france': 'France',
        'japan': 'Japan',
        'china': 'China',
        'singapore': 'Singapore',
        'uae': 'UAE',
        'dubai': 'UAE',
        'india': 'India',
    }
    
    for country_key, country_name in country_mappings.items():
        if country_key in location_lower:
            return country_name
    
    return 'India'  # Default to India

def get_country_coordinates(country):
    """Get coordinates for a country"""
    country_coordinates = {
        'India': (20.5937, 78.9629),
        'USA': (37.0902, -95.7129),
        'UK': (55.3781, -3.4360),
        'Canada': (56.1304, -106.3468),
        'Australia': (-25.2744, 133.7751),
        'Germany': (51.1657, 10.4515),
        'France': (46.6034, 1.8883),
        'Japan': (36.2048, 138.2529),
        'China': (35.8617, 104.1954),
        'Singapore': (1.3521, 103.8198),
        'UAE': (23.4241, 53.8478),
    }
    
    return country_coordinates.get(country, (20.5937, 78.9629))  # Default to India


# Notification System Views
@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})

@login_required
def view_all_notifications(request):
    """View all notifications page"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'freelancer/all_notifications.html', {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })

@login_required
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    messages.success(request, "Notification deleted successfully!")
    return redirect('view_all_notifications')

@login_required
def clear_all_notifications(request):
    """Clear all notifications for the current user"""
    Notification.objects.filter(user=request.user).delete()
    messages.success(request, "All notifications cleared successfully!")
    return redirect('view_all_notifications')


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from datetime import datetime, timedelta
from .models import Application, SavedJob, FreelancerProfile

@login_required
def freelancer_analytics(request):
    # Get the freelancer profile
    freelancer = FreelancerProfile.objects.get(user=request.user)
    
    # 1️⃣ Application Status Overview
    status_counts = (
        Application.objects.filter(freelancer=freelancer)
        .values('status')
        .annotate(total=Count('status'))
    )
    status_data = {'Pending': 0, 'Accepted': 0, 'Rejected': 0}
    for s in status_counts:
        status_data[s['status']] = s['total']

    total_applications = sum(status_data.values())

    # 2️⃣ My Monthly Activity (Applications Sent per Month)
    current_month = datetime.now().month
    monthly_data = []
    months = []

    for i in range(3, -1, -1):  # Last 4 months
        month_date = datetime.now() - timedelta(days=30 * i)
        month_name = month_date.strftime("%B")
        months.append(month_name)
        count = Application.objects.filter(
            freelancer=freelancer,
            applied_at__month=month_date.month,
            applied_at__year=month_date.year
        ).count()
        monthly_data.append(count)

    # 3️⃣ Saved Jobs by Type
    saved_jobs = (
        SavedJob.objects.filter(freelancer=freelancer)
        .values('job__job_type')
        .annotate(total=Count('job__job_type'))
    )
    job_type_data = {
        'full_time': 0,
        'part_time': 0,
        'internship': 0,
    }
    for j in saved_jobs:
        job_type_data[j['job__job_type']] = j['total']

    return render(request, 'freelancer/analytics.html', {
        'status_data': status_data,
        'total_applications': total_applications,
        'months': months,
        'monthly_data': monthly_data,
        'job_type_data': job_type_data,
    })

@login_required
def recruiter_analytics(request):
    recruiter_user = request.user

    # Get all jobs posted by this recruiter
    jobs = Job.objects.filter(recruiter__user=recruiter_user)

    # 1️⃣ Applications per Job Post
    job_titles = []
    applications_count = []
    for job in jobs:
        job_titles.append(job.title)
        applications_count.append(job.applications.count())

    # 2️⃣ Job Status Overview
    job_status_data = {
        "Open": jobs.filter(status="Open").count(),
        "Closed": jobs.filter(status="Closed").count(),
        "Filled": jobs.filter(status="Filled").count()
    }
    total_jobs = sum(job_status_data.values())

    # 3️⃣ Overall Application Funnel
    funnel_stages = ["Pending", "Accepted", "Rejected"]
    funnel_counts = [
        Application.objects.filter(job__in=jobs, status="Pending").count(),
        Application.objects.filter(job__in=jobs, status="Accepted").count(),
        Application.objects.filter(job__in=jobs, status="Rejected").count()
    ]

    context = {
        "job_titles": job_titles,
        "applications_count": applications_count,
        "job_status_data": job_status_data,
        "total_jobs": total_jobs,
        "funnel_stages": funnel_stages,
        "funnel_counts": funnel_counts,
    }

    return render(request, "recruiter/analytics.html", context)


@login_required
def freelancer_discussions(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        parent_id = request.POST.get('parent_id')  # ID of comment being replied to
        if content:
            if parent_id:
                parent_comment = DiscussionComment.objects.filter(id=parent_id).first()
                DiscussionComment.objects.create(user=request.user, content=content, parent=parent_comment)
            else:
                DiscussionComment.objects.create(user=request.user, content=content)
        return redirect('freelancer_discussions')

    comments = DiscussionComment.objects.filter(parent__isnull=True).order_by('-created_at')  # top-level comments
    return render(request, 'freelancer/discussions.html', {'comments': comments})

@login_required
def recruiter_discussions(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        parent_id = request.POST.get('parent_id')  # ID of comment being replied to
        if content:
            if parent_id:
                parent_comment = DiscussionComment.objects.filter(id=parent_id).first()
                DiscussionComment.objects.create(user=request.user, content=content, parent=parent_comment)
            else:
                DiscussionComment.objects.create(user=request.user, content=content)
        return redirect('freelancer_discussions')

    comments = DiscussionComment.objects.filter(parent__isnull=True).order_by('-created_at')  # top-level comments
    return render(request, 'recruiter/discussions.html', {'comments': comments})

# aiassistant/views.py
from django.shortcuts import render
from django.http import JsonResponse
from .models import AIRequestLog
from .forms import AIRequestForm
from openai import OpenAI
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
from django.views.decorators.csrf import csrf_exempt
import pdfplumber
from docx import Document

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_pdf_text(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_docx_text(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

@csrf_exempt
@login_required
def ask_ai_resume(request):
    if request.method == "POST" and request.FILES.get("resume"):
        resume_file = request.FILES["resume"]  # <-- ADD HERE

        # Extract text based on file type
        if resume_file.name.endswith(".pdf"):
            resume_text = extract_pdf_text(resume_file)
        elif resume_file.name.endswith(".docx"):
            resume_text = extract_docx_text(resume_file)
        else:
            return JsonResponse({"reply": "Only PDF and DOCX resumes are supported."})

        # Create AI prompt
        prompt = f"Review this freelancer's resume and give a short rating (1-100) and actionable tips:\n\n{resume_text}"

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a friendly AI assistant for freelancers. Provide short, simple, actionable feedback and rate the resume from 1 to 100. Make the tone supportive and helpful."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )

        reply_text = response.choices[0].message.content

        # Log request
        AIRequestLog.objects.create(
            user=request.user,
            prompt="Resume Review",
            response=reply_text,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens
        )

        return JsonResponse({"reply": reply_text})

@csrf_exempt
@login_required
def ask_ai_api(request):
    if request.method == "POST":
        print("request came")
        data = json.loads(request.body)
        prompt = data.get("message", "")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": 
                        "You are a friendly AI assistant for freelancers. "
                        "Always give short, simple, and correct answers in 3-5 sentences. "
                        "If the user asks about the website, explain clearly how it works in a friendly tone."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )

        reply_text = response.choices[0].message.content
        usage = response.usage

        AIRequestLog.objects.create(
            user=request.user,
            prompt=prompt,
            response=reply_text,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens
        )
        print(reply_text)
        return JsonResponse({"reply": reply_text})
    

from django.db.models import Count, Q
from collections import defaultdict
import random
from datetime import datetime, timedelta

from django.db.models import Count, Q
from collections import defaultdict
import random
from datetime import datetime, timedelta

@login_required
def skill_trends(request):
    freelancer = FreelancerProfile.objects.get(user=request.user)
    
    # Get real market data from job postings
    all_jobs = Job.objects.filter(status='Open')
    
    # Enhanced trending skills with real data analysis
    trending_skills = get_enhanced_trending_skills(all_jobs)
    
    # Get freelancer's skills for comparison
    freelancer_skills = []
    if freelancer.skills:
        freelancer_skills = [skill.strip().lower() for skill in freelancer.skills.split(',')]
    
    # Enhanced categorization with better logic
    rising_skills = {}
    stable_skills = {}
    declining_skills = {}
    not_in_demand_skills = {}
    
    for skill, data in trending_skills.items():
        if data['trend'] == 'up' and data['growth'] > 15 and data['demand'] in ['high', 'medium']:
            rising_skills[skill] = data
        elif data['trend'] == 'down' or data['growth'] < 0:
            declining_skills[skill] = data
        elif data['demand'] == 'low' and data['jobs_count'] < 100:
            not_in_demand_skills[skill] = data
        else:
            stable_skills[skill] = data
    
    # Limit to top skills in each category
    rising_skills = dict(sorted(rising_skills.items(), 
                              key=lambda x: (x[1]['growth'], x[1]['jobs_count']), reverse=True)[:8])
    stable_skills = dict(sorted(stable_skills.items(), 
                              key=lambda x: x[1]['jobs_count'], reverse=True)[:8])
    declining_skills = dict(sorted(declining_skills.items(), 
                                 key=lambda x: x[1]['jobs_count'])[:6])
    not_in_demand_skills = dict(sorted(not_in_demand_skills.items(),
                                     key=lambda x: x[1]['jobs_count'])[:6])
    
    # Skills the freelancer already has
    freelancer_has_skills = {skill: trending_skills[skill] for skill in freelancer_skills if skill in trending_skills}
    
    # Recommended skills to learn (high growth skills freelancer doesn't have)
    recommended_skills = {}
    for skill, data in rising_skills.items():
        if skill not in freelancer_skills:
            recommended_skills[skill] = data
            if len(recommended_skills) >= 6:
                break
    
    # Complementary skills based on freelancer's existing skills
    complementary_skills = get_complementary_skills(freelancer_skills, trending_skills)
    
    # Skills gap analysis
    skills_gap = analyze_skills_gap(freelancer_skills, trending_skills)
    
    # Industry insights
    industry_insights = generate_industry_insights(trending_skills, freelancer_skills, not_in_demand_skills)
    
    # Market stats
    total_jobs_analyzed = all_jobs.count()
    total_skills_tracked = len(trending_skills)
    
    # Notifications
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'trending_skills': trending_skills,
        'rising_skills': rising_skills,
        'stable_skills': stable_skills,
        'declining_skills': declining_skills,
        'not_in_demand_skills': not_in_demand_skills,
        'complementary_skills': complementary_skills,
        'recommended_skills': recommended_skills,
        'skills_gap': skills_gap,
        'freelancer_has_skills': freelancer_has_skills,
        'freelancer_skills': freelancer_skills,
        'industry_insights': industry_insights,
        'total_jobs_analyzed': total_jobs_analyzed,
        'total_skills_tracked': total_skills_tracked,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    
    return render(request, 'freelancer/skill_trends.html', context)

def get_enhanced_trending_skills(all_jobs):
    """Enhanced trending skills with real market analysis including not-in-demand skills"""
    # Base sample data with more skills including declining ones
    base_trending_skills = {
        # High demand skills
        'react': {'trend': 'up', 'growth': 25, 'demand': 'high', 'jobs_count': 1500, 'avg_salary': 95000},
        'python': {'trend': 'up', 'growth': 18, 'demand': 'high', 'jobs_count': 2000, 'avg_salary': 110000},
        'node.js': {'trend': 'up', 'growth': 15, 'demand': 'medium', 'jobs_count': 1200, 'avg_salary': 105000},
        'typescript': {'trend': 'up', 'growth': 30, 'demand': 'high', 'jobs_count': 900, 'avg_salary': 100000},
        'docker': {'trend': 'up', 'growth': 22, 'demand': 'high', 'jobs_count': 1100, 'avg_salary': 115000},
        'kubernetes': {'trend': 'up', 'growth': 28, 'demand': 'high', 'jobs_count': 700, 'avg_salary': 125000},
        'aws': {'trend': 'up', 'growth': 20, 'demand': 'high', 'jobs_count': 1800, 'avg_salary': 120000},
        'machine learning': {'trend': 'up', 'growth': 35, 'demand': 'high', 'jobs_count': 600, 'avg_salary': 130000},
        'cybersecurity': {'trend': 'up', 'growth': 40, 'demand': 'high', 'jobs_count': 500, 'avg_salary': 115000},
        
        # Stable skills
        'angular': {'trend': 'stable', 'growth': 2, 'demand': 'medium', 'jobs_count': 600, 'avg_salary': 95000},
        'java': {'trend': 'stable', 'growth': 3, 'demand': 'medium', 'jobs_count': 1500, 'avg_salary': 105000},
        'sql': {'trend': 'stable', 'growth': 5, 'demand': 'high', 'jobs_count': 2200, 'avg_salary': 85000},
        'mongodb': {'trend': 'up', 'growth': 18, 'demand': 'medium', 'jobs_count': 700, 'avg_salary': 95000},
        'postgresql': {'trend': 'up', 'growth': 12, 'demand': 'medium', 'jobs_count': 600, 'avg_salary': 92000},
        
        # Declining skills
        'php': {'trend': 'down', 'growth': -5, 'demand': 'low', 'jobs_count': 400, 'avg_salary': 75000},
        'jquery': {'trend': 'down', 'growth': -15, 'demand': 'low', 'jobs_count': 200, 'avg_salary': 70000},
        'perl': {'trend': 'down', 'growth': -25, 'demand': 'low', 'jobs_count': 80, 'avg_salary': 85000},
        'ruby': {'trend': 'down', 'growth': -12, 'demand': 'low', 'jobs_count': 300, 'avg_salary': 90000},
        'actionscript': {'trend': 'down', 'growth': -40, 'demand': 'low', 'jobs_count': 50, 'avg_salary': 65000},
        
        # Not in demand skills (low job count, stable but not growing)
        'cobol': {'trend': 'stable', 'growth': 0, 'demand': 'low', 'jobs_count': 150, 'avg_salary': 95000},
        'fortran': {'trend': 'stable', 'growth': 1, 'demand': 'low', 'jobs_count': 60, 'avg_salary': 88000},
        'pascal': {'trend': 'stable', 'growth': -2, 'demand': 'low', 'jobs_count': 30, 'avg_salary': 70000},
        'visual basic': {'trend': 'down', 'growth': -20, 'demand': 'low', 'jobs_count': 120, 'avg_salary': 68000},
        'coldfusion': {'trend': 'down', 'growth': -30, 'demand': 'low', 'jobs_count': 40, 'avg_salary': 72000},
        'flash': {'trend': 'down', 'growth': -50, 'demand': 'low', 'jobs_count': 20, 'avg_salary': 60000},
        
        # Emerging but not yet in high demand
        'rust': {'trend': 'up', 'growth': 45, 'demand': 'low', 'jobs_count': 180, 'avg_salary': 115000},
        'go': {'trend': 'up', 'growth': 35, 'demand': 'medium', 'jobs_count': 400, 'avg_salary': 120000},
        'kotlin': {'trend': 'up', 'growth': 28, 'demand': 'medium', 'jobs_count': 350, 'avg_salary': 105000},
        'swift': {'trend': 'up', 'growth': 22, 'demand': 'medium', 'jobs_count': 300, 'avg_salary': 110000},
        'scala': {'trend': 'stable', 'growth': 8, 'demand': 'low', 'jobs_count': 250, 'avg_salary': 125000},
    }
    
    # Enhance with real data from job postings
    skill_analysis = {}
    for job in all_jobs:
        if job.skills_required:
            skills = [skill.strip().lower() for skill in job.skills_required.split(',') if skill.strip()]
            for skill in skills:
                if skill in skill_analysis:
                    skill_analysis[skill]['count'] += 1
                    if job.salary:
                        skill_analysis[skill]['salary_sum'] += job.salary
                        skill_analysis[skill]['salary_count'] += 1
                else:
                    skill_analysis[skill] = {
                        'count': 1,
                        'salary_sum': job.salary or 0,
                        'salary_count': 1 if job.salary else 0,
                    }
    
    # Update base data with real insights
    for skill, data in skill_analysis.items():
        if skill in base_trending_skills:
            # Update with real job count
            base_trending_skills[skill]['jobs_count'] = data['count']
            
            # Update salary if available
            if data['salary_count'] > 0:
                base_trending_skills[skill]['avg_salary'] = data['salary_sum'] // data['salary_count']
        else:
            # Add new skills found in job postings
            avg_salary = data['salary_sum'] // data['salary_count'] if data['salary_count'] > 0 else 80000
            demand = 'high' if data['count'] > 50 else 'medium' if data['count'] > 20 else 'low'
            growth = random.randint(5, 25) if demand == 'high' else random.randint(-5, 15)
            trend = 'up' if growth > 10 else 'stable' if growth >= 0 else 'down'
            
            base_trending_skills[skill] = {
                'trend': trend,
                'growth': growth,
                'demand': demand,
                'jobs_count': data['count'],
                'avg_salary': avg_salary
            }
    
    return base_trending_skills

def get_complementary_skills(freelancer_skills, trending_skills):
    """Get skills that complement existing skills"""
    skill_relationships = {
        'python': ['django', 'flask', 'machine learning', 'data analysis', 'pandas', 'fastapi'],
        'javascript': ['react', 'vue', 'angular', 'node.js', 'typescript', 'express'],
        'react': ['redux', 'next.js', 'typescript', 'graphql', 'material-ui'],
        'node.js': ['express', 'mongodb', 'postgresql', 'socket.io', 'rest api'],
        'java': ['spring', 'spring boot', 'hibernate', 'microservices'],
        'html': ['css', 'sass', 'javascript', 'responsive design'],
        'css': ['sass', 'tailwind css', 'bootstrap', 'material design'],
        'php': ['laravel', 'wordpress', 'mysql'],
        'sql': ['database design', 'postgresql', 'mysql', 'mongodb'],
        'aws': ['docker', 'kubernetes', 'terraform', 'ci/cd'],
    }
    
    complementary_skills = {}
    
    for freelancer_skill in freelancer_skills:
        if freelancer_skill in skill_relationships:
            for related_skill in skill_relationships[freelancer_skill]:
                if (related_skill in trending_skills and 
                    related_skill not in freelancer_skills and 
                    related_skill not in complementary_skills):
                    complementary_skills[related_skill] = trending_skills[related_skill]
                    if len(complementary_skills) >= 4:
                        return complementary_skills
    
    return complementary_skills

def analyze_skills_gap(freelancer_skills, trending_skills):
    """Analyze gaps in freelancer's skill set"""
    high_demand_skills = {skill: data for skill, data in trending_skills.items() 
                         if data['demand'] == 'high' and data['growth'] > 10}
    
    missing_high_demand = {}
    for skill, data in high_demand_skills.items():
        if skill not in freelancer_skills:
            missing_high_demand[skill] = data
            if len(missing_high_demand) >= 5:
                break
    
    return missing_high_demand

def generate_industry_insights(trending_skills, freelancer_skills, not_in_demand_skills):
    """Generate market insights including not-in-demand skills"""
    insights = []
    
    # Domain analysis
    domains = {
        'Web Development': ['javascript', 'react', 'vue', 'angular', 'html', 'css', 'typescript'],
        'Mobile Development': ['react native', 'flutter', 'swift', 'kotlin'],
        'Backend Development': ['python', 'node.js', 'java', 'php', 'ruby'],
        'Data Science': ['python', 'machine learning', 'data analysis', 'sql', 'pandas'],
        'DevOps': ['docker', 'kubernetes', 'aws', 'jenkins', 'ci/cd'],
        'Cloud': ['aws', 'azure', 'google cloud', 'docker'],
    }
    
    domain_scores = {}
    for domain, skills in domains.items():
        score = sum(1 for skill in skills if skill in trending_skills)
        domain_scores[domain] = score
    
    top_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)[:2]
    if top_domains:
        insights.append(f"🏆 Top Domains: {', '.join([domain for domain, _ in top_domains])}")
    
    # High growth insights
    high_growth = [skill for skill, data in trending_skills.items() 
                  if data['growth'] > 25 and data['demand'] == 'high']
    if high_growth:
        insights.append(f"🚀 Rapid Growth: {', '.join(high_growth[:2])} showing exceptional demand")
    
    # Your skills alignment
    your_high_demand = sum(1 for skill in freelancer_skills 
                          if skill in trending_skills and trending_skills[skill]['demand'] == 'high')
    total_high_demand = sum(1 for data in trending_skills.values() if data['demand'] == 'high')
    
    if total_high_demand > 0:
        alignment_percentage = (your_high_demand / total_high_demand * 100)
        insights.append(f"📊 Skills Alignment: {alignment_percentage:.1f}% with high-demand market needs")
    
    # Warning about not-in-demand skills you have
    your_not_in_demand = [skill for skill in freelancer_skills 
                         if skill in not_in_demand_skills]
    if your_not_in_demand:
        insights.append(f"⚠️ Consider Upskilling: {', '.join(your_not_in_demand[:2])} have limited opportunities")
    
    # Salary opportunities
    high_salary_skills = [skill for skill, data in trending_skills.items() 
                         if data.get('avg_salary', 0) > 100000 and skill not in freelancer_skills]
    if high_salary_skills:
        insights.append(f"💰 High Salary: {', '.join(high_salary_skills[:2])} offer premium rates")
    
    # Legacy skills warning
    legacy_skills = ['cobol', 'fortran', 'pascal', 'visual basic']
    your_legacy_skills = [skill for skill in freelancer_skills if skill in legacy_skills]
    if your_legacy_skills:
        insights.append(f"🕰️ Legacy Skills: {', '.join(your_legacy_skills)} are becoming obsolete")
    
    return insights

@login_required
def add_skill_to_profile(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            skill_to_add = data.get('skill', '').strip().lower()
            
            if not skill_to_add:
                return JsonResponse({'success': False, 'error': 'No skill provided'})
            
            freelancer = FreelancerProfile.objects.get(user=request.user)
            
            # Get current skills
            current_skills = []
            if freelancer.skills:
                current_skills = [skill.strip() for skill in freelancer.skills.split(',')]
            
            # Add new skill if not already present
            if skill_to_add not in [s.lower() for s in current_skills]:
                if current_skills:
                    current_skills.append(skill_to_add.title())
                else:
                    current_skills = [skill_to_add.title()]
                
                # Update freelancer profile
                freelancer.skills = ', '.join(current_skills)
                freelancer.save()
                
                # Create notification
                Notification.objects.create(
                    user=request.user,
                    notification_type='system',
                    message=f'Skill "{skill_to_add.title()}" added to your profile!',
                    is_read=False
                )
                
                return JsonResponse({
                    'success': True, 
                    'message': f'Skill "{skill_to_add.title()}" added successfully!',
                    'updated_skills': freelancer.skills
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'error': 'Skill already exists in your profile'
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def map(request):
    """View for the freelancer geo map"""
    freelancer = FreelancerProfile.objects.get(user=request.user)
    
    # Get all freelancers with location data
    freelancers = FreelancerProfile.objects.exclude(
        Q(location__isnull=True) | Q(location__exact='')
    )
    
    # Count stats for the map view
    total_freelancers = freelancers.count()
    available_freelancers = freelancers.filter(availability_status='available').count()
    
    # Notifications for recruiter
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'total_freelancers': total_freelancers,
        'available_freelancers': available_freelancers,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    
    return render(request, 'freelancer/map.html', context)

@login_required
def create_task(request, project_id):
    """
    Recruiter adds a new task to a project.
    """
    project = get_object_or_404(Project, id=project_id)

    # Ensure the logged-in user is the recruiter
    if project.recruiter.user != request.user:
        return redirect('dashboard')

    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        due_date = request.POST.get('due_date')
        priority = request.POST.get('priority')
        reference_file = request.FILES.get('reference_file')

        task = Task.objects.create(
            project=project,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            reference_file=reference_file
        )
        # ✅ AUTO-CREATE CHAT ROOM + SEND MESSAGE
        recruiter_user = project.recruiter.user
        freelancer_user = project.freelancer.user

        chat_room, _ = ChatRoom.objects.get_or_create(
            recruiter=recruiter_user,
            freelancer=freelancer_user
        )

        msg_content = f"📝 New Task Assigned: '{task.title}' — Please review the details and start working on it."
        Message.objects.create(chat_room=chat_room, sender=recruiter_user, content=msg_content)

        chat_room.last_message = msg_content
        chat_room.recruiter_unread_count = 0
        chat_room.freelancer_unread_count += 1
        chat_room.save()

        return redirect('project_tasks', project_id=project.id)

    return render(request, 'create_task.html', {'project': project})

@login_required
def freelancer_update_task(request, task_id):
    """
    Freelancer updates the task status or uploads deliverable.
    Returns JSON response for AJAX.
    """
    task = get_object_or_404(Task, id=task_id)

    if task.project.freelancer.user != request.user:
        return JsonResponse({'success': False, 'error': 'Not authorized'})

    if request.method == 'POST':
        file = request.FILES.get('freelancer_file')
        task_status = request.POST.get('status')

        if task_status == 'completed':
            task.status = 'completed'
            task.approval_status = 'pending'  # mark waiting for recruiter approval
        elif task_status in ['in_progress', 'pending']:
            task.status = task_status

        if file:
            task.freelancer_file = file

        task.save()

        # Return the status to display in UI
        display_status = 'Pending' if task.status == 'completed' else task.status.title()

        return JsonResponse({'success': True, 'message': 'Task updated!', 'display_status': display_status})
    
    return render(request, 'freelancer/project_tasks.html', {'task': task})

@login_required
def approve_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    # Ensure logged-in user is the recruiter
    if task.project.recruiter.user != request.user:
        return redirect('dashboard')

    if task.status == 'completed':
        task.approval_status = 'approved'
        task.status = 'completed'  # ✅ Sync status too
        task.save()

        # Add earnings to freelancer
        job_salary = task.project.job.salary or 0
        freelancer = task.project.freelancer
        freelancer.total_earnings = int(
            (freelancer.total_earnings or Decimal(0)) + (Decimal(job_salary) * Decimal('100000') / 12)
        )
        freelancer.save()

        # ✅ SEND CHAT MESSAGE: Approved
        recruiter_user = task.project.recruiter.user
        freelancer_user = task.project.freelancer.user

        chat_room, _ = ChatRoom.objects.get_or_create(
            recruiter=recruiter_user,
            freelancer=freelancer_user
        )

        msg_content = f"✅ Task Approved: Great job on '{task.title}'! Your work has been accepted."
        Message.objects.create(chat_room=chat_room, sender=recruiter_user, content=msg_content)

        chat_room.last_message = msg_content
        chat_room.recruiter_unread_count = 0
        chat_room.freelancer_unread_count += 1
        chat_room.save()

        # Check if all tasks are approved
        if task.project.is_completed():
            task.project.status = 'completed'
            task.project.save()

    return redirect('project_tasks', project_id=task.project.id)

@login_required
def disapprove_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    # Ensure logged-in user is the recruiter
    if task.project.recruiter.user != request.user:
        return redirect('dashboard')

    if task.status == 'completed':
        task.approval_status = 'disapproved'
        task.status = 'completed'  # Allow freelancer to revise
        task.save()

        task.project.status = 'active'
        task.project.save()

        # ✅ SEND CHAT MESSAGE: Disapproved
        recruiter_user = task.project.recruiter.user
        freelancer_user = task.project.freelancer.user

        chat_room, _ = ChatRoom.objects.get_or_create(
            recruiter=recruiter_user,
            freelancer=freelancer_user
        )

        msg_content = f"❌ Task Disapproved: '{task.title}' needs some revisions. Please review and re-upload."
        Message.objects.create(chat_room=chat_room, sender=recruiter_user, content=msg_content)

        chat_room.last_message = msg_content
        chat_room.recruiter_unread_count = 0
        chat_room.freelancer_unread_count += 1
        chat_room.save()

    return redirect('project_tasks', project_id=task.project.id)

@login_required
def project_tasks(request, project_id):
    """
    Show all tasks under a project for recruiter & freelancer.
    """
    project = get_object_or_404(Project, id=project_id)
    tasks = project.tasks.all()

    return render(request, 'recruiter/project_tasks.html', {
        'project': project,
        'tasks': tasks
    })

def freelancer_project_tasks(request, room_id):
    # Get the chat room
    chat_room = get_object_or_404(ChatRoom, id=room_id)

    # Ensure current user is the freelancer
    if chat_room.freelancer != request.user:
        return redirect('freelancer_dashboard')

    # Get profiles
    freelancer_profile = getattr(chat_room.freelancer, 'freelancerprofile', None)
    recruiter_profile = getattr(chat_room.recruiter, 'recruiterprofile', None)

    # Get all projects between recruiter and freelancer
    projects = Project.objects.filter(
        recruiter=recruiter_profile,
        freelancer=freelancer_profile
    )

    # Filter only those projects that have tasks assigned
    projects_with_tasks = []
    for project in projects:
        tasks = Task.objects.filter(project=project)
        if tasks.exists():  # Only include if tasks are assigned
            projects_with_tasks.append({
                'project': project,
                'tasks': tasks
            })

    context = {
        'projects_with_tasks': projects_with_tasks,
    }
    return render(request, 'freelancer/project_tasks.html', context)

@login_required
def freelancer_view_rank(request):
    freelancers = []
    current_user_freelancer = FreelancerProfile.objects.get(user=request.user)

    for freelancer in FreelancerProfile.objects.all():
        total_tasks = Task.objects.filter(project__freelancer=freelancer).count()
        approved_tasks = Task.objects.filter(project__freelancer=freelancer, approval_status='approved').count()
        completion_rate = (approved_tasks / total_tasks * 100) if total_tasks else 0

        freelancers.append({
            'profile': freelancer,
            'total_tasks': total_tasks,
            'approved_tasks': approved_tasks,
            'completion_rate': round(completion_rate, 2),
            'is_current_user': freelancer == current_user_freelancer
        })

    # Sort freelancers by completion_rate descending
    freelancers_sorted = sorted(freelancers, key=lambda x: x['completion_rate'], reverse=True)

    # Assign ranks and find current user's rank
    current_user_rank = None
    for idx, f in enumerate(freelancers_sorted, start=1):
        f['rank'] = idx
        if f['is_current_user']:
            current_user_rank = {
                'rank': idx,
                'total_tasks': f['total_tasks'],
                'approved_tasks': f['approved_tasks'],
                'completion_rate': f['completion_rate']
            }

    context = {
        'freelancers': freelancers_sorted,
        'current_user_rank': current_user_rank
    }
    return render(request, 'freelancer/view_ranks.html', context)

def recruiter_view_ranks(request):
    freelancers = []

    for freelancer in FreelancerProfile.objects.all():
        total_tasks = Task.objects.filter(project__freelancer=freelancer).count()
        approved_tasks = Task.objects.filter(project__freelancer=freelancer, approval_status='approved').count()
        completion_rate = (approved_tasks / total_tasks * 100) if total_tasks else 0

        freelancers.append({
            'profile': freelancer,
            'total_tasks': total_tasks,
            'approved_tasks': approved_tasks,
            'completion_rate': round(completion_rate, 2),  # two decimals
        })

    # Sort freelancers by completion_rate descending
    freelancers_sorted = sorted(freelancers, key=lambda x: x['completion_rate'], reverse=True)

    # Assign ranks
    for idx, f in enumerate(freelancers_sorted, start=1):
        f['rank'] = idx

    context = {'freelancers': freelancers_sorted}
    return render(request, 'recruiter/view_ranks.html', context)

@login_required
def add_testimonial(request):
    try:
        freelancer_profile = FreelancerProfile.objects.get(user=request.user)
    except FreelancerProfile.DoesNotExist:
        return redirect('home')  # only freelancers can access

    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        rating = request.POST.get('rating')

        Testimonial.objects.create(
            freelancer=freelancer_profile,
            title=title,
            message=message,
            rating=rating
        )
        return redirect('freelancer_dashboard')

    return render(request, 'freelancer/add_testimonial.html')