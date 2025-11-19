import io
import logging
import os

from django import forms
from django.contrib import admin
from django.core.files.storage import storages
from django.core.management import CommandError, call_command
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Backup

logger = logging.getLogger("dbbackup_admin")


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = (
        "backup_type",
        "label",
        "env",
        "backup_created_at",
        "status",
        "size_display",
        "file_status",
        "admin_actions",
    )
    list_filter = ("backup_type", "status", "backup_created_at")
    search_fields = ("file_path",)
    readonly_fields = (
        "file_path",
        "size",
        "record_created_at",
        "backup_created_at",
    )
    actions = ["restore_selected_backup"]

    def file_status(self, obj):
        """Display whether the backup file exists."""
        if obj.file_exists:
            return format_html('<span style="color: #56914a;">✓ File exists</span>')
        return format_html('<span style="color: #b33b46;">✗ File missing</span>')

    file_status.short_description = "File Status"

    def size_display(self, obj):
        return obj.get_size_display()

    size_display.short_description = "Size"

    def admin_actions(self, obj):
        """Display action buttons for each backup."""
        actions = []

        # Download button (if file exists)
        if obj.file_path and obj.file_exists:
            download_url = reverse("admin:download_backup", args=[obj.id])
            actions.append(
                format_html(
                    '<a class="button" href="{}" style="background-color: #2e6da0; '
                    "color: white; padding: 3px 8px; text-decoration: none; "
                    'border-radius: 3px;">Download</a>',
                    download_url,
                )
            )

        # Restore button - only if environment matches
        if obj.status == "completed" and obj.file_path and obj.file_exists:
            current_env = os.getenv("ENVIRONMENT")
            if obj.env != current_env:
                # Environment mismatch - do not show restore button
                pass
            else:
                restore_url = reverse("admin:restore_backup", args=[obj.id])
                actions.append(
                    format_html(
                        '<a class="button" href="{}" style="background-color: #56914a; '
                        "color: white; padding: 3px 8px; text-decoration: none; "
                        'border-radius: 3px; margin-left: 5px;">Restore</a>',
                        restore_url,
                    )
                )

        return mark_safe("".join(actions)) if actions else "-"

    admin_actions.short_description = "Actions"

    def get_urls(self):
        """Add custom URLs for backup operations."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "create-backup/",
                self.admin_site.admin_view(self.create_backup_view),
                name="create_backup",
            ),
            path(
                "restore-backup/<int:backup_id>/",
                self.admin_site.admin_view(self.restore_backup_view),
                name="restore_backup",
            ),
            path(
                "download-backup/<int:backup_id>/",
                self.admin_site.admin_view(self.download_backup_view),
                name="download_backup",
            ),
            path(
                "sync-backups/",
                self.admin_site.admin_view(self.sync_backups_view),
                name="sync_backups",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Add custom buttons to the changelist view."""
        extra_context = extra_context or {}
        extra_context["create_backup_url"] = reverse("admin:create_backup")
        extra_context["sync_backups_url"] = reverse("admin:sync_backups")
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        """Remove the default 'ADD BACKUP +' button."""
        return False

    def create_backup_view(self, request):
        """View to create a new backup."""
        if request.method == "POST":
            backup_type = request.POST.get("backup_type", "db")
            label = request.POST.get("label", "")
            env = os.getenv("ENVIRONMENT", None)
            backup = Backup.objects.create(
                backup_type=backup_type, status="pending", label=label, env=env
            )
            output = io.StringIO()

            try:
                command = "dbbackup" if backup_type == "db" else "mediabackup"
                call_command(command, stdout=output, stderr=output)

                # Find the latest backup file created
                self._update_backup_with_latest_file(backup, backup_type)
                backup.status = "completed"
                backup.backup_created_at = timezone.now()
                backup.save()

                # Create metadata file
                self._create_metadata_file(backup)

                self.message_user(
                    request,
                    f"Backup created successfully: {backup.file_path}",
                )
            except (CommandError, Exception) as e:
                backup.status = "failed"
                backup.save()
                output.seek(0)
                result_output = output.read()
                logger.error(f"Backup creation failed: {e}\nOutput:\n{result_output}")
                self.message_user(
                    request,
                    "Backup creation failed. Check server logs for details.",
                    level="error",
                )

            return HttpResponseRedirect(
                reverse("admin:dbbackup_admin_backup_changelist")
            )

        # Display a form to select backup type
        form = forms.Form()
        form.fields["backup_type"] = forms.ChoiceField(
            choices=[("db", "Database"), ("media", "Media")],
            widget=forms.RadioSelect,
            initial="db",
        )
        form.fields["label"] = forms.CharField(
            required=False, widget=forms.TextInput(attrs={"style": "width: 300px;"})
        )

        context = {
            "form": form,
            "title": "Create Backup",
            "opts": self.model._meta,
            "has_change_permission": self.has_change_permission(request),
        }

        return TemplateResponse(
            request,
            "admin/dbbackup_admin/backup/create_backup.html",
            context,
        )

    def _create_metadata_file(self, backup):
        """Create a sidecar metadata file for the backup."""
        if not backup.file_path:
            return

        try:
            import json

            storage = storages["dbbackup"]
            meta_file_path = f"{backup.file_path}.meta"

            metadata = {
                "label": backup.label,
                "env": backup.env,
                "backup_type": backup.backup_type,
                "backup_created_at": (
                    backup.backup_created_at.isoformat()
                    if backup.backup_created_at
                    else None
                ),
            }

            # storage.save expects a file-like object
            from django.core.files.base import ContentFile

            storage.save(meta_file_path, ContentFile(json.dumps(metadata)))

        except Exception as e:
            logger.warning(
                f"Could not create metadata file for backup {backup.id}: {e}"
            )

    def restore_backup_view(self, request, backup_id):
        """View to restore a specific backup."""
        backup = Backup.objects.get(id=backup_id)

        if request.method == "POST":
            output = io.StringIO()
            try:
                command = "dbrestore" if backup.backup_type == "db" else "mediarestore"
                kwargs = {
                    "stdout": output,
                    "stderr": output,
                    "noinput": True,
                    "interactive": False,
                    "input_filename": backup.file_path,
                }
                # Add pg_options only if restoring a PostgreSQL DB and the env
                # var is set
                if (
                    command == "dbrestore"
                    and os.environ.get("ALLOW_RESTORE_FROM_OTHER_DB") == "True"
                ):
                    kwargs["pg_options"] = "--no-owner --no-privileges"

                call_command(command, **kwargs)

                self.message_user(
                    request,
                    f"Backup restored successfully from: {backup.file_path}",
                )
            except (CommandError, Exception) as e:
                output.seek(0)
                result_output = output.read()
                logger.error(f"Restore failed: {e}\nOutput:\n{result_output}")
                self.message_user(
                    request, f"Restore failed: {result_output}", level="error"
                )

            return HttpResponseRedirect(
                reverse("admin:dbbackup_admin_backup_changelist")
            )

        context = {
            "backup": backup,
            "title": f"Restore Backup: {backup.file_path}",
            "opts": self.model._meta,
        }

        return TemplateResponse(
            request, "admin/dbbackup_admin/backup/restore_backup.html", context
        )

    def sync_backups_view(self, request):
        """View to sync backups with the database."""
        if request.method == "POST":
            output = io.StringIO()
            try:
                call_command("sync_backups", stdout=output, stderr=output)
                self.message_user(request, "Backups synced successfully!")

            except (CommandError, Exception) as e:
                output.seek(0)
                result_output = output.read()
                logger.error(f"Backup sync failed: {e}\nOutput:\n{result_output}")
                self.message_user(
                    request, f"Backup sync failed: {result_output}", level="error"
                )

            return HttpResponseRedirect(
                reverse("admin:dbbackup_admin_backup_changelist")
            )
        context = {
            "title": "Sync Backups",
            "opts": self.model._meta,
        }
        return TemplateResponse(
            request, "admin/dbbackup_admin/backup/sync_backups.html", context
        )

    def download_backup_view(self, request, backup_id):
        """View to download a backup file."""
        backup = Backup.objects.get(id=backup_id)

        if not backup.file_path or not backup.file_exists:
            self.message_user(request, "Backup file not found.", level="error")
            return HttpResponseRedirect(
                reverse("admin:dbbackup_admin_backup_changelist")
            )

        try:
            # Use the storage API to open and read the file for download
            storage = storages["dbbackup"]
            with storage.open(backup.file_path, "rb") as file:
                response = HttpResponse(
                    file.read(), content_type="application/octet-stream"
                )
                response["Content-Disposition"] = (
                    f'attachment; filename="{os.path.basename(backup.file_path)}"'
                )
                return response
        except Exception as e:
            self.message_user(
                request, f"Error downloading backup: {str(e)}", level="error"
            )
            return HttpResponseRedirect(
                reverse("admin:dbbackup_admin_backup_changelist")
            )

    def _update_backup_with_latest_file(self, backup, backup_type):
        """
        Update backup record with the latest file information using the storage API.
        """
        try:
            storage = storages["dbbackup"]
            # List files from the root of the storage
            _, files = storage.listdir("")

            # Filter files based on backup type
            if backup_type == "db":
                backup_files = [f for f in files if f.endswith(".psql.bin")]
            else:
                backup_files = [f for f in files if f.endswith(".tar")]

            if backup_files:
                # Sort by modification time using the storage API
                backup_files.sort(
                    key=lambda f: storage.get_modified_time(f), reverse=True
                )
                latest_file = backup_files[0]

                # Update the backup record with file info from storage
                backup.file_path = latest_file
                backup.size = storage.size(latest_file)
                backup.save()
        except Exception as e:
            # If we can't find the file, leave the backup as is
            logger.warning(f"Could not update backup {backup.id} with file info: {e}")
