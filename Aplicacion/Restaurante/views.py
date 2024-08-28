from django.shortcuts import render, redirect
from .models import *
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from .forms import *
from django.http import HttpResponse, JsonResponse
from datetime import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group, User
import json
from datetime import date
from datetime import datetime
from django.db.models import Sum, Count
from django.utils.timezone import now
from datetime import datetime, timedelta
from background_task import background
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.conf import settings
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime
from decimal import Decimal
#############################################################################################################################################################
def obtener_interacciones_cliente(cliente):
    # Obtener reservas y ventas del cliente
    reservas = Detalles_Reservas.objects.filter(reserva__cliente=cliente).select_related('menu')
    ventas = Ventas.objects.filter(cliente=cliente).select_related('menu')

    # Convertir a DataFrame
    reservas_df = pd.DataFrame(list(reservas.values('reserva_id', 'menu__categoria_menu', 'menu_id')))
    ventas_df = pd.DataFrame(list(ventas.values('venta_id', 'menu__categoria_menu', 'menu_id')))

    # Concatenar DataFrames
    datos = pd.concat([reservas_df, ventas_df], axis=0) if not reservas_df.empty or not ventas_df.empty else pd.DataFrame()

    print("Datos de interacciones cliente:")
    print(datos)  # Agregar impresión para verificar datos
    return datos

def recomendar_menus_por_categoria(cliente, datos_interacciones):
    recomendaciones_por_categoria = {}

    if not datos_interacciones.empty:
        # Contar las interacciones por categoría
        categorias_populares = datos_interacciones['menu__categoria_menu'].value_counts().index.tolist()

        print("Categorías populares:")
        print(categorias_populares)  # Agregar impresión para verificar categorías populares

        for categoria in categorias_populares:
            # Filtrar menús por categoría
            menues_recomendados = Menus.objects.filter(categoria_menu=categoria).exclude(
                detalles_reservas__reserva__cliente=cliente
            ).distinct()

            print(f"Menús recomendados para categoría '{categoria}':")
            print(menues_recomendados)  # Agregar impresión para verificar menús recomendados por categoría

            recomendaciones_por_categoria[categoria] = menues_recomendados
    else:
        # Si no hay interacciones, recomendar menús populares de todas las categorías
        categorias = Menus.objects.values_list('categoria_menu', flat=True).distinct()

        for categoria in categorias:
            menues_recomendados = Menus.objects.filter(categoria_menu=categoria).distinct()

            print(f"Menús recomendados para categoría '{categoria}' (sin interacciones previas):")
            print(menues_recomendados)  # Agregar impresión para verificar menús recomendados por categoría

            recomendaciones_por_categoria[categoria] = menues_recomendados

    return recomendaciones_por_categoria

def enviar_notificacion_recomendacion(usuario_email, recomendaciones_por_categoria, es_nuevo_cliente):
    # Obtener el cliente
    cliente = Clientes.objects.filter(email_cli=usuario_email).first()

    if not cliente:
        print(f"No se encontró el cliente con email {usuario_email}")
        return

    # Renderizar la plantilla con el contexto
    context = {
        'cliente_nombre': cliente.nombre_cli if cliente else 'Cliente',
        'recomendaciones_por_categoria': recomendaciones_por_categoria,
        'url_sitio': 'URL_DE_TU_SITIO',  # Asegúrate de reemplazar esto con la URL real de tu sitio
        'year': timezone.now().year,
        'es_nuevo_cliente': es_nuevo_cliente
    }
    mensaje_html = render_to_string('recomendacion_email.html', context)

    # Enviar el correo
    try:
        email = EmailMessage(
            subject="¡Tienes nuevas recomendaciones de menús!",
            body=mensaje_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[usuario_email]
        )
        email.content_subtype = "html"  # Especificar que el contenido es HTML
        email.send()
        print(f"Correo enviado a {usuario_email}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

def procesar_recomendaciones(usuario_email):
    cliente = Clientes.objects.filter(email_cli=usuario_email).first()
    if cliente:
        datos_interacciones = obtener_interacciones_cliente(cliente)
        recomendaciones_por_categoria = recomendar_menus_por_categoria(cliente, datos_interacciones)
        es_nuevo_cliente = datos_interacciones.empty
        enviar_notificacion_recomendacion(usuario_email, recomendaciones_por_categoria, es_nuevo_cliente)
    else:
        # Manejar el caso donde no se encuentra el cliente
        print(f"No se encontró el cliente con email {usuario_email}")

# Llama a la función de ejemplo con el email del usuario
procesar_recomendaciones('ejemplo@correo.com')
#############################################################################################################################################################

def enviar_correo_nuevo_menu(nuevo_menu):
    subject = f'Nuevo Menú Disponible: {nuevo_menu.nombre_menu}'
    from_email = settings.EMAIL_HOST_USER

    # Obtener la lista de correos de clientes
    recipient_list = Clientes.objects.values_list('email_cli', flat=True)  # Obtiene una lista de correos electrónicos

    # Renderizar la plantilla HTML con los datos del nuevo menú
    html_content = render_to_string('nuevo_menu_email.html', {
        'nombre_menu': nuevo_menu.nombre_menu,
        'descripcion_menu': nuevo_menu.descripcion_menu,
        'categoria_menu': nuevo_menu.categoria_menu,
        'precio_menu': nuevo_menu.precio_menu,
        'foto_menu_url': nuevo_menu.fotos_menu
    })

    # Crear el mensaje de correo electrónico con contenido HTML
    msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
    msg.attach_alternative(html_content, "text/html")

    # Enviar el correo
    msg.send()

def enviar_correo_nueva_promocion(nueva_promocion):
    subject = f'Nueva Promoción: {nueva_promocion.menu.nombre_menu}'
    from_email = settings.EMAIL_HOST_USER

    # Obtener la lista de correos de clientes
    recipient_list = Clientes.objects.values_list('email_cli', flat=True)  # Obtiene una lista de correos electrónicos

    # Renderizar la plantilla HTML con los datos de la nueva promoción
    html_content = render_to_string('nueva_promocion_email.html', {
        'nombre_menu': nueva_promocion.menu.nombre_menu,
        'descripcion_pro': nueva_promocion.descripcion_pro,
        'fecha_inicio_pro': nueva_promocion.fecha_inicio_pro,
        'fecha_fin_pro': nueva_promocion.fecha_fin_pro,
        'descuento_pro': nueva_promocion.descuento_pro
    })

    # Crear el mensaje de correo electrónico con contenido HTML
    msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
    msg.attach_alternative(html_content, "text/html")

    # Enviar el correo
    msg.send()
##########################################################################################################################################################

def registro(request):

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar el usuario si el formulario es válido
            form.save()
            # Crear cliente asociado
            usuario = User.objects.get(username=form.cleaned_data['username'])
            fecha = date.today()
            nuevoClientes = Clientes.objects.create(
                nombre_cli=form.cleaned_data['first_name'],
                apellido_cli=form.cleaned_data['last_name'],
                cedula_cli="0",  # Asignar un valor por defecto
                email_cli=form.cleaned_data['email'],
                telefono_cli="09",  # Asignar un valor por defecto
                fecha_Reguistro_cli=fecha
            )

            # Asignar el grupo "Clientes" al nuevo usuario
            grupo = Group.objects.filter(name='Clientes').first()
            if grupo:
                usuario.groups.add(grupo)

            # Autenticar y hacer login al usuario
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password1'])
            login(request, user)

            # Redirigir al usuario a la plantillaCliente después del registro exitoso
            return redirect('plantillaCliente')
        else:
            # Captura de errores personalizados si el formulario no es válido
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')

            if username and User.objects.filter(username=username).exists():
                form.add_error('username', 'Este nombre de usuario ya está en uso.')

            if email and User.objects.filter(email=email).exists():
                form.add_error('email', 'Este correo electrónico ya está en uso.')

    else:
        form = CustomUserCreationForm()

    data = {
        'form': form
    }

    return render(request, 'registration/registro.html', data)
##############################################################################################################################################
def plantillaCliente(request):
    return render(request, 'plantillaCliente.html')


def menus(request):
    return render(request, 'menus.html')
#############################################################################################################################################
def listadoOrdenMenus(request):
    menuBdd = Menus.objects.all()
    mesaBdd = Mesas.objects.filter(estado_mes='Libre')
    login = False
    menues_recomendados = []
    cliente = None

    if request.user.is_authenticated:
        user = request.user
        cliente = Clientes.objects.filter(email_cli=user.email).first()
        login = True

        if cliente:
            hoy = date.today()  # Fecha actual sin la hora

            if cliente.ultima_recomendacion != hoy:  # Verifica si la última recomendación no fue hoy
                datos_interacciones = obtener_interacciones_cliente(cliente)
                es_nuevo_cliente = datos_interacciones.empty

                if not datos_interacciones.empty:
                    menues_recomendados = recomendar_menus_por_categoria(cliente, datos_interacciones)

                enviar_notificacion_recomendacion(cliente.email_cli, menues_recomendados, es_nuevo_cliente)
                cliente.ultima_recomendacion = hoy  # Actualiza solo con la fecha, sin la hora
                cliente.save()

    menus_con_promocion = Menus.objects.filter(
        promociones__fecha_inicio_pro__lte=timezone.now().date(),
        promociones__fecha_fin_pro__gte=timezone.now().date()
    ).distinct()

    data = {
        'menus': menuBdd,
        'mesas': mesaBdd,
        'user': cliente,
        'login': login,
        'menus_con_promocion': menus_con_promocion,
        'menues_recomendados': menues_recomendados if login else []
    }

    return render(request, 'listadoOrdenMenus.html', data)

#################################################################################################################################################
def reporte_semanal(request):
    # Obtener ventas por fecha
    ventas_por_dia = Ventas.objects.values('fecha_venta').annotate(total_ventas=Count('venta_id')).order_by('fecha_venta')
    # Obtener reservas por fecha
    reservas_por_dia = Reservas.objects.values('fecha_reserva').annotate(total_reservas=Count('reserva_id')).order_by('fecha_reserva')

    # Preparar datos para los gráficos
    ventas_labels = [venta['fecha_venta'].strftime('%Y-%m-%d') for venta in ventas_por_dia]
    ventas_data = [venta['total_ventas'] for venta in ventas_por_dia]
    reservas_labels = [reserva['fecha_reserva'].strftime('%Y-%m-%d') for reserva in reservas_por_dia]
    reservas_data = [reserva['total_reservas'] for reserva in reservas_por_dia]

    context = {
        'ventas_labels': ventas_labels,
        'ventas_data': ventas_data,
        'reservas_labels': reservas_labels,
        'reservas_data': reservas_data,
        'ventas_por_dia': ventas_por_dia,
        'reservas_por_dia': reservas_por_dia,
        'start_date': '2024-07-22',  # Reemplaza con la fecha real
        'end_date': '2024-07-28'     # Reemplaza con la fecha real
    }

    return render(request, 'reporte_semanal.html', context)
#######################################################################################################################################################

def reservarMesaCliente(request):
    data = {
        'status': False,
        'message': 'Error, ocurrió un problema con tu petición'
    }

    if request.method == 'POST':
        try:
            cliente_id = int(request.POST.get('cliente'))
            mesa_id = request.POST.get('mesa')
            articulos = json.loads(request.POST.get('articulos', '[]'))
            personas = int(request.POST.get('personas', 0))
            fecha = request.POST.get('fecha')
            hora = request.POST.get('hora')

            if not cliente_id:
                data['message'] = 'Perdón, pero necesitas iniciar sesión.'
                return JsonResponse(data)

            if not mesa_id:
                data['message'] = 'Selecciona una mesa, por favor 🪑🙏.'
                return JsonResponse(data)

            if personas <= 0:
                data['message'] = 'Debe haber al menos una persona en la mesa 👤🪑.'
                return JsonResponse(data)

            if not fecha or not hora:
                data['message'] = 'Debe seleccionar una fecha 📅 y una hora 🕒.'
                return JsonResponse(data)

            fecha_hora_reserva = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")

            fecha_hoy = datetime.now()
            dos_horas_desde_ahora = fecha_hoy + timedelta(hours=2)

            if fecha_hora_reserva < dos_horas_desde_ahora:
                data['message'] = 'La reserva debe hacerse con al menos dos horas de anticipación ⏳'
                return JsonResponse(data)

            if fecha_hora_reserva < fecha_hoy:
                data['message'] = 'Selecciona una fecha y hora válidas 📅🕒, con al menos dos horas de anticipación ⏳.'
                return JsonResponse(data)

            hora_reserva = fecha_hora_reserva.hour
            minutos_reserva = fecha_hora_reserva.minute

            if hora_reserva < 8 or (hora_reserva > 19 or (hora_reserva == 19 and minutos_reserva > 0)):
                data['message'] = 'La hora de la reserva debe estar entre las 08:00 AM 🕗 y las 07:00 PM 🕖.'
                return JsonResponse(data)

            reserva_cliente_existente = Reservas.objects.filter(
                cliente_id=cliente_id,
                fecha_reserva=fecha_hora_reserva.date(),
                hora_reserva=fecha_hora_reserva.time()
            ).exists()

            if reserva_cliente_existente:
                data['message'] = 'Ya tienes una reserva en la misma fecha y hora.'
                return JsonResponse(data)

            reserva_existente = Reservas.objects.filter(
                mesa_id=mesa_id,
                fecha_reserva=fecha_hora_reserva.date(),
                hora_reserva=fecha_hora_reserva.time()
            ).exists()

            if reserva_existente:
                data['message'] = 'La mesa ya está reservada para esa fecha y hora.'
                return JsonResponse(data)

            if len(articulos) == 0:
                data['message'] = 'No podemos reservar una mesa sin una orden previa 📝🚫'
                return JsonResponse(data)

            nuevaReserva = Reservas.objects.create(
                fecha_reserva=fecha_hora_reserva.date(),
                hora_reserva=fecha_hora_reserva.time(),
                numero_personas_reserva=personas,
                estado_reserva='Pendiente',
                mesa_id=mesa_id,
                cliente_id=cliente_id
            )

            total_precio = Decimal('0.00')
            for item in articulos:
                plato_id = item["plato_id"]
                cantidad = int(item["cantidad"])  # Convertir a entero
                menuSeleccionado = Menus.objects.get(menu_id=plato_id)

                # Calcular el precio con descuento
                precio_con_descuento = menuSeleccionado.precio_con_descuento()

                # Asegurarse de que precio_con_descuento es Decimal
                if not isinstance(precio_con_descuento, Decimal):
                    precio_con_descuento = Decimal(precio_con_descuento)

                total_precio += precio_con_descuento * Decimal(cantidad)

                # Crear detalles de la reserva con la cantidad de platos
                Detalles_Reservas.objects.create(
                    reserva=nuevaReserva,
                    menu=menuSeleccionado,
                    cantidad=cantidad
                )

            # Si quieres guardar el total_precio en la reserva, añade un campo al modelo de Reservas para eso
            # nuevaReserva.total_precio = total_precio
            # nuevaReserva.save()

            data['status'] = True
            data['message'] = 'Reserva realizada con éxito.'
            data['total_precio'] = total_precio  # Opcional, si deseas devolver el total en la respuesta
            return JsonResponse(data)

        except Exception as e:
            data['message'] = str(e)
            return JsonResponse(data)

    return JsonResponse(data)


@background(schedule=60)  # Asegúrate de que el decorador esté configurado correctamente
def actualizar_estado_mesa(fecha_hora_reserva_str, reserva_id):
    fecha_hora_reserva = datetime.strptime(fecha_hora_reserva_str, "%Y-%m-%d %H:%M")
    reserva = Reservas.objects.get(pk=reserva_id)
    mesa = reserva.mesa

    # Verifica si el tiempo actual es mayor o igual a la hora de reserva más 15 minutos
    if datetime.now() >= fecha_hora_reserva + timedelta(minutes=15):
        if reserva.estado_reserva == 'Confirmada':  # Cambia 'Pendiente' por 'Confirmada' si la reserva ya está confirmada
            mesa.estado_mes = 'Libre'
            mesa.save()
            reserva.estado_reserva = 'Liberada'  # Opcional, si quieres cambiar el estado de la reserva también
            reserva.save()
#################################################################################################################################
def bienvenida(request):
    clienteBdd = Clientes.objects.all()

    if (request.user.is_authenticated):
        if(request.user.is_staff > 0):
            return render(request, 'bienvenida.html',{'clientes': clienteBdd})
        else:
            return redirect('plantillaCliente')
    else:
        return redirect('login')


def listadoClientes(request):
    clienteBdd = Clientes.objects.all()
    return render(request, 'listadoClientes.html',{'clientes': clienteBdd})

def guardarClientes(request):
    nombre_cli = request.POST["nombre_cli"]
    apellido_cli = request.POST["apellido_cli"]
    email_cli = request.POST["email_cli"]
    telefono_cli = request.POST["telefono_cli"]
    cedula_cli = request.POST["cedula_cli"]
    fecha_Reguistro_cli = request.POST["fecha_Reguistro_cli"]
    nuevoClientes = Clientes.objects.create(nombre_cli=nombre_cli, apellido_cli=apellido_cli, cedula_cli=cedula_cli,
                                             email_cli=email_cli, telefono_cli=telefono_cli,
                                             fecha_Reguistro_cli=fecha_Reguistro_cli)
    messages.success(request, '¡Cliente guardado exitosamente!')
    return redirect('listadoClientes')


def eliminarClientes(request, cliente_id):
    try:
        cliente = Clientes.objects.get(pk=cliente_id)
        cliente.delete()
        messages.success(request, 'Cliente eliminado correctamente.')
    except Clientes.DoesNotExist:
        messages.error(request, 'El Cliente que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar el cliente por que Tiene una Venta Registrada.')
    return redirect('listadoClientes')


def editarClientes(request, cliente_id):
    clienteEditar = Clientes.objects.get(cliente_id=cliente_id)
    return render(request, 'editarClientes.html', {'clientes': clienteEditar})

def procesarActualizacionClientes(request):
    cliente_id = request.POST["cliente_id"]
    nombre_cli = request.POST["nombre_cli"]
    apellido_cli = request.POST["apellido_cli"]
    email_cli = request.POST["email_cli"]
    telefono_cli = request.POST["telefono_cli"]
    cedula_cli = request.POST["cedula_cli"]
    fecha_Reguistro_cli = request.POST["fecha_Reguistro_cli"]
    # Insertando datos mediante el ORM de DJANGO
    clienteEditar = Clientes.objects.get(cliente_id=cliente_id)
    clienteEditar.nombre_cli = nombre_cli
    clienteEditar.apellido_cli = apellido_cli
    clienteEditar.email_cli = email_cli
    clienteEditar.telefono_cli = telefono_cli
    clienteEditar.cedula_cli = cedula_cli
    clienteEditar.fecha_Reguistro_cli = fecha_Reguistro_cli
    clienteEditar.save()
    messages.success(request, 'Cliente ACTUALIZADO Exitosamente')
    return redirect('listadoClientes')

####################################################################################################################################################

def listadoMesas(request):
    mesaBdd = Mesas.objects.all()
    return render(request, 'listadoMesas.html', {'mesas': mesaBdd})


def guardarMesas(request):
    numero_mes = request.POST["numero_mes"]
    capacidad_mes = request.POST["capacidad_mes"]
    estado_mes = request.POST["estado_mes"]
    nuevoMesas = Mesas.objects.create(numero_mes=numero_mes, capacidad_mes=capacidad_mes, estado_mes=estado_mes)
    messages.success(request, '¡Mesa guardado exitosamente!')
    return redirect('listadoMesas')

def eliminarMesas(request, id_mesa):
    try:
        mesa = Mesas.objects.get(pk=id_mesa)
        mesa.delete()
        messages.success(request, 'Mesa eliminado correctamente.')
    except Mesas.DoesNotExist:
        messages.error(request, 'La Mesa que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar la Mesa por motivos de Datos.')
    return redirect('listadoMesas')

def editarMesas(request, id_mesa):
    mesaEditar = Mesas.objects.get(id_mesa=id_mesa)
    return render(request, 'editarMesas.html', {'mesas': mesaEditar})


def procesarActualizacionMesas(request):
    id_mesa = request.POST["id_mesa"]
    numero_mes = request.POST["numero_mes"]
    capacidad_mes = request.POST["capacidad_mes"]
    estado_mes = request.POST["estado_mes"]
    # Insertando datos mediante el ORM de DJANGO
    mesaEditar = Mesas.objects.get(id_mesa=id_mesa)
    mesaEditar.numero_mes = numero_mes
    mesaEditar.capacidad_mes = capacidad_mes
    mesaEditar.estado_mes = estado_mes
    mesaEditar.save()
    messages.success(request, 'Mesa Actualizado Exitosamente')
    return redirect('listadoMesas')
###################################################################################################################################################


def listadoReservas(request):
    clienteBdd = Clientes.objects.all()
    mesaBdd = Mesas.objects.all()
    reservaBdd = Reservas.objects.all()
    return render(request, 'listadoReservas.html', {'reservas': reservaBdd,'clientes':clienteBdd,'mesas':mesaBdd })


def guardarReservas(request):
    if request.method == 'POST':
        cliente_id_cliente = request.POST.get("cliente_id_cliente")
        clienteSeleccionado = Clientes.objects.get(cliente_id=cliente_id_cliente)

        id_mesa_mesa = request.POST.get("id_mesa_mesa")
        mesaSeleccionado = Mesas.objects.get(id_mesa=id_mesa_mesa)

        fecha_reserva = request.POST.get("fecha_reserva")
        hora_reserva = request.POST.get('hora_reserva', None)
        numero_personas_reserva = request.POST.get("numero_personas_reserva")
        estado_reserva = request.POST.get("estado_reserva")

        # Verificar si la mesa ya está reservada en la misma fecha y hora
        reserva_conflictiva = Reservas.objects.filter(
            mesa=mesaSeleccionado,
            fecha_reserva=fecha_reserva,
            hora_reserva=hora_reserva
        ).exists()

        if reserva_conflictiva:
            messages.error(request, 'La mesa ya está reservada en la fecha y hora seleccionada.')
            return redirect('listadoReservas')

        # Crear la nueva reserva si no hay conflicto
        nuevoReservas = Reservas.objects.create(
            fecha_reserva=fecha_reserva,
            hora_reserva=hora_reserva,
            numero_personas_reserva=numero_personas_reserva,
            estado_reserva=estado_reserva,
            mesa=mesaSeleccionado,
            cliente=clienteSeleccionado
        )

        messages.success(request, 'Reserva guardada exitosamente')
        return redirect('listadoReservas')


def eliminarReservas(request, reserva_id):
    try:
        reserva = Reservas.objects.get(pk=reserva_id)
        reserva.delete()
        messages.success(request, 'Reserva eliminado correctamente.')
    except Reservas.DoesNotExist:
        messages.error(request, 'La Reserva que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar la Reserva por existe un DETALLE DE RESERVA.')
    return redirect('listadoReservas')

def editarReservas(request,reserva_id):
    reservaEditar=Reservas.objects.get(reserva_id=reserva_id)
    mesaBdd = Mesas.objects.all()
    clienteBdd = Clientes.objects.all()
    return render(request, 'editarReservas.html', {'reservas': reservaEditar,'clientes':clienteBdd,'mesas':mesaBdd })


def procesarActualizacionReservas(request):
    if request.method == 'POST':
        try:
            reserva_id = request.POST.get("reserva_id")
            cliente_id_cliente = request.POST.get("cliente_id_cliente")
            id_mesa_mesa = request.POST.get("id_mesa_mesa")
            fecha_reserva = request.POST.get("fecha_reserva")
            hora_reserva = request.POST.get('hora_reserva', None)
            numero_personas_reserva = request.POST.get("numero_personas_reserva")
            estado_reserva = request.POST.get("estado_reserva")

            # Validar los campos requeridos
            if not all([reserva_id, cliente_id_cliente, id_mesa_mesa, fecha_reserva, numero_personas_reserva, estado_reserva]):
                raise ValueError('Faltan campos requeridos en la solicitud.')

            clienteSeleccionado = Clientes.objects.get(cliente_id=cliente_id_cliente)
            mesaSeleccionado = Mesas.objects.get(id_mesa=id_mesa_mesa)

            # Obtener la reserva existente
            reservaEditar = Reservas.objects.get(reserva_id=reserva_id)

            # Crear una fecha y hora combinadas
            fecha_hora_reserva = datetime.strptime(f"{fecha_reserva} {hora_reserva}", "%Y-%m-%d %H:%M")

            # Verificar si ya existe una reserva para esa mesa en la misma fecha y hora, excluyendo la reserva actual
            reserva_existente = Reservas.objects.filter(
                mesa=mesaSeleccionado,
                fecha_reserva=fecha_hora_reserva.date(),
                hora_reserva=fecha_hora_reserva.time()
            ).exclude(reserva_id=reserva_id).exists()

            if reserva_existente:
                raise ValueError('La mesa ya está reservada para esa fecha y hora.')

            # Verificar si el cliente ya tiene otra reserva en la misma fecha y hora, excluyendo la reserva actual
            reserva_cliente_existente = Reservas.objects.filter(
                cliente=clienteSeleccionado,
                fecha_reserva=fecha_hora_reserva.date(),
                hora_reserva=fecha_hora_reserva.time()
            ).exclude(reserva_id=reserva_id).exists()

            if reserva_cliente_existente:
                raise ValueError('El cliente ya tiene una reserva en la misma fecha y hora.')

            # Verificar si el estado actual es 'confirmada' y el nuevo estado es 'pendiente'
            if reservaEditar.estado_reserva.lower() == 'confirmada' and estado_reserva.lower() == 'cancelada':
                # Eliminar las ventas asociadas a la reserva
                Ventas.objects.filter(reserva=reservaEditar).delete()

            # Actualizar los campos de la reserva
            reservaEditar.cliente = clienteSeleccionado
            reservaEditar.mesa = mesaSeleccionado
            reservaEditar.fecha_reserva = fecha_hora_reserva.date()
            reservaEditar.hora_reserva = fecha_hora_reserva.time()
            reservaEditar.numero_personas_reserva = numero_personas_reserva
            reservaEditar.estado_reserva = estado_reserva
            reservaEditar.save()

            # Si el nuevo estado es 'confirmada', crear ventas basadas en los detalles de la reserva
            if estado_reserva.lower() == 'confirmada':
                # Eliminar ventas existentes antes de crear nuevas
                Ventas.objects.filter(reserva=reservaEditar).delete()

                detalles = Detalles_Reservas.objects.filter(reserva=reservaEditar)
                for detalle in detalles:
                    menuSeleccionado = detalle.menu
                    cantidad = detalle.cantidad

                    # Crear una entrada en ventas
                    Ventas.objects.create(
                        menu=menuSeleccionado,
                        reserva=reservaEditar,
                        cliente=clienteSeleccionado,
                        mesa=mesaSeleccionado,
                        fecha_venta=fecha_hora_reserva.date(),
                        cantidad=cantidad
                    )

            messages.success(request, 'Reserva actualizada exitosamente.')
        except Exception as e:
            messages.error(request, f'No puedes actualizar la reserva: {str(e)}')

        return redirect('listadoReservas')


##########################################################################################################################################################
def listadoVentas(request):
    # Obtener todas las ventas
    ventas = Ventas.objects.all()

    # Obtener los datos para el template
    menuBdd = Menus.objects.all()
    clienteBdd = Clientes.objects.all()
    mesaBdd = Mesas.objects.all()

    return render(request, 'listadoVentas.html', {
        'ventas': ventas,
        'menu': menuBdd,
        'clientes': clienteBdd,
        'mesas': mesaBdd
    })

def guardarVentas(request):
    menu_id_menu=request.POST["menu_id_menu"]
    menuSeleccionado=Menus.objects.get(menu_id=menu_id_menu)
    cliente_id_cliente=request.POST["cliente_id_cliente"]
    clienteSeleccionado=Clientes.objects.get(cliente_id=cliente_id_cliente)
    id_mesa_mesa=request.POST["id_mesa_mesa"]
    mesaSeleccionado=Mesas.objects.get(id_mesa=id_mesa_mesa)
    fecha_venta=request.POST["fecha_venta"]
    total_venta=request.POST["total_venta"]
    cantidad = request.POST["cantidad"]

    nuevoVentas = Ventas.objects.create(
        fecha_venta=fecha_venta,
        total_venta=total_venta,
        menu=menuSeleccionado,
        mesa=mesaSeleccionado,
        cliente=clienteSeleccionado,
        cantidad=cantidad
    )

    messages.success(request, 'Venta guardada exitosamente')
    return redirect('listadoVentas')


def eliminarVentas(request, venta_id):
    try:
        venta = Ventas.objects.get(pk=venta_id)
        venta.delete()
        messages.success(request, 'Ventas eliminado correctamente.')
    except Reservas.DoesNotExist:
        messages.error(request, 'Las Ventas que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar la Reserva porque hay Cliente relacionados.')
    return redirect('listadoVentas')


def editarVentas(request,venta_id):
    ventaEditar=Ventas.objects.get(venta_id=venta_id)
    menuBdd = Menus.objects.all()
    clienteBdd = Clientes.objects.all()
    mesaBdd = Mesas.objects.all()
    return render(request, 'editarVentas.html', {'ventas': ventaEditar,'menu':menuBdd, 'clientes':clienteBdd, 'mesas':mesaBdd })

def procesarActualizacionVentas(request):
    try:
        # Obtener los datos del POST
        venta_id = request.POST["venta_id"]
        menu_id_menu = request.POST["menu_id_menu"]
        cliente_id_cliente = request.POST["cliente_id_cliente"]
        id_mesa_mesa = request.POST["id_mesa_mesa"]
        fecha_venta = request.POST["fecha_venta"]
        total_venta = request.POST["total_venta"]
        cantidad = request.POST["cantidad"]

        # Obtener los objetos relacionados
        menuSeleccionado = Menus.objects.get(menu_id=menu_id_menu)
        clienteSeleccionado = Clientes.objects.get(cliente_id=cliente_id_cliente)
        mesaSeleccionado = Mesas.objects.get(id_mesa=id_mesa_mesa)
        ventaEditar = Ventas.objects.get(venta_id=venta_id)

        # Actualizar la venta
        ventaEditar.cliente = clienteSeleccionado
        ventaEditar.menu = menuSeleccionado
        ventaEditar.mesa = mesaSeleccionado
        ventaEditar.fecha_venta = fecha_venta
        ventaEditar.total_venta = total_venta
        ventaEditar.cantidad = cantidad
        ventaEditar.save()

        # Actualizar el detalle de reserva correspondiente
        try:
            detalleReserva = Detalles_Reservas.objects.get(
                reserva=ventaEditar.reserva,  # Suponiendo que `ventaEditar.reserva` es el campo relacionado
                menu=menuSeleccionado
            )
            detalleReserva.cantidad = cantidad
            detalleReserva.save()
        except Detalles_Reservas.DoesNotExist:
            messages.error(request, 'No se encontró el detalle de reserva para actualizar.')

        messages.success(request, 'Venta ACTUALIZADA Exitosamente')

    except Ventas.DoesNotExist:
        messages.error(request, 'No se encontró la venta para actualizar.')
    except Menus.DoesNotExist:
        messages.error(request, 'No se encontró el menú especificado.')
    except Clientes.DoesNotExist:
        messages.error(request, 'No se encontró el cliente especificado.')
    except Mesas.DoesNotExist:
        messages.error(request, 'No se encontró la mesa especificada.')
    except Exception as e:
        messages.error(request, f'Error al actualizar la venta: {str(e)}')

    return redirect('listadoVentas')

##################################################################################################################################################
def listadoMenus(request):
    menuBdd = Menus.objects.all()
    return render(request, 'listadoMenus.html',{'menus': menuBdd})

def guardarMenus(request):
    nombre_menu = request.POST["nombre_menu"]
    descripcion_menu = request.POST["descripcion_menu"]
    categoria_menu = request.POST["categoria_menu"]
    disponibilidad_menu = request.POST["disponibilidad_menu"]
    precio_menu = request.POST["precio_menu"]
    fotos_menu = request.FILES.get("fotos_menu")

    nuevoMenu = Menus.objects.create(
        nombre_menu=nombre_menu,
        descripcion_menu=descripcion_menu,
        categoria_menu=categoria_menu,
        disponibilidad_menu=disponibilidad_menu,
        precio_menu=precio_menu,
        fotos_menu=fotos_menu
    )

    # Enviar correo a los clientes
    enviar_correo_nuevo_menu(nuevoMenu)

    messages.success(request, 'Menú guardado exitosamente y notificación enviada a los clientes.')
    return redirect('listadoMenus')



def eliminarMenus(request, menu_id):
    try:
        menu = Menus.objects.get(pk=menu_id)
        menu.delete()
        messages.success(request, 'Menus eliminado correctamente.')
    except Menus.DoesNotExist:
        messages.error(request, 'El Menu que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar el menu porque existen reservas')
    return redirect('listadoMenus')


def editarMenus(request, menu_id):
    menuEditar = Menus.objects.get(menu_id=menu_id)
    return render(request, 'editarMenus.html', {'menus': menuEditar})

def procesarActualizacionMenus(request):
    menu_id = request.POST["menu_id"]
    nombre_menu = request.POST["nombre_menu"]
    descripcion_menu = request.POST["descripcion_menu"]
    categoria_menu = request.POST["categoria_menu"]
    disponibilidad_menu = request.POST["disponibilidad_menu"]
    precio_menu = request.POST["precio_menu"]
    fotos_menu=request.FILES.get("fotos_menu")
    # Insertando datos mediante el ORM de DJANGO
    menuEditar = Menus.objects.get(menu_id=menu_id)
    menuEditar.nombre_menu = nombre_menu
    menuEditar.descripcion_menu = descripcion_menu
    menuEditar.categoria_menu = categoria_menu
    menuEditar.disponibilidad_menu = disponibilidad_menu
    menuEditar.precio_menu = precio_menu
    menuEditar.fotos_menu = fotos_menu
    menuEditar.save()
    messages.success(request, 'Menu ACTUALIZADO Exitosamente')
    return redirect('listadoMenus')

#############################################################################################################################################

def listadoDetalles_Reservas(request):
    detalle_ReservaBdd = Detalles_Reservas.objects.all()
    reservaBdd = Reservas.objects.all()
    menuBdd = Menus.objects.all()
    return render(request, 'listadoDetalles_Reservas.html', {'detalle_Reservas': detalle_ReservaBdd, 'reservas': reservaBdd, 'menus': menuBdd})

def guardarDetalles_Reservas(request):
    if request.method == 'POST':
        try:
            reserva_id_reserva = request.POST.get("reserva_id_reserva")
            menu_id_menu = request.POST.get("menu_id_menu")
            cantidad = request.POST.get("cantidad")

            if not reserva_id_reserva or not menu_id_menu or not cantidad:
                raise ValueError("Todos los campos son requeridos")

            reservaSeleccionado = Reservas.objects.get(reserva_id=reserva_id_reserva)
            menuSeleccionado = Menus.objects.get(menu_id=menu_id_menu)

            # Puedes hacer validaciones adicionales aquí si es necesario

            # Crear el detalle de reserva
            nuevodetalle_Reserva = Detalles_Reservas.objects.create(
                reserva=reservaSeleccionado,
                menu=menuSeleccionado,
                cantidad=cantidad
            )

            messages.success(request, 'Detalles Reserva guardada exitosamente')
            return redirect('listadoDetalles_Reservas')

        except Reservas.DoesNotExist:
            messages.error(request, 'Reserva no encontrada')
        except Menus.DoesNotExist:
            messages.error(request, 'Menú no encontrado')
        except ValueError as ve:
            messages.error(request, str(ve))
        except Exception as e:
            messages.error(request, 'Error al guardar los detalles de reserva: {}'.format(e))

    return HttpResponseBadRequest('Método no permitido o falta de datos')


def eliminarDetalles_Reservas(request, detalle_reserva_id):
    try:
        detalles_Reservas = Detalles_Reservas.objects.get(pk=detalle_reserva_id)
        detalles_Reservas.delete()
        messages.success(request, 'Detalles Ventas eliminado correctamente.')
    except Detalles_Reservas.DoesNotExist:
        messages.error(request, 'Los Detalles Ventas que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar el Detalles Ventas porque hay productos relacionados.')
    return redirect('listadoDetalles_Reservas')

def editarDetalles_Reservas(request,detalle_reserva_id):
    detalle_ReservaEditar=Detalles_Reservas.objects.get(detalle_reserva_id=detalle_reserva_id)
    reservaBdd = Reservas.objects.all()
    menuBdd = Menus.objects.all()
    return render(request, 'editarDetalles_Reservas.html', {'detalle_Reservas': detalle_ReservaEditar,'reservas':reservaBdd,'menus':menuBdd })


def procesarActualizacionDetalles_Reservas(request):
    try:
        # Obtener los datos del POST
        detalle_reserva_id = request.POST["detalle_reserva_id"]
        reserva_id_reserva = request.POST["reserva_id_reserva"]
        menu_id_menu = request.POST["menu_id_menu"]
        cantidad = request.POST["cantidad"]

        # Obtener los objetos relacionados
        reservaSeleccionado = Reservas.objects.get(reserva_id=reserva_id_reserva)
        menuSeleccionado = Menus.objects.get(menu_id=menu_id_menu)
        detalle_ReservaEditar = Detalles_Reservas.objects.get(detalle_reserva_id=detalle_reserva_id)

        # Verificar si el menú ha cambiado
        menuAnterior = detalle_ReservaEditar.menu

        # Actualizar el detalle de reserva
        detalle_ReservaEditar.menu = menuSeleccionado
        detalle_ReservaEditar.cantidad = cantidad
        detalle_ReservaEditar.reserva = reservaSeleccionado
        detalle_ReservaEditar.save()

        if menuAnterior != menuSeleccionado:
            # Si el menú cambió, eliminar la venta asociada al menú anterior
            Ventas.objects.filter(reserva=reservaSeleccionado, menu=menuAnterior).delete()

            # Crear una nueva venta para el nuevo menú
            Ventas.objects.create(
                menu=menuSeleccionado,
                reserva=reservaSeleccionado,
                cliente=reservaSeleccionado.cliente,
                mesa=reservaSeleccionado.mesa,
                fecha_venta=reservaSeleccionado.fecha_reserva,
                cantidad=cantidad,
                total_venta=menuSeleccionado.precio_menu * int(cantidad)
            )
        else:
            # Si el menú no cambió, actualizar la venta existente
            venta_existente = Ventas.objects.filter(reserva=reservaSeleccionado, menu=menuSeleccionado).first()
            if venta_existente:
                venta_existente.cantidad = cantidad
                venta_existente.total_venta = menuSeleccionado.precio_menu * int(cantidad)
                venta_existente.save()

        messages.success(request, 'Detalles de Reserva ACTUALIZADO Exitosamente')

    except Exception as e:
        messages.error(request, f'Error al actualizar los detalles de la reserva: {str(e)}')

    return redirect('listadoDetalles_Reservas')




########################################################################################################################################################

def listadoPromociones(request):
    promocionBdd = Promociones.objects.all()
    menuBdd = Menus.objects.all()
    return render(request, 'listadoPromociones.html', {'promociones': promocionBdd,'menus':menuBdd})


def guardarPromociones(request):
    menu_id_menu = request.POST["menu_id_menu"]
    menuSeleccionado = Menus.objects.get(menu_id=menu_id_menu)
    descripcion_pro = request.POST["descripcion_pro"]
    fecha_inicio_pro = request.POST.get('fecha_inicio_pro')
    fecha_fin_pro = request.POST.get('fecha_fin_pro')
    descuento_pro = request.POST["descuento_pro"]

    # Validar si ya existe una promoción para el mismo menú en el rango de fechas
    promociones_existentes = Promociones.objects.filter(
        menu=menuSeleccionado,
        fecha_inicio_pro__lte=fecha_fin_pro,
        fecha_fin_pro__gte=fecha_inicio_pro
    )

    if promociones_existentes.exists():
        messages.error(request, 'Ya existe una promoción para este menú en las fechas especificadas.')
        return redirect('listadoPromociones')

    # Crear la nueva promoción si no existen conflictos
    nuevoPromociones = Promociones.objects.create(
        descripcion_pro=descripcion_pro,
        fecha_inicio_pro=fecha_inicio_pro,
        fecha_fin_pro=fecha_fin_pro,
        descuento_pro=descuento_pro,
        menu=menuSeleccionado
    )

    enviar_correo_nueva_promocion(nuevoPromociones)

    messages.success(request, 'Promoción guardada exitosamente y notificación enviada a los clientes.')
    return redirect('listadoPromociones')


def eliminarPromociones(request, promociones_id):
    try:
        promocion = Promociones.objects.get(pk=promociones_id)
        promocion.delete()
        messages.success(request, 'Promocion eliminado correctamente.')
    except Reservas.DoesNotExist:
        messages.error(request, 'La Promocion que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar la Promocion porque hay productos relacionados.')
    return redirect('listadoPromociones')

def editarPromociones(request,promociones_id):
    promocionEditar=Promociones.objects.get(promociones_id=promociones_id)
    menuBdd = Menus.objects.all()
    return render(request, 'editarPromociones.html', {'promociones': promocionEditar,'menus':menuBdd})

def procesarActualizacionPromociones(request):
    promociones_id = request.POST["promociones_id"]
    menu_id_menu = request.POST["menu_id_menu"]
    menuSeleccionado = Menus.objects.get(menu_id=menu_id_menu)
    descripcion_pro = request.POST["descripcion_pro"]
    fecha_inicio_pro = request.POST.get('fecha_inicio_pro')
    fecha_fin_pro = request.POST.get('fecha_fin_pro')
    descuento_pro = request.POST["descuento_pro"]

    # Obtener la promoción a actualizar
    promocionEditar = Promociones.objects.get(promociones_id=promociones_id)

    # Validar si el rango de fechas actualizado se solapa con otra promoción existente
    promociones_existentes = Promociones.objects.filter(
        menu=menuSeleccionado,
        fecha_inicio_pro__lte=fecha_fin_pro,
        fecha_fin_pro__gte=fecha_inicio_pro
    ).exclude(promociones_id=promocionEditar.promociones_id)

    if promociones_existentes.exists():
        messages.error(request, 'Ya existe una promoción para este menú en las fechas especificadas.')
        return redirect('listadoPromociones')

    # Actualizar los datos de la promoción
    promocionEditar.menu = menuSeleccionado
    promocionEditar.descripcion_pro = descripcion_pro
    promocionEditar.fecha_inicio_pro = fecha_inicio_pro
    promocionEditar.fecha_fin_pro = fecha_fin_pro
    promocionEditar.descuento_pro = descuento_pro
    promocionEditar.save()

    messages.success(request, 'Promoción actualizada exitosamente.')
    return redirect('listadoPromociones')
###########################################################################################################################################################
def listadoRecibo_Reserva(request):
    recibo_reservaBdd = Recibo_Reserva.objects.all()
    clienteBdd = Clientes.objects.all()
    reservaBdd = Reservas.objects.all()
    return render(request, 'listadoRecibo_Reserva.html', {
        'recibo_reservas': recibo_reservaBdd,
        'clientes': clienteBdd,
        'reservas': reservaBdd
    })

def guardarRecibo_Reserva(request):
    cliente_id_cliente=request.POST["cliente_id_cliente"]
    clienteSeleccionado=Clientes.objects.get(cliente_id=cliente_id_cliente)
    reserva_id_reserva=request.POST["reserva_id_reserva"]
    reservaSeleccionado=Reservas.objects.get(reserva_id=reserva_id_reserva)
    total_re = request.POST["total_re"]
    fecha_emision_re = request.POST["fecha_emision_re"]

    nuevoRecibo_Reserva = Recibo_Reserva.objects.create(
        cliente=clienteSeleccionado,
        reserva=reservaSeleccionado,
        total_re=total_re,
        fecha_emision_re=fecha_emision_re
    )

    messages.success(request, 'Recibo de Reserva guardado exitosamente')
    return redirect('listadoRecibo_Reserva')



def eliminarRecibo_Reserva(request, id_re):
    try:
        recibo_reserva = Recibo_Reserva.objects.get(pk=id_re)
        recibo_reserva.delete()
        messages.success(request, 'Recibo de Reserva eliminado correctamente.')
    except Recibo_Reserva.DoesNotExist:
        messages.error(request, 'El Recibo de Reserva que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar el Recibo de Reserva porque hay datos relacionados.')
    return redirect('listadoRecibo_Reserva')


def editarRecibo_Reserva(request, id_re):
    recibo_ReservaEditar = Recibo_Reserva.objects.get(id_re=id_re)
    clienteBdd = Clientes.objects.all()
    reservaBdd = Reservas.objects.all()
    return render(request, 'editarRecibo_Reserva.html', {
        'recibo_Reservas': recibo_ReservaEditar,
        'clientes': clienteBdd,
        'reservas': reservaBdd
    })


def procesarActualizacionRecibo_Reserva(request):
    id_re=request.POST["id_re"]
    cliente_id_cliente=request.POST["cliente_id_cliente"]
    clienteSeleccionado=Clientes.objects.get(cliente_id=cliente_id_cliente)
    reserva_id_reserva=request.POST["reserva_id_reserva"]
    reservaSeleccionado=Reservas.objects.get(reserva_id=reserva_id_reserva)
    total_re = request.POST["total_re"]
    fecha_emision_re = request.POST["fecha_emision_re"]

    recibo_ReservaEditar = Recibo_Reserva.objects.get(id_re=id_re)
    recibo_ReservaEditar.cliente = clienteSeleccionado
    recibo_ReservaEditar.reserva = reservaSeleccionado
    recibo_ReservaEditar.total_re = total_re
    recibo_ReservaEditar.fecha_emision_re = fecha_emision_re
    recibo_ReservaEditar.save()

    messages.success(request, 'Recibo de Reserva actualizado exitosamente')
    return redirect('listadoRecibo_Reserva')
###################################################################################################################################################################s
# LOGIN CLIENTE

def viewLoginCliente(request):
     return render(request, 'client/auth/login.html')
