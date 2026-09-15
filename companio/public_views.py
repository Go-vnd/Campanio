from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.models import ContactMessage

def index(request): return render(request, "public/index.html")
def about(request): return render(request, "public/about.html")
def services(request): return render(request, "public/services.html")

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        role = request.POST.get("role", "").strip()
        message_text = request.POST.get("message", "").strip()
        
        if name and email and message_text:
            ContactMessage.objects.create(
                name=name,
                email=email,
                role=role,
                message=message_text
            )
            messages.success(request, "Thank you! Your message has been sent successfully. Our support team will reach out soon.")
            return redirect("contact")
        else:
            messages.error(request, "Please fill in all required fields (Name, Email, and Message).")
    
    return render(request, "public/contact.html")

