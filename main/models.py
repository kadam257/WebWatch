from django.db import models


class WatchParty(models.Model):
    name = models.CharField(max_length=255)
    torrent_file = models.FileField(upload_to='torrents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    host_channel_name = models.CharField(max_length=255)
    participant_count = models.IntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
