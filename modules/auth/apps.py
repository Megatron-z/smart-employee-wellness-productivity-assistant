from django.apps import AppConfig

class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.auth'
    label = 'modules_auth' # To avoid collision with django.contrib.auth
