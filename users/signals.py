# users/signals.py

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile
from .utils import get_gender_from_name

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    # This signal runs when a User object is saved.
    if created:
        # Determine gender from the first name provided during registration.
        if instance.first_name and instance.first_name.strip():
            gender = get_gender_from_name(instance.first_name)
        else:
            gender = 'unknown'

        # Select the appropriate default avatar.
        if gender == 'male':
            avatar_path = 'default_avatars/male.png'
        elif gender == 'female':
            avatar_path = 'default_avatars/female.png'
        else:
            avatar_path = 'default_avatars/unknown.png'

        # Create the profile for the new user with the determined avatar.
        Profile.objects.create(user=instance, avatar=avatar_path)

# You can also add a signal to save the profile when the user is saved,
# though it's not strictly necessary for this fix.
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # This ensures that if a user has a profile, it gets saved.
    # It's good practice but not the source of your error.
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        # A profile will be created by the `create_user_profile` signal on creation
        # or by the `profile_view` on first access.
        pass