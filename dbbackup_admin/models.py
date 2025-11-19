from django.core.files.storage import storages
from django.db import models


class Backup(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    backup_type = models.CharField(
        max_length=10, choices=[("db", "Database"), ("media", "Media")]
    )
    file_path = models.CharField(max_length=255, blank=True)
    label = models.CharField(max_length=255, blank=True, default="")
    env = models.CharField(max_length=50, blank=True, default="")
    size = models.PositiveIntegerField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    record_created_at = models.DateTimeField(auto_now_add=True)
    backup_created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-backup_created_at"]

    def __str__(self):
        return f"{self.backup_type} backup - {self.backup_created_at}"

    def get_size_display(self):
        if self.size is None:
            return "Unknown"
        size = float(self.size)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def file_exists(self):
        """Check if the backup file still exists in storage."""
        if not self.file_path:
            return False
        try:
            return storages["dbbackup"].exists(self.file_path)
        except Exception:
            return False

    def delete(self, *args, **kwargs):
        """
        Override delete to rename the file in storage instead of deleting it.
        """
        if self.file_path:
            try:
                storage = storages["dbbackup"]

                def rename_file(old_name, new_name):
                    if storage.exists(old_name):
                        # Try to use move if available (some backends might support it)
                        # Otherwise copy and delete
                        try:
                            # Open the old file
                            with storage.open(old_name) as f:
                                # Save to new location
                                storage.save(new_name, f)
                            # Delete old file
                            storage.delete(old_name)
                        except Exception as e:
                            import logging

                            logger = logging.getLogger("dbbackup_admin")
                            logger.warning(
                                f"Failed to rename {old_name} to {new_name}: {e}"
                            )

                # Rename backup file
                rename_file(self.file_path, f"{self.file_path}.deleted")

                # Rename metadata file
                rename_file(f"{self.file_path}.meta", f"{self.file_path}.meta.deleted")

            except Exception as e:
                import logging

                logger = logging.getLogger("dbbackup_admin")
                logger.warning(
                    f"Failed to process file deletion for backup {self.id}: {e}"
                )

        super().delete(*args, **kwargs)
