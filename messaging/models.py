from django.db import models

class Contact(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Message(models.Model):
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)