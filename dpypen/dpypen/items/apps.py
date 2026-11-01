from django.apps import AppConfig


class ItemsConfig(AppConfig):
    name = 'dpypen.items'
    label = 'items'

    def ready(self):
        # fold() in every SQLite connection's SQL (kit lists.py, items/listing.py).
        from dpypen.items import listing

        listing.wire()
