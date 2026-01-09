from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from django.conf import settings
        from .integrity import verify_integrity
        import os
        
        # Run check only if not in migration/test mode to avoid cluttering those ops, 
        # but user wanted strict check so let's run it always on startup.
        # Ideally we check if we are the main process or triggered by runserver
        base_dir = settings.BASE_DIR
        verify_integrity(base_dir)
