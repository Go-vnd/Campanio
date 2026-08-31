<<<<<<< HEAD
# Campanio
Campanio - The Volunteer Skill Exchange Platform is a web-based application that connects people with disabilities with volunteers who are willing to provide assistance. Users with disabilities can request help for tasks such as grocery shopping, transportation, filling out government forms, reading documents, technology support, or companionship
=======
# Companio Django Backend Starter

This backend scaffold connects the supplied Companio HTML/CSS/JS frontend to Django.

## Implemented foundation
- Role-based authentication: assistance seeker, volunteer, admin
- User profiles and accessibility preferences
- Assistance requests
- Volunteer skills and availability
- Request matching/acceptance
- Ratings and feedback
- Badges and certificates
- Notifications
- WebSocket chat with Django Channels
- Admin-ready Django models and routes

## Setup

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

For WebSocket support:

```bash
daphne -b 127.0.0.1 -p 8000 companio.asgi:application
```

The frontend templates should be moved into Django `templates/` folders and their static assets into `static/`.

This is a working foundation, not a production deployment. Before deployment, configure a real database, secret key, HTTPS, secure cookies, email, object storage, and a production ASGI/Redis setup.
>>>>>>> pages-linked
