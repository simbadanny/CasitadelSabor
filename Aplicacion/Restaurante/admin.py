from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Clientes)
admin.site.register(Mesas)
admin.site.register(Reservas)
admin.site.register(Ventas)
admin.site.register(Menus)
admin.site.register(Detalles_Reservas)
admin.site.register(Promociones)
admin.site.register(Recibo_Reserva)
