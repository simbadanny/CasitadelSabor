from django.db import models
from django.utils import timezone


class Clientes(models.Model):
    cliente_id = models.AutoField(primary_key=True)
    nombre_cli = models.CharField(max_length=50)
    apellido_cli = models.CharField(max_length=150)
    email_cli = models.EmailField()
    cedula_cli = models.CharField(max_length=10, null=True, blank=True)
    telefono_cli = models.CharField(max_length=15)
    fecha_Reguistro_cli = models.DateField()
    ultima_recomendacion = models.DateField(null=True, blank=True)


    def __str__(self):
        fila="{0}: {1}"
        return fila.format(self.cliente_id,self.nombre_cli)


class Mesas(models.Model):
    id_mesa = models.AutoField(primary_key=True)
    numero_mes = models.CharField(max_length=50, null=True, blank=True)
    capacidad_mes = models.IntegerField()
    estado_mes = models.CharField(max_length=20, null=True, blank=True)
    def actualizar_estado(self):
        # Check if this table has any confirmed reservations for today or the future
        reservas_activas = Reservas.objects.filter(
            mesa=self,
            fecha_reserva__gte=datetime.today().date(),
            estado_reserva='confirmada'
        )
        self.estado_mes = 'ocupada' if reservas_activas.exists() else 'libre'
        self.save()

    def __str__(self):
        return f"Mesa {self.numero_mes} - {self.estado_mes}"


class Reservas(models.Model):
    reserva_id = models.AutoField(primary_key=True)
    fecha_reserva = models.DateField()
    hora_reserva = models.TimeField()
    numero_personas_reserva = models.IntegerField()
    estado_reserva = models.CharField(max_length=20)
    cliente = models.ForeignKey(Clientes, null=True, blank=True, on_delete=models.PROTECT)
    mesa = models.ForeignKey(Mesas, null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.reserva_id}: {self.fecha_reserva}"


class Menus(models.Model):
    menu_id = models.AutoField(primary_key=True)
    nombre_menu = models.CharField(max_length=100)
    descripcion_menu = models.TextField()
    categoria_menu = models.CharField(max_length=100, null=True, blank=True)
    disponibilidad_menu = models.CharField(max_length=100, null=True, blank=True)
    precio_menu = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fotos_menu = models.FileField(upload_to='menus', null=True, blank=True)

    def __str__(self):
        fila = "{0}: {1}"
        return fila.format(self.menu_id, self.nombre_menu)

    def precio_con_descuento(self):
        """ Devuelve el precio con descuento si hay una promoción activa. """
        promociones = Promociones.objects.filter(
            menu=self,
            fecha_inicio_pro__lte=timezone.now().date(),
            fecha_fin_pro__gte=timezone.now().date()
        )
        if promociones.exists():
            promocion = promociones.first()
            descuento = promocion.descuento_pro / 100
            precio_descuento = self.precio_menu * (1 - descuento)
            return round(precio_descuento, 2)
        return self.precio_menu

    def tiene_promocion_activa(self):
        """ Verifica si el menú tiene una promoción activa. """
        return Promociones.objects.filter(
            menu=self,
            fecha_inicio_pro__lte=timezone.now().date(),
            fecha_fin_pro__gte=timezone.now().date()
        ).exists()




class Detalles_Reservas(models.Model):
    detalle_reserva_id = models.AutoField(primary_key=True)
    menu = models.ForeignKey(Menus, null=True, blank=True, on_delete=models.PROTECT)
    reserva = models.ForeignKey(Reservas, null=True, blank=True, on_delete=models.PROTECT)
    cantidad = models.IntegerField(default=1)

    def __str__(self):
        fila = "{0}: {1} - {2} x {3}"
        return fila.format(self.detalle_reserva_id, self.reserva, self.menu.nombre_plato, self.cantidad)

    @property
    def precio_con_descuento(self):
        if self.menu.promociones_set.exists():
            # Asume que la primera promoción es la aplicable
            promocion = self.menu.promociones_set.first()
            descuento = promocion.descuento_pro
            precio_original = self.menu.precio_menu
            precio_descuento = precio_original * (1 - descuento / 100)
            return round(precio_descuento, 2)
        return self.menu.precio_menu

    @property
    def total_con_descuento(self):
        return round(self.precio_con_descuento * self.cantidad, 2)



class Ventas(models.Model):
    venta_id = models.AutoField(primary_key=True)
    fecha_venta = models.DateField(null=True, blank=True)
    total_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cantidad = models.IntegerField(default=1)
    menu = models.ForeignKey(Menus, null=True, blank=True, on_delete=models.PROTECT)
    reserva = models.ForeignKey(Reservas, null=True, blank=True, on_delete=models.PROTECT)
    cliente = models.ForeignKey(Clientes, null=True, blank=True, on_delete=models.PROTECT)
    mesa = models.ForeignKey(Mesas, null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.venta_id}: {self.fecha_venta}"

    @property
    def precio_con_descuento(self):
        if self.menu.promociones_set.exists():
            # Asume que la primera promoción es la aplicable
            promocion = self.menu.promociones_set.first()
            descuento = promocion.descuento_pro
            precio_original = self.menu.precio_menu
            precio_descuento = precio_original * (1 - descuento / 100)
            return round(precio_descuento, 2)
        return self.menu.precio_menu

    @property
    def total_con_descuento(self):
        return round(self.precio_con_descuento * self.cantidad, 2)

    @property
    def precio_sin_descuento(self):
        return round(self.menu.precio_menu, 2)

    @property
    def total_sin_descuento(self):
        return round(self.precio_sin_descuento * self.cantidad, 2)




#Relacion de Promociones de 1 a muchos a Promociones de menu
class Promociones(models.Model):
    promociones_id = models.AutoField(primary_key=True)
    descripcion_pro = models.TextField()
    fecha_inicio_pro = models.DateField()
    fecha_fin_pro = models.DateField()
    descuento_pro = models.DecimalField(max_digits=5, decimal_places=2)
    menu = models.ForeignKey(Menus, null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        fila="{0}: {1}"
        return fila.format(self.promociones_id,self.descripcion_pro)

class Recibo_Reserva(models.Model):
    id_re = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Clientes, null=True, blank=True, on_delete=models.PROTECT)
    reserva = models.ForeignKey(Reservas, null=True, blank=True, on_delete=models.PROTECT)
    total_re = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_emision_re = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        fila="{0}: {1}"
        return fila.format(self.total_re)
