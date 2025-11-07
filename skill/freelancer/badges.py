# badges.py
from django.utils import timezone
from datetime import timedelta
from .models import Badge, UserBadge, Application, FreelancerProfile

class BadgeManager:
    @staticmethod
    def award_badge(user, badge_name):
        """Award a badge to a user if they haven't earned it already"""
        try:
            badge = Badge.objects.get(name=badge_name)
            user_badge, created = UserBadge.objects.get_or_create(
                user=user, 
                badge=badge
            )
            if created:
                # Create notification for the user
                from .models import Notification
                Notification.objects.create(
                    user=user,
                    notification_type='system',
                    message=f"🎉 Congratulations! You earned the '{badge.name}' badge!",
                )
                return True
        except Badge.objects.DoesNotExist:
            pass
        return False

    @staticmethod
    def check_application_badges(user):
        """Check and award badges related to job applications"""
        freelancer_profile = FreelancerProfile.objects.get(user=user)
        applications_count = Application.objects.filter(freelancer=freelancer_profile).count()
        accepted_count = Application.objects.filter(freelancer=freelancer_profile, status='Accepted').count()
        
        # First Application badge
        if applications_count >= 1:
            BadgeManager.award_badge(user, "First Step")
        
        # Prolific Applicant badges
        if applications_count >= 5:
            BadgeManager.award_badge(user, "Job Hunter")
        if applications_count >= 10:
            BadgeManager.award_badge(user, "Application Master")
        if applications_count >= 25:
            BadgeManager.award_badge(user, "Submission Pro")
            
        # Success badges
        if accepted_count >= 1:
            BadgeManager.award_badge(user, "First Success")
        if accepted_count >= 3:
            BadgeManager.award_badge(user, "Proven Talent")
        if accepted_count >= 10:
            BadgeManager.award_badge(user, "Highly Sought After")

    @staticmethod
    def check_profile_badges(user):
        """Check and award badges related to profile completion"""
        try:
            profile = FreelancerProfile.objects.get(user=user)
            
            # Calculate profile completion
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
            completion_percentage = int((completed_fields / len(fields_to_check)) * 100)
            
            # Profile completion badges
            if completion_percentage >= 50:
                BadgeManager.award_badge(user, "Profile Builder")
            if completion_percentage >= 80:
                BadgeManager.award_badge(user, "Profile Perfectionist")
            if completion_percentage >= 95:
                BadgeManager.award_badge(user, "All-Star Profile")
                
            # Skill-based badges
            if profile.skills:
                skills_count = len([skill.strip() for skill in profile.skills.split(",") if skill.strip()])
                if skills_count >= 3:
                    BadgeManager.award_badge(user, "Skill Collector")
                if skills_count >= 8:
                    BadgeManager.award_badge(user, "Versatile Expert")
                    
        except FreelancerProfile.DoesNotExist:
            pass

    @staticmethod
    def check_login_badges(user):
        """Check and award badges related to login activity"""
        # This would typically check login history
        # For now, we'll award based on account age
        account_age = timezone.now() - user.date_joined
        if account_age >= timedelta(days=7):
            BadgeManager.award_badge(user, "Week Warrior")
        if account_age >= timedelta(days=30):
            BadgeManager.award_badge(user, "Monthly Regular")
        if account_age >= timedelta(days=90):
            BadgeManager.award_badge(user, "Seasoned Member")

    @staticmethod
    def check_all_badges(user):
        """Check all badge conditions for a user"""
        BadgeManager.check_application_badges(user)
        BadgeManager.check_profile_badges(user)
        BadgeManager.check_login_badges(user)