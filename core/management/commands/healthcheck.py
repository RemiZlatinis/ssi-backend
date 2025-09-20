from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Check if the database is available"

    def handle(self, *args, **options):
        db_conn = connections["default"]
        try:
            db_conn.cursor()
        except OperationalError:
            self.stdout.write(self.style.ERROR("Database unavailable"))
            exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("Database available"))
