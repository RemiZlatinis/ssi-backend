import re

from django.core.files.storage import storages
from django.core.management.base import BaseCommand
from django.utils import timezone

from dbbackup_admin.models import Backup


class Command(BaseCommand):
    help = "Sync existing backup files with the database"

    def handle(self, *args, **options):
        storage = storages["dbbackup"]
        try:
            _, all_files = storage.listdir("")
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Could not list files from storage: {e}")
            )
            return

        # Filter files for database and media backups
        db_files = [f for f in all_files if f.endswith(".psql.bin")]
        media_files = [f for f in all_files if f.endswith(".tar")]

        created_count = 0
        updated_count = 0

        # Process database backups
        db_created, db_updated = self._process_backup_files(storage, db_files, "db")
        created_count += db_created
        updated_count += db_updated

        # Process media backups
        media_created, media_updated = self._process_backup_files(
            storage, media_files, "media"
        )
        created_count += media_created
        updated_count += media_updated

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete. Created: {created_count}, Updated: {updated_count}"
            )
        )

    def _process_backup_files(self, storage, files, backup_type):
        """Process backup files from storage."""
        created_count = 0
        updated_count = 0

        for filename in files:
            # Check for metadata file
            meta_filename = f"{filename}.meta"
            metadata = {}
            try:
                if storage.exists(meta_filename):
                    import json

                    with storage.open(meta_filename) as f:
                        metadata = json.load(f)
            except Exception as e:
                self.stderr.write(
                    self.style.WARNING(f"Could not read metadata for {filename}: {e}")
                )

            # Determine backup_created_at
            backup_created_at = None
            if "backup_created_at" in metadata and metadata["backup_created_at"]:
                timestamp_str = metadata["backup_created_at"]
                try:
                    backup_created_at = timezone.datetime.fromisoformat(timestamp_str)
                except ValueError:
                    pass

            if not backup_created_at:
                # Fallback to filename parsing or modification time
                if backup_type == "db":
                    match = re.match(
                        r"(.+)-(.+)-(\d{4}-\d{2}-\d{2}-\d{6})\.psql\.bin", filename
                    )
                    if match:
                        _, _, timestamp_str = match.groups()
                        timestamp = timezone.datetime.strptime(
                            timestamp_str, "%Y-%m-%d-%H%M%S"
                        )
                        backup_created_at = timezone.make_aware(timestamp)
                else:  # media backup
                    try:
                        backup_created_at = storage.get_modified_time(filename)
                    except (OSError, NotImplementedError):
                        pass

            # Get file size from storage
            try:
                file_size = storage.size(filename)
            except (OSError, NotImplementedError):
                file_size = None

            # Determine label and backup_type from metadata if available
            label = metadata.get("label", "")
            env = metadata.get("env", "")
            # If backup_type is in metadata, use it, otherwise use the passed arg
            # (though the passed arg is usually correct based on file extension
            # filtering)
            final_backup_type = metadata.get("backup_type", backup_type)

            # Check if backup already exists
            # We use file_path as the unique identifier
            backup, created = Backup.objects.update_or_create(
                file_path=filename,
                defaults={
                    "backup_type": final_backup_type,
                    "size": file_size,
                    "status": "completed",
                    "backup_created_at": backup_created_at,
                    "completed_at": timezone.now(),  # Or keep it same as created?
                    "label": label,
                    "env": env,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created backup record: {filename}")
                )
            else:
                updated_count += 1

        return created_count, updated_count
