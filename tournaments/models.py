from django.db import models

# Create your models here.
class Tournament(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    organizer = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    region = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.region}) - {self.start_date} to {self.end_date}"