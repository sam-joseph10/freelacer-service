'''from decimal import Decimal
from freelancer.models import FreelancerProfile, Project, Task

# Step 1: Reset all freelancer earnings
FreelancerProfile.objects.update(total_earnings=0)
print("All freelancer earnings have been reset to zero.")

# Step 2: Backfill earnings
for profile in FreelancerProfile.objects.all():
    total_earning = Decimal('0')

    # Get all projects of this freelancer
    projects = Project.objects.filter(freelancer=profile)

    for project in projects:
        # Skip if no job or no salary
        if not project.job or not project.job.salary:
            continue

        job_salary_lpa = project.job.salary  # Salary in LPA

        # Get approved tasks in this project
        approved_tasks = project.tasks.filter(approval_status='approved')
        #print(Decimal(job_salary_lpa) * Decimal('100000'))
        # Each approved task earns 1/12th of yearly salary (convert LPA → INR)
        total_earning += approved_tasks.count() * (Decimal(job_salary_lpa) * Decimal('100000') / Decimal('12'))

    # Update freelancer profile
    profile.total_earnings = int(total_earning)
    profile.save()

    print(f"{profile.full_name}: Total Earnings = {profile.total_earnings} INR")
'''
from freelancer.models import FreelancerProfile, Task
from django.db.models import Count, Q, F

freelancers = FreelancerProfile.objects.all()

for freelancer in freelancers:
    total_tasks = Task.objects.filter(project__freelancer=freelancer).count()
    approved_tasks = Task.objects.filter(project__freelancer=freelancer, approval_status='approved').count()

    completion_rate = (approved_tasks / total_tasks * 100) if total_tasks else 0
    freelancer.task_completion_rate = round(completion_rate, 0)  # Round to integer
    freelancer.save()

freelancers = FreelancerProfile.objects.order_by('-task_completion_rate')

for position, freelancer in enumerate(freelancers, start=1):
    freelancer.rank_position = position
    freelancer.save()

