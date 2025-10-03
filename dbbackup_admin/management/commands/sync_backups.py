import glob
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from dbbackup_admin.models import Backup


class Command(BaseCommand):
    help = "Sync existing backup files with the database"

    def handle(self, *args, **options):
        try:
            backup_dir = settings.STORAGES["dbbackup"]["OPTIONS"]["location"]
        except KeyError:
            self.stderr.write(
                self.style.ERROR(
                    "Missing required setting: STORAGES['dbbackup']['OPTIONS']"
                    "['location']"
                )
            )
            return

        # Look for database backup files
        db_pattern = os.path.join(backup_dir, "*.psql.bin")
        media_pattern = os.path.join(backup_dir, "*.tar")

        created_count = 0
        updated_count = 0

        # Process database backups
        db_created, db_updated = self._process_backup_files(db_pattern, "db")
        created_count += db_created
        updated_count += db_updated

        # Process media backups
        media_created, media_updated = self._process_backup_files(
            media_pattern, "media"
        )
        created_count += media_created
        updated_count += media_updated

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete. Created: {created_count}, Updated: {updated_count}"
            )
        )

    def _process_backup_files(self, pattern, backup_type):
        """Process backup files matching the given pattern."""
        created_count = 0
        updated_count = 0

        for file_path in glob.glob(pattern):
            filename = os.path.basename(file_path)

            # Parse filename to extract information
            # Expected format for db: {database}-{hash}-{timestamp}.psql.bin
            # Expected format for media: {timestamp}.tar
            if backup_type == "db":
                match = re.match(
                    r"(.+)-(.+)-(\d{4}-\d{2}-\d{2}-\d{6})\.psql\.bin", filename
                )
                if match:
                    database_name, hash_part, timestamp_str = match.groups()

                    # Parse timestamp
                    timestamp = timezone.datetime.strptime(
                        timestamp_str, "%Y-%m-%d-%H%M%S"
                    )
                    timestamp = timezone.make_aware(timestamp)

                    # Get file size
                    file_size = os.path.getsize(file_path)

                    # Check if backup already exists
                    backup, created = Backup.objects.get_or_create(
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
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Updated backup record: {filename}")
                        )
            else:  # media backup
                try:
                    # For media backups, we'll use the file modification time
                    mod_time = os.path.getmtime(file_path)
                    timestamp = timezone.datetime.fromtimestamp(mod_time)
                    timestamp = timezone.make_aware(timestamp)

                    # Get file size
                    file_size = os.path.getsize(file_path)
                except OSError as e:
                    self.stderr.write(
                        self.style.WARNING(f"Error processing {filename}: {e}")
                    )
                    continue

                # Check if backup already exists
                backup, created = Backup.objects.get_or_create(
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
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Updated backup record: {filename}")
                    )
        return created_count, updated_count
