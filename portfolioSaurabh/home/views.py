from django.shortcuts import render, HttpResponse
from home.models import Contact

# Create your views here.
def home(request):
    # return HttpResponse("This is my Homepage (/)")
    context= {'name': 'Saurabh', 'course': 'Django'}
    return render(request,'home.html', context)

def about(request):
    # return HttpResponse("This is my About page (/about)")
    return render(request,'about.html')

def projects(request):
    # return HttpResponse("This is my Projects page (/projects)")
    return render(request,'projects.html')

def contact(request):
    if request.method == "POST":

        name = request.POST['name']
        email = request.POST['email']
        desc = request.POST['desc']
        #print(name, email, desc)
        contact = Contact(name=name, email=email, desc=desc)
        contact.save()
        print("The data has been written to the DB")


    # return HttpResponse("This is my Contact page (/contact)")
    return render(request,'contact.html')
