# users/models.py

from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # --- FIX: Define the avatar field only once ---
    # We use a default that matches the 'unknown' case in your signal
    # to maintain consistency.
    avatar = models.ImageField(
        default='default_avatars/unknown.png',
        upload_to='avatars/'
    )

    def __str__(self):
        return f'{self.user.username} Profile'