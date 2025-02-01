from django.apps import AppConfig

class OrdersConfig(AppConfig):
    name = 'orders'

    def ready(self):
        import orders.signals  # чтобы сработали receiver'ы