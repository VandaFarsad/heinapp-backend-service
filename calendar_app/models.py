from django.db import models


class CalendarEvent(models.Model):
    uid = models.CharField(max_length=255, db_index=True)
    recurrence_id = models.CharField(max_length=255, blank=True, null=True)  # For recurring events
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=500, blank=True)  # For meeting links
    rrule = models.TextField(blank=True, null=True)  # RFC 5545 recurrence rule
    exdate = models.TextField(blank=True, null=True)  # Exception dates (comma-separated ISO strings)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)  # Set during CalDAV sync

    class Meta:
        ordering = ["start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["uid", "recurrence_id"],
                name="unique_uid_recurrence",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(fields=["start_date", "end_date"], name="idx_event_date_range"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.start_date} - {self.end_date})"
