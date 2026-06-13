from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import University, generate_tasks_for_university


@receiver(post_save, sender=University)
def create_default_tasks(sender, instance, created, **kwargs):
    """
    When a new University is created, auto-generate the default
    ApplicationTask checklist based on its university_type.

    We only run on `created=True` so editing a university later
    doesn't wipe or duplicate existing tasks.
    """
    if created:
        generate_tasks_for_university(instance)
