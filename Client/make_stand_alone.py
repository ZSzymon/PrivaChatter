import os
import django
PROJECT_NAME = 'PrivaChatterDjango'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '%s.settings' % PROJECT_NAME)
django.setup()
