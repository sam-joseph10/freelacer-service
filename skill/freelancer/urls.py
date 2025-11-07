from django.urls import path
from .views import *

urlpatterns =[

    path('', home, name="home"),
    path("login/", login_page, name="login"),
    path('logout/',logout_view, name='logout'),
    path("register/", register, name="register"),
    path("freelancer/dashboard/", freelancer_dashboard, name="freelancer_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    
    # MAP URLS
    path("freelancer-map/", freelancer_map, name="freelancer_map"),
    path('api/candidate-location/<int:freelancer_id>/', get_candidate_location, name='get_candidate_location'), 
    path("api/freelancers/", get_freelancer_data, name="get_freelancer_data"),   
    path("profile/view/", view_profile, name="view_profile"),
    path("profile/edit/", edit_profile, name="edit_profile"),
    path("profile/create/", create_profile, name="create_profile"),
    path("profile/upload-certificate/", upload_certificate, name="upload_certificate"),

    path('post/edit/<int:post_id>/', edit_post, name='edit_post'),
    path('post/delete/<int:post_id>/', delete_post, name='delete_post'),
    
    path('post-job/',post_job, name='post_job'),
    path('my-jobs/', my_jobs, name='my_jobs'),
    path('applications/<int:job_id>/', view_applications, name='view_applications'),
    path('profile/', recruiter_profile, name='recruiter_profile'),
    path('job/<int:job_id>/close/',close_job, name='close_job'),
    path('job/<int:job_id>/edit/', edit_job, name='edit_job'),
    path('job/<int:job_id>/applications/', view_applications, name='view_job'),
    path('application/<int:app_id>/status/<str:status>/', update_application_status, name='update_application_status'),
    path('freelancer/<int:freelancer_id>/', view_freelancer_profile, name='view_freelancer_profile'),
    path('freelancer/jobs/', jobs_page, name='jobs_page'),
    path('freelancer/jobs/<int:job_id>/apply/', apply_job, name='apply_job'),
    path('freelancer/applications/', freelancer_applications, name='freelancer_applications'),
    path('jobs/save/<int:job_id>/', toggle_save_job, name='toggle_save_job'),
    path('freelancer/saved-jobs/', saved_jobs_page, name='saved_jobs'),
    path('internships/', internship_page, name='internship_page'),
    path('freelancer-message',freelancer_messages,name='freelancer_message'),
    path('recruiter-message',recruiter_messages,name='recruiter_message'),
    path('notifications/<int:notification_id>/mark-read/', mark_notification_read, name='mark_notification_read'),
    # Add these URL patterns
    path('notifications/<int:notification_id>/mark-read/', mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/', view_all_notifications, name='view_all_notifications'),
    path('freelancer/analytics/', freelancer_analytics, name='freelancer_analytics'),
    path("analytics/", recruiter_analytics, name="recruiter_analytics"),
    path('freelancer_discussions/',freelancer_discussions,name="freelancer_discussions"),
    path('recruiter_discussions/',recruiter_discussions,name="recruiter_discussions"),
    path('ask-ai/', ask_ai_api, name='ask_ai_api'),
    path('ask-ai-resume/', ask_ai_resume, name='ask_ai_resume'),
    path('skill-trends/', skill_trends, name='skill_trends'),
    path('add-skill-to-profile/', add_skill_to_profile, name='add_skill_to_profile'),
    path("map/", map, name="map"),

    # ----------------------------
    # Project & Task Management
    # ----------------------------

    # List all tasks in a project
    path('project/<int:project_id>/tasks/', project_tasks, name='project_tasks'),

    # Recruiter: Create a new task
    path('project/<int:project_id>/tasks/create/', create_task, name='create_task'),

    # Freelancer: Update a task (status + upload ZIP)
    path('task/<int:task_id>/update/', freelancer_update_task, name='freelancer_update_task'),

    # Recruiter: Approve a task
    path('task/<int:task_id>/approve/', approve_task, name='approve_task'),

    path('task/<int:task_id>/disapprove/', disapprove_task, name='disapprove_task'),

    path('freelancer/tasks/<int:room_id>/', freelancer_project_tasks, name='freelancer_project_tasks'),

    path('freelancer/view-rank/',freelancer_view_rank,name="freelancer_view_rank"),

    path('recruiter/view-rank/',recruiter_view_ranks,name="recruiter_view_rank"),

    path('add-testimonial/', add_testimonial, name='add_testimonial'),
]