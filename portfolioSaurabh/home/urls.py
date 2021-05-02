from django.contrib import admin
from django.urls import path
from home import views

#Django admin header customization
admin.site.site_header = "Log In To Developer Saurabh"
admin.site.site_title = "Welcome to Saurabh's Dashboard"
admin.site.index_title = "Welcome to this Admin Portal"
urlpatterns = [
    path('', views.home, name='home'),
    path('about', views.about, name='about'),
    path('projects', views.projects, name='projects'),
    path('contact', views.contact, name='contact')
]
 