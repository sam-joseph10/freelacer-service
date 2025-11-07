# recruiters/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import RecruiterProfile

@receiver(post_save, sender=User)
def create_or_update_recruiter_profile(sender, instance, created, **kwargs):
    """
    - Create RecruiterProfile automatically when a superuser is created.
    - Ensure an existing superuser has a profile.
    """
    if instance.is_superuser:
        profile, created = RecruiterProfile.objects.get_or_create(
            user=instance,
            defaults={"company_name": f"{instance.username}'s Company"},
        )
        if not created:
            # Optionally update details if needed
            profile.company_name = profile.company_name or f"{instance.username}'s Company"
            profile.save()

# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Application, FreelancerProfile, Badge, FreelancerBadge
from django.utils import timezone

# ---------------------------------------------
# 📩 When an application is created or accepted
# ---------------------------------------------
@receiver(post_save, sender=Application)
def update_application_and_acceptance_badges(sender, instance, **kwargs):
    freelancer = instance.freelancer
    if not freelancer:
        return

    # 1️⃣ Application-based badges (every 10 applications)
    total_apps = Application.objects.filter(freelancer=freelancer).count()
    app_level = total_apps // 10
    for level in range(1, app_level + 1):
        badge, _ = Badge.objects.get_or_create(
            badge_type='application',
            level=level,
            defaults={
                'name': f'Application Level {level}',
                'description': f'Completed {level * 10} job applications',
                'icon': 'fa-solid fa-briefcase'
            }
        )
        FreelancerBadge.objects.get_or_create(freelancer=freelancer, badge=badge)

    # 2️⃣ Acceptance-based badges (every 5 accepted jobs)
    accepted_apps = Application.objects.filter(freelancer=freelancer, status__iexact='Accepted').count()
    acc_level = accepted_apps // 5
    for level in range(1, acc_level + 1):
        badge, _ = Badge.objects.get_or_create(
            badge_type='acceptance',
            level=level,
            defaults={
                'name': f'Acceptance Level {level}',
                'description': f'{level * 5} job acceptances achieved',
                'icon': 'fa-solid fa-check-circle'
            }
        )
        FreelancerBadge.objects.get_or_create(freelancer=freelancer, badge=badge)


# ---------------------------------------------
# 👤 When freelancer updates their profile
# ---------------------------------------------
@receiver(post_save, sender=FreelancerProfile)
def update_profile_badges(sender, instance, **kwargs):
    freelancer = instance
    profile_completion = calculate_profile_completion(freelancer)

    if profile_completion == 100:
        badge, _ = Badge.objects.get_or_create(
            badge_type='profile',
            level=1,
            defaults={
                'name': 'Profile Master',
                'description': 'Profile 100% completed',
                'icon': 'fa-solid fa-user'
            }
        )
        FreelancerBadge.objects.get_or_create(freelancer=freelancer, badge=badge)


# ---------------------------------------------
# 🧮 Helper for profile completion
# ---------------------------------------------
def calculate_profile_completion(freelancer):
    fields = [
        freelancer.full_name, freelancer.professional_title, freelancer.bio,
        freelancer.skills, freelancer.experience_level, freelancer.profile_picture,
        freelancer.resume
    ]
    filled = sum(1 for field in fields if field)
    return int((filled / len(fields)) * 100)

