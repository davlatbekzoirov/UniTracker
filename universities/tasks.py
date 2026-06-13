from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_deadline_reminder(self, university_id: int):
    """
    Send a deadline reminder email for a single university.
    Called by check_upcoming_deadlines for each qualifying university.
    Retries up to 3 times on failure (e.g. SMTP timeout).
    """
    from .models import University  # local import avoids circular import at module load

    try:
        uni = University.objects.select_related('user').get(pk=university_id)
    except University.DoesNotExist:
        logger.warning(f"University {university_id} not found — skipping reminder.")
        return

    user = uni.user
    if not user.email:
        logger.info(f"User {user.username} has no email — skipping.")
        return

    days = uni.days_until_deadline
    if days is None:
        return

    subject = f"⏰ {days} days left to apply to {uni.name}"
    body = (
        f"Hi {user.username},\n\n"
        f"This is a reminder that your application deadline for:\n\n"
        f"  University : {uni.name}\n"
        f"  Program    : {uni.program}\n"
        f"  Country    : {uni.country}\n"
        f"  Deadline   : {uni.deadline}\n"
        f"  Status     : {uni.get_status_display()}\n\n"
        f"is in {days} day{'s' if days != 1 else ''}.\n\n"
        f"Log in to update your application status:\n"
        f"{settings.SITE_URL}/universities/\n\n"
        f"Good luck!\n"
        f"— UniTracker"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Reminder sent to {user.email} for {uni.name} ({days}d)")
    except Exception as exc:
        logger.error(f"Failed to send reminder for uni {university_id}: {exc}")
        raise self.retry(exc=exc)

@shared_task
def check_upcoming_deadlines():
    """
    Runs daily (scheduled via django-celery-beat).
    Finds every application whose deadline is exactly 30, 14, or 7 days away
    and dispatches a send_deadline_reminder task for each one.
    """
    from .models import University

    today = timezone.now().date()
    reminder_days = [30, 14, 7]

    reminded = 0
    for days in reminder_days:
        target = today + timezone.timedelta(days=days)
        universities = University.objects.filter(
            deadline=target,
            status__in=['preparing', 'submitted', 'interview'],  # skip accepted/rejected
        ).select_related('user')

        for uni in universities:
            send_deadline_reminder.delay(uni.pk)
            reminded += 1

    logger.info(f"check_upcoming_deadlines: queued {reminded} reminder(s) for {today}")
    return reminded

@shared_task(bind=True, max_retries=3)
def send_weekly_digest(self):
    """Runs every Monday at 08:00. Sends a personalised week-ahead summary."""
    today = timezone.now().date()
    week_end = today + timezone.timedelta(days=7)

    for user in User.objects.filter(is_active=True).select_related('test_scores'):
        try:
            _send_digest_for_user(user, today, week_end)
        except Exception as exc:
            self.retry(exc=exc, countdown=60 * 10)

def _send_digest_for_user(user, today, week_end):
    from .models import University, Document

    universities = University.objects.filter(user=user)
    if not universities.exists():
        return

    upcoming     = universities.filter(deadline__gte=today, deadline__lte=week_end).order_by('deadline')
    accepted     = universities.filter(status='accepted')
    interviews   = universities.filter(status='interview')
    in_progress  = universities.exclude(status__in=['accepted', 'rejected'])

    missing_docs = [
        u for u in in_progress
        if not u.documents.exists()
    ]

    from .models import ApplicationTask
    pending_tasks = ApplicationTask.objects.filter(
        university__user=user,
        status='pending',
        due_date__lte=week_end,
    ).select_related('university').order_by('due_date')[:10]

    if not upcoming and not pending_tasks and not missing_docs:
        return  
    subject = f"UniTracker — your week ahead ({today:%b %d})"
    body = _build_digest_body(
        user, today, upcoming, accepted, interviews, missing_docs, pending_tasks
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def _build_digest_body(user, today, upcoming, accepted, interviews, missing_docs, pending_tasks):
    lines = [
        f"Hi {user.first_name or user.username},",
        f"",
        f"Here is your UniTracker summary for the week of {today:%B %d, %Y}.",
        f"",
    ]

    if upcoming:
        lines.append(f"📅  UPCOMING DEADLINES ({len(upcoming)})")
        for u in upcoming:
            days = (u.deadline - today).days
            label = "tomorrow" if days == 1 else f"in {days} days" if days > 1 else "today"
            lines.append(f"  • {u.name} — {u.program} ({label}, {u.deadline:%b %d})")
        lines.append("")

    if interviews:
        lines.append(f"🎤  ACTIVE INTERVIEWS ({interviews.count()})")
        for u in interviews:
            lines.append(f"  • {u.name}")
        lines.append("")

    if accepted:
        lines.append(f"✅  OFFERS RECEIVED ({accepted.count()})")
        for u in accepted:
            lines.append(f"  • {u.name} — {u.program}")
        lines.append("")

    if missing_docs:
        lines.append(f"⚠️   MISSING DOCUMENTS ({len(missing_docs)})")
        for u in missing_docs:
            lines.append(f"  • {u.name} has no documents uploaded yet")
        lines.append("")

    if pending_tasks:
        lines.append(f"☑️   PENDING TASKS DUE THIS WEEK ({len(pending_tasks)})")
        for t in pending_tasks:
            due = f" — due {t.due_date:%b %d}" if t.due_date else ""
            lines.append(f"  • [{t.university.name}] {t.title}{due}")
        lines.append("")

    lines += [
        "—",
        "UniTracker · Manage your applications at http://localhost:8000",
        "To stop receiving these emails, log in and update your notification preferences.",
    ]
    return "\n".join(lines)