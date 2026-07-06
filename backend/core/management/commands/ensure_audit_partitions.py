"""Creates upcoming monthly partitions for core_auditlog (docs/02 §5).

Run monthly from ops/cron (a Celery beat task takes over in a later
milestone). Idempotent; the DEFAULT partition catches any gap meanwhile.
"""

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand
from django.db import connection

from core.db import month_partition_sql


class Command(BaseCommand):
    help = "Create monthly partitions for core_auditlog (current month + N ahead)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--ahead", type=int, default=2, help="Months ahead of the current one (default 2)"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        year, month = date.today().year, date.today().month
        with connection.cursor() as cursor:
            for _ in range(options["ahead"] + 1):
                cursor.execute(month_partition_sql("core_auditlog", year, month))
                self.stdout.write(f"ensured core_auditlog_y{year}m{month:02d}")
                year, month = (year + 1, 1) if month == 12 else (year, month + 1)
