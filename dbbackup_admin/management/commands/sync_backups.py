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
            # Parse filename to extract information
            # Expected format for db: {database}-{hash}-{timestamp}.psql.bin
            # Expected format for media: {timestamp}.tar
            if backup_type == "db":
                match = re.match(
                    r"(.+)-(.+)-(\d{4}-\d{2}-\d{2}-\d{6})\.psql\.bin", filename
                )
                if match:
                    _, _, timestamp_str = match.groups()

                    # Parse timestamp
                    timestamp = timezone.datetime.strptime(
                        timestamp_str, "%Y-%m-%d-%H%M%S"
                    )
                    timestamp = timezone.make_aware(timestamp)

                    # Get file size from storage
                    file_size = storage.size(filename)

                    # Check if backup already exists
                    _, created = Backup.objects.get_or_create(
                        file_path=filename,
                        defaults={
                            "backup_type": backup_type,
                            "size": file_size,
                            "status": "completed",
                            "created_at": timestamp,
                            "completed_at": timestamp,
                        },
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Created backup record: {filename}")
                        )
                    else:
                        # If you want to update existing records, add logic here
                        updated_count += 1
            else:  # media backup
                try:
                    # For media backups, use the file modification time from storage
                    timestamp = storage.get_modified_time(filename)

                    # Get file size from storage
                    file_size = storage.size(filename)
                except (OSError, NotImplementedError) as e:
                    self.stderr.write(
                        self.style.WARNING(f"Error processing {filename}: {e}")
                    )
                    continue

                # Check if backup already exists
                _, created = Backup.objects.get_or_create(
                    file_path=filename,
                    defaults={
                        "backup_type": backup_type,
                        "size": file_size,
                        "status": "completed",
                        "created_at": timestamp,
                        "completed_at": timestamp,
                    },
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Created backup record: {filename}")
                    )
                else:
                    # If you want to update existing records, add logic here
                    updated_count += 1
        return created_count, updated_count
