# Django-DBBackup Admin Integration

This Django application provides a user-friendly admin interface for the django-dbbackup package, allowing administrators to create and restore database backups directly from the Django admin panel.

## Features

- **Create Backups**: Create database or media backups with a single click
- **Restore Backups**: Restore from any existing backup
- **Backup History**: View all backups with creation date, size, and status
- **File Status**: Check if backup files still exist on disk
- **Download Backups**: Download backup files for external storage
- **Confirmation Dialogs**: Prevent accidental restores with confirmation prompts
- **Error Handling**: Clear feedback for backup and restore operations

## Configuration

Make sure you have django-dbbackup properly configured in your settings:

```python
STORAGES = {
    "dbbackup": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": BASE_DIR / "backups",
        },
    },
}
```

## Usage

### Creating Backups

1. Go to the Django admin panel
2. Navigate to "Dbbackup_admin" → "Backups"
3. Click the "Create Backup" button
4. Select the backup type (Database or Media)
5. Click "Create Backup"

### Restoring Backups

#### Restore a Specific Backup:

1. In the backups list, find the backup you want to restore
2. Click the "Restore" button in the Actions column
3. Review the backup details and confirm the restore

### Downloading Backups

1. In the backups list, find the backup you want to download
2. Click the "Download" button in the Actions column

## Management Commands

### Sync Existing Backups

If you have existing backup files that aren't showing up in the admin panel, run:

```bash
python manage.py sync_backups
```

This command will scan your backup directory and add any missing backup files to the database.

## File Naming Conventions

The system expects the following file naming conventions:

- Database backups: `{database}-{hash}-{timestamp}.psql.bin`
- Media backups: `{timestamp}.tar`

## Security Considerations

- Only users with admin access can create and restore backups
- Restore operations require confirmation to prevent accidental data loss
- Backup files are stored in the configured backup directory

## Troubleshooting

### Backups Not Showing Up

1. Check that the backup directory is correctly configured in settings
2. Run `python manage.py sync_backups` to sync existing files
3. Verify that backup files follow the expected naming convention

### Restore Fails

1. Check that the backup file exists on disk
2. Verify the backup file is not corrupted
3. Check the Django logs for detailed error messages

### Create Backup Fails

1. Verify django-dbbackup is properly configured
2. Check that the backup directory is writable
3. Ensure you have sufficient disk space

## Installation Steps

1. Add the app to your `INSTALLED_APPS` if not already added:

   ```python
   INSTALLED_APPS = [
       # ... other apps
       "dbbackup",
       "dbbackup_admin",
       # ... other apps
   ]
   ```

2. Run migrations:

   ```bash
   python manage.py makemigrations dbbackup_admin
   python manage.py migrate
   ```

3. Sync existing backups:
   ```bash
   python manage.py sync_backups
   ```

## Customization

You can customize the templates by overriding them in your project's template directory:

- `admin/dbbackup_admin/backup/change_list.html`
- `admin/dbbackup_admin/backup/create_backup.html`
- `admin/dbbackup_admin/backup/restore_backup.html`
