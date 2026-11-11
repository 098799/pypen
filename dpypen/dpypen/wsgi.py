"""
WSGI config for dpypen project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dpypen.settings')

# One gunicorn worker with threads since the speed pass of 11 Nov 2026
# (deploy/pypen.service): cap glibc's arenas before the first thread starts
# (kit README §7 "Memory").
from dpypen.items import malloc  # noqa: E402

malloc.start()

application = get_wsgi_application()
