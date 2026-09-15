import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'companio.settings')
django.setup()

from django.test import Client
from django.utils import timezone
from accounts.models import User, Profile, ContactMessage
from assistance.models import AssistanceRequest, Feedback
from volunteering.models import Skill
from rewards.models import Badge, BadgeAward, Certificate

def run_tests():
    print("=== Testing Admin Control Panel & Features ===")
    client = Client()

    # 1. Setup Admin user
    admin_user, _ = User.objects.get_or_create(
        username="test_superadmin",
        defaults={"role": "admin", "is_staff": True, "is_superuser": True, "email": "admin@example.com"}
    )
    admin_user.set_password("AdminPass123!")
    admin_user.role = "admin"
    admin_user.is_staff = True
    admin_user.save()
    client.force_login(admin_user)

    # 2. Setup test seeker and volunteer
    seeker, _ = User.objects.get_or_create(
        username="admin_test_seeker",
        defaults={"role": "seeker", "email": "seeker_test@example.com", "first_name": "Sam", "last_name": "Seeker"}
    )
    seeker.role = "seeker"
    seeker.save()
    Profile.objects.get_or_create(user=seeker, defaults={"accessibility_preferences": {"preference": "screenreader"}})

    vol, _ = User.objects.get_or_create(
        username="admin_test_vol",
        defaults={"role": "volunteer", "email": "vol_test@example.com", "first_name": "Valerie", "last_name": "Volunteer", "is_verified": False}
    )
    vol.role = "volunteer"
    vol.is_verified = False
    vol.save()
    vol_profile, _ = Profile.objects.get_or_create(user=vol, defaults={"background_verified": False})
    vol_profile.background_verified = False
    vol_profile.save()

    test_skill, _ = Skill.objects.get_or_create(
        volunteer=vol,
        name="Admin Test Skill",
        defaults={"description": "Testing admin approval", "verified": False}
    )

    print("\n[1] Testing Admin Dashboard & Verification Queue...")
    res = client.get("/admin/")
    assert res.status_code == 200, f"Dashboard failed with {res.status_code}"
    assert b"Volunteer Identity &amp; Skill Verification Queue" in res.content or b"Volunteer Identity & Skill Verification Queue" in res.content

    # Test approve volunteer
    res = client.post("/admin/", {"action": "approve_volunteer", "target_id": vol.id})
    assert res.status_code == 302
    vol.refresh_from_db()
    vol_profile.refresh_from_db()
    assert vol.is_verified is True, "Volunteer not marked as verified!"
    assert vol_profile.background_verified is True, "Background verified not True!"
    print("  [PASS] Volunteer approval successfully updated database.")

    # Test approve skill
    res = client.post("/admin/", {"action": "approve_skill", "target_id": test_skill.id})
    assert res.status_code == 302
    test_skill.refresh_from_db()
    assert test_skill.verified is True, "Skill not marked as verified!"
    print("  [PASS] Skill verification successfully approved.")

    print("\n[2] Testing User Management, Search, Filter, Toggle, and CSV Export...")
    # Search
    res = client.get("/admin/users/?q=Sam")
    assert res.status_code == 200
    assert b"Sam" in res.content
    print("  [PASS] User search returned matching user.")

    # CSV export
    res = client.get("/admin/users/export/")
    assert res.status_code == 200
    assert res["Content-Type"] == "text/csv"
    assert b"Sam" in res.content
    print("  [PASS] CSV export generated valid file response.")

    # Toggle suspend / activate
    res = client.post(f"/admin/users/toggle/{seeker.id}/")
    assert res.status_code == 302
    seeker.refresh_from_db()
    assert seeker.is_active is False, "User was not suspended!"
    # Toggle back to active
    client.post(f"/admin/users/toggle/{seeker.id}/")
    seeker.refresh_from_db()
    assert seeker.is_active is True, "User was not re-activated!"
    print("  [PASS] User active status toggle functional.")

    print("\n[3] Testing Volunteer Management, Verification Toggle, & Certificates...")
    res = client.get("/admin/volunteers/?q=Valerie")
    assert res.status_code == 200
    assert b"Valerie" in res.content

    # Toggle verification
    res = client.post(f"/admin/volunteers/verify/{vol.id}/")
    assert res.status_code == 302
    vol.refresh_from_db()
    assert vol.is_verified is False

    # Issue Certificate
    res = client.post(f"/admin/volunteers/certificate/{vol.id}/", {
        "title": "Outstanding ASL Contributor",
        "hours": "25"
    })
    assert res.status_code == 302
    cert = Certificate.objects.filter(volunteer=vol, title="Outstanding ASL Contributor").first()
    assert cert is not None, "Certificate not created!"
    assert cert.hours_recognized == 25
    print("  [PASS] Digital certificate created and issued to volunteer.")

    # Award Badge to volunteer
    test_badge, _ = Badge.objects.get_or_create(title="Admin Test Badge", defaults={"criteria": "Admin criteria"})
    res = client.post(f"/admin/volunteers/award/{vol.id}/", {"badge_id": test_badge.id})
    assert res.status_code == 302
    award = BadgeAward.objects.filter(volunteer=vol, badge=test_badge).first()
    assert award is not None, "BadgeAward not created!"
    print("  [PASS] Badge award granted to volunteer.")

    print("\n[4] Testing Request Management & Volunteer Assignment...")
    req = AssistanceRequest.objects.create(
        seeker=seeker,
        category="tech",
        title="Admin Test Tech Assistance",
        description="Setting up screen reader software",
        scheduled_at=timezone.now(),
        priority="urgent",
        status="pending"
    )

    res = client.get("/admin/requests/?priority=urgent")
    assert res.status_code == 200
    assert b"Admin Test Tech Assistance" in res.content

    # Assign volunteer and set in_progress
    res = client.post(f"/admin/requests/assign/{req.id}/", {
        "volunteer_id": vol.id,
        "status": "in_progress"
    })
    assert res.status_code == 302
    req.refresh_from_db()
    assert req.volunteer == vol, "Volunteer was not assigned!"
    assert req.status == "in_progress", f"Status not updated: {req.status}"
    print("  [PASS] Request volunteer assignment and status change successful.")

    print("\n[5] Testing Badge Management...")
    res = client.post("/admin/badges/", {
        "action": "create",
        "title": "Community Champion",
        "criteria": "Completed 50 hours of verified assistance"
    })
    assert res.status_code == 302
    new_badge = Badge.objects.filter(title="Community Champion").first()
    assert new_badge is not None, "Badge not created!"

    # Toggle active
    client.post("/admin/badges/", {"action": "toggle", "badge_id": new_badge.id})
    new_badge.refresh_from_db()
    assert new_badge.active is False
    print("  [PASS] Badge creation and status toggling successful.")

    print("\n[6] Testing Support Messages in Admin...")
    msg = ContactMessage.objects.create(
        name="Test Contact User",
        email="contact@example.com",
        role="organization",
        message="Inquiry regarding wheelchair access partnership",
        is_resolved=False
    )
    res = client.get("/admin/messages/?status=pending")
    assert res.status_code == 200
    assert b"wheelchair access partnership" in res.content

    # Toggle resolve
    client.post("/admin/messages/", {"message_id": msg.id, "action": "toggle_resolve"})
    msg.refresh_from_db()
    assert msg.is_resolved is True, "ContactMessage not marked as resolved!"
    print("  [PASS] Contact inquiry resolution functional.")

    # Cleanup
    admin_user.delete()
    seeker.delete()
    vol.delete()
    test_badge.delete()
    new_badge.delete()
    msg.delete()

    print("\n================================================")
    print("ALL ADMIN FEATURES TESTED AND WORKING 100%!")
    print("================================================")

if __name__ == "__main__":
    run_tests()
