from django.shortcuts import render
def index(request): return render(request,"public/index.html")
def about(request): return render(request,"public/about.html")
def services(request): return render(request,"public/services.html")
def contact(request): return render(request,"public/contact.html")
