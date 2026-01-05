from typing import Any

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Check if the database is available"

    def handle(self, *args: Any, **options: Any) -> None:
        db_conn = connections["default"]
        try:
            db_conn.cursor()
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f"Database unavailable: {e}"))
            exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("Database available"))
