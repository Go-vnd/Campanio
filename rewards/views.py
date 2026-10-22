from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from .models import Certificate
import io


def _generate_certificate_pdf(user, cert):
    """Generate a PDF certificate using ReportLab."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph

    buffer = io.BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    # Background gradient simulation using rectangles
    c.setFillColor(colors.HexColor('#0d0f1a'))
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # Decorative border
    c.setStrokeColor(colors.HexColor('#7c3aed'))
    c.setLineWidth(3)
    c.rect(30, 30, width - 60, height - 60, fill=False, stroke=True)
    c.setStrokeColor(colors.HexColor('#3b82f6'))
    c.setLineWidth(1)
    c.rect(38, 38, width - 76, height - 76, fill=False, stroke=True)

    # Corner decorations
    corner_size = 20
    for x, y in [(30, 30), (width-30, 30), (30, height-30), (width-30, height-30)]:
        c.setFillColor(colors.HexColor('#7c3aed'))
        c.circle(x, y, 5, fill=True, stroke=False)

    # Header — Companio logo
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor('#94a3b8'))
    c.drawCentredString(width / 2, height - 70, "🤝  COMPANIO — Volunteer Skill Exchange Platform")

    # Divider
    c.setStrokeColor(colors.HexColor('#7c3aed'))
    c.setLineWidth(1)
    c.line(80, height - 85, width - 80, height - 85)

    # Certificate of Achievement header
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(colors.HexColor('#f1f5f9'))
    c.drawCentredString(width / 2, height - 140, "Certificate of Achievement")

    # Presented to
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor('#94a3b8'))
    c.drawCentredString(width / 2, height - 175, "This certificate is proudly presented to")

    # Recipient name
    full_name = user.get_full_name() or user.username
    c.setFont("Helvetica-BoldOblique", 42)
    c.setFillColor(colors.HexColor('#a78bfa'))
    c.drawCentredString(width / 2, height - 225, full_name)

    # Award title line
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor('#94a3b8'))
    c.drawCentredString(width / 2, height - 265, "in recognition of outstanding volunteer contributions and earning the award:")

    # Certificate title
    c.setFont("Helvetica-Bold", 28)
    # Color based on tier
    if 'Gold' in cert.title:
        title_color = colors.HexColor('#fbbf24')
    elif 'Silver' in cert.title:
        title_color = colors.HexColor('#cbd5e1')
    else:
        title_color = colors.HexColor('#f59e0b')
    c.setFillColor(title_color)
    c.drawCentredString(width / 2, height - 310, cert.title)

    # Divider
    c.setStrokeColor(colors.HexColor('#7c3aed'))
    c.setLineWidth(0.5)
    c.line(width/2 - 150, height - 335, width/2 + 150, height - 335)

    # Date issued
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor('#64748b'))
    c.drawCentredString(width / 2, height - 360, f"Issued on: {cert.issue_date.strftime('%B %d, %Y')}")

    # Bottom signature lines
    sig_y = 80
    c.setStrokeColor(colors.HexColor('#334155'))
    c.setLineWidth(1)
    c.line(100, sig_y, 260, sig_y)
    c.line(width - 260, sig_y, width - 100, sig_y)

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor('#64748b'))
    c.drawCentredString(180, sig_y - 15, "Platform Director")
    c.drawCentredString(width - 180, sig_y - 15, "Volunteer Coordinator")

    c.save()
    buffer.seek(0)
    return buffer


@login_required
def rewards_view(request):
    try:
        profile = request.user.volunteer_profile
    except Exception:
        profile = None

    certs = Certificate.objects.filter(user=request.user).order_by('-issue_date')

    # Tier thresholds
    points = profile.points if profile else 0
    tiers = [
        {'name': 'Bronze', 'threshold': 50,  'icon': '🥉', 'color': 'bronze', 'title': 'Bronze Certificate of Participation'},
        {'name': 'Silver', 'threshold': 100, 'icon': '🥈', 'color': 'silver', 'title': 'Silver Certificate of Achievement'},
        {'name': 'Gold',   'threshold': 200, 'icon': '🥇', 'color': 'gold',   'title': 'Gold Certificate of Excellence'},
    ]
    for tier in tiers:
        tier['earned'] = points >= tier['threshold']
        tier['cert'] = certs.filter(title=tier['title']).first()

    return render(request, 'rewards/rewards.html', {
        'profile': profile,
        'certificates': certs,
        'tiers': tiers,
        'points': points,
    })


@login_required
def download_certificate(request, pk):
    cert = get_object_or_404(Certificate, pk=pk, user=request.user)

    try:
        pdf_buffer = _generate_certificate_pdf(request.user, cert)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        safe_title = cert.title.replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="Companio_{safe_title}.pdf"'
        return response
    except Exception as e:
        from django.contrib import messages
        messages.error(request, f'Could not generate PDF: {e}')
        return HttpResponse(f'Error generating PDF: {e}', status=500)
