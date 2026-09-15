import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'companio.settings')
django.setup()

from django.test import Client
from accounts.models import User, Profile, ContactMessage
from volunteering.models import Skill
from assistance.models import AssistanceRequest, Feedback
from django.utils import timezone

def run_tests():
    print("--- 1. Testing Registration Flow ---")
    client = Client()
    # Create seeker user
    User.objects.filter(username="test_seeker_99").delete()
    response = client.post("/accounts/register/", {
        "username": "test_seeker_99",
        "first_name": "Test",
        "last_name": "Seeker",
        "email": "seeker99@example.com",
        "phone": "+1-555-987-6543",
        "role": "seeker",
        "password1": "ComplexPass123!",
        "password2": "ComplexPass123!",
        "accessibility_preference": "screenreader"
    })
    assert response.status_code in [200, 302], f"Unexpected status: {response.status_code}"
    u = User.objects.filter(username="test_seeker_99").first()
    assert u is not None, "User was not created!"
    assert u.phone == "+1-555-987-6543", f"Phone mismatch: {u.phone}"
    assert u.role == "seeker", f"Role mismatch: {u.role}"
    p = Profile.objects.filter(user=u).first()
    assert p is not None, "Profile was not created!"
    assert p.accessibility_preferences.get("preference") == "screenreader", f"Preferences mismatch: {p.accessibility_preferences}"
    print("[PASS] Registration successfully created user with phone and accessibility preference.")

    print("\n--- 2. Testing Volunteer Skill Management ---")
    # Create or get volunteer user
    vol, _ = User.objects.get_or_create(
        username="test_vol_99",
        defaults={"role": "volunteer", "email": "vol99@example.com"}
    )
    vol.set_password("VolPass123!")
    vol.save()
    Profile.objects.get_or_create(user=vol)

    client.force_login(vol)
    # Add skill
    Skill.objects.filter(volunteer=vol, name="Sign Language Fluency").delete()
    res = client.post("/volunteer/skills/", {
        "name": "Sign Language Fluency",
        "description": "Certified in ASL interpretation."
    })
    assert res.status_code == 302, f"Expected redirect, got {res.status_code}"
    skill = Skill.objects.filter(volunteer=vol, name="Sign Language Fluency").first()
    assert skill is not None, "Skill not saved to database!"
    assert skill.description == "Certified in ASL interpretation."
    print("[PASS] Volunteer skill added successfully.")

    # Remove skill
    res = client.post(f"/volunteer/skills/remove/{skill.id}/")
    assert res.status_code == 302, f"Expected redirect, got {res.status_code}"
    assert Skill.objects.filter(id=skill.id).count() == 0, "Skill was not deleted!"
    print("[PASS] Volunteer skill removed successfully.")

    print("\n--- 3. Testing Feedback Submission Flow ---")
    req = AssistanceRequest.objects.create(
        seeker=u,
        volunteer=vol,
        category="sign",
        title="ASL Meeting Support",
        description="Help interpreting a community townhall meeting",
        scheduled_at=timezone.now(),
        status=AssistanceRequest.Status.COMPLETED,
        completed_at=timezone.now()
    )

    client.force_login(u)
    Feedback.objects.filter(request=req).delete()
    # Test feedback submission
    res = client.post(f"/accounts/feedback/{req.id}/", {
        "rating": "5",
        "testimonial": "Incredible help during the live session!"
    })
    assert res.status_code == 302, f"Expected redirect, got {res.status_code}"
    fb = Feedback.objects.filter(request=req).first()
    assert fb is not None, "Feedback not saved to database!"
    assert fb.rating == 5, f"Rating mismatch: {fb.rating}"
    assert fb.testimonial == "Incredible help during the live session!"
    print("[PASS] Feedback submitted and stored with rating and testimonial.")

    print("\n--- 4. Testing Contact Form Submission & Model ---")
    anon_client = Client()
    ContactMessage.objects.filter(email="visitor@example.com").delete()
    res = anon_client.post("/contact/", {
        "name": "Jane Visitor",
        "email": "visitor@example.com",
        "role": "volunteer",
        "message": "I would like to inquire about partner organization volunteering opportunities."
    })
    assert res.status_code == 302, f"Expected redirect, got {res.status_code}"
    msg = ContactMessage.objects.filter(email="visitor@example.com").first()
    assert msg is not None, "Contact message not saved to database!"
    assert msg.name == "Jane Visitor"
    assert msg.role == "volunteer"
    assert "partner organization" in msg.message
    print("[PASS] Contact message successfully processed and saved to database.")

    print("\n--- 5. Testing Volunteer Dashboard Query ---")
    client.force_login(vol)
    res = client.get("/volunteer/dashboard/")
    assert res.status_code == 200, f"Volunteer dashboard returned {res.status_code}"
    print("[PASS] Volunteer dashboard loaded without errors.")

    # Cleanup test records
    u.delete()
    vol.delete()
    req.delete()
    if msg:
        msg.delete()
    print("\n==========================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
