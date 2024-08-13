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
from datetime import timedelta
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



def obtener_interacciones_cliente(cliente):
    # Obtener reservas y ventas del cliente
    reservas = Detalles_Reservas.objects.filter(reserva__cliente=cliente).select_related('menu')
    ventas = Detalles_Ventas.objects.filter(venta__cliente=cliente).select_related('menu')

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
        'precio_menu': nuevo_menu.precio_menu
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

    data = {
        'form': CustomUserCreationForm
    }

    if( request.method == 'POST' ):
        formulario = CustomUserCreationForm(data = request.POST)
        if(formulario.is_valid()):
            formulario.save()
            usuario = User.objects.get(username=formulario.cleaned_data['username'])
            fecha = date.today()
            nuevoClientes = Clientes.objects.create(
                nombre_cli=formulario.cleaned_data['username'],
                apellido_cli=formulario.cleaned_data['last_name'],
                cedula_cli="0",
                email_cli=formulario.cleaned_data['email'],
                telefono_cli="09",
                fecha_Reguistro_cli=fecha
            )


            grupo = Group.objects.filter(name='Clientes').first()
            if grupo:
                usuario.groups.add(grupo)

            user = authenticate(username = formulario.cleaned_data['username'], password=formulario.cleaned_data['password1'])
            login(request, user)

            return redirect('plantillaCliente')

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
    user = ''
    login = False
    menues_recomendados = []

    if request.user.is_authenticated:
        user = request.user
        cliente = Clientes.objects.filter(nombre_cli=user.username).first()
        login = True

        if cliente:
            hoy = timezone.now().date()

            # Obtener las interacciones del cliente
            datos_interacciones = obtener_interacciones_cliente(cliente)
            es_nuevo_cliente = datos_interacciones.empty

            # Si el cliente es nuevo o si la recomendación no se ha enviado hoy
            if es_nuevo_cliente or cliente.ultima_recomendacion != hoy:
                if not datos_interacciones.empty:
                    # Obtener recomendaciones basadas en categorías
                    menues_recomendados = recomendar_menus_por_categoria(cliente, datos_interacciones)

                # Enviar las recomendaciones por correo
                enviar_notificacion_recomendacion(cliente.email_cli, menues_recomendados, es_nuevo_cliente)

                # Actualizar la última fecha de recomendación
                cliente.ultima_recomendacion = hoy
                cliente.save()
            else:
                # Si ya se ha enviado una recomendación hoy, no recalcular
                menues_recomendados = Menus.objects.none()

    # Obtener menús con promociones activas
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
    today = datetime.now().date()
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)

    reservas = Reservas.objects.filter(fecha_reserva__range=[start_date, end_date])
    ventas = Ventas.objects.filter(fecha_venta__range=[start_date, end_date])

    # Preparar datos para gráficos
    ventas_por_dia = ventas.values('fecha_venta').annotate(total_ventas=Sum('total_venta')).order_by('fecha_venta')
    reservas_por_dia = reservas.values('fecha_reserva').annotate(total_reservas=Count('reserva_id')).order_by('fecha_reserva')

    # Convertir datos a listas para gráficos
    ventas_labels = [v['fecha_venta'].strftime('%d/%m') for v in ventas_por_dia]
    ventas_data = [v['total_ventas'] for v in ventas_por_dia]
    reservas_labels = [r['fecha_reserva'].strftime('%d/%m') for r in reservas_por_dia]
    reservas_data = [r['total_reservas'] for r in reservas_por_dia]

    context = {
        'reservas': reservas,
        'ventas': ventas,
        'ventas_por_dia': ventas_por_dia,
        'reservas_por_dia': reservas_por_dia,
        'start_date': start_date,
        'end_date': end_date,
        'ventas_labels': ventas_labels,
        'ventas_data': ventas_data,
        'reservas_labels': reservas_labels,
        'reservas_data': reservas_data,
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
            cliente_id = int(request.POST['cliente'])
            cliente = Clientes.objects.filter(cliente_id=cliente_id).first()
            mesa_id = request.POST['mesa']
            mesa = Mesas.objects.filter(id_mesa=mesa_id).first()
            articulos = json.loads(request.POST.get('articulos', '[]'))
            personas = int(request.POST['personas'])
            fecha = request.POST['fecha']
            hora = request.POST['hora']

            fecha_hora_reserva = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")

            reserva_existente = Reservas.objects.filter(
                mesa=mesa,
                fecha_reserva=fecha,
                hora_reserva=hora
            ).exists()

            if reserva_existente:
                data['message'] = 'La mesa ya está reservada para esa fecha y hora.'
                return JsonResponse(data)

            nuevaReserva = Reservas.objects.create(
                fecha_reserva=fecha,
                hora_reserva=hora,
                numero_personas_reserva=personas,
                estado_reserva='Pendiente',
                mesa=mesa,
                cliente=cliente
            )

            reservaSeleccionado = Reservas.objects.get(reserva_id=nuevaReserva.reserva_id)

            for item in articulos:
                plato_id = item["plato_id"]
                cantidad = item["cantidad"]
                menuSeleccionado = Menus.objects.get(menu_id=plato_id)

                Detalles_Reservas.objects.create(
                    reserva=reservaSeleccionado,
                    menu=menuSeleccionado
                )

            tiempo_de_aviso = fecha_hora_reserva - timedelta(minutes=5)
            actualizar_estado_mesa(str(fecha_hora_reserva), nuevaReserva.reserva_id, schedule=tiempo_de_aviso)

            data = {
                'status': True,
                'message': "Tu reserva fue exitosa",
            }
        except Exception as e:
            data['message'] = f'Error: {str(e)}'

    return JsonResponse(data)

@background(schedule=60)
def actualizar_estado_mesa(fecha_hora_reserva_str, reserva_id):
    fecha_hora_reserva = datetime.strptime(fecha_hora_reserva_str, "%Y-%m-%d %H:%M")
    reserva = Reservas.objects.get(pk=reserva_id)
    mesa = reserva.mesa

    if datetime.now() >= fecha_hora_reserva and reserva.estado_reserva == 'Pendiente':
        mesa.estado_mes = 'Ocupado'
        mesa.save()
        reserva.estado_reserva = 'Confirmada'
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
    cliente_id_cliente=request.POST["cliente_id_cliente"]
    clienteSeleccionado=Clientes.objects.get(cliente_id=cliente_id_cliente)
    id_mesa_mesa=request.POST["id_mesa_mesa"]
    mesaSeleccionado=Mesas.objects.get(id_mesa=id_mesa_mesa)
    fecha_reserva=request.POST["fecha_reserva"]
    hora_reserva = request.POST.get('hora_reserva', None)
    numero_personas_reserva=request.POST["numero_personas_reserva"]
    estado_reserva=request.POST["estado_reserva"]

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
    reserva_id=request.POST["reserva_id"]
    cliente_id_cliente=request.POST["cliente_id_cliente"]
    clienteSeleccionado=Clientes.objects.get(cliente_id=cliente_id_cliente)
    id_mesa_mesa=request.POST["id_mesa_mesa"]
    mesaSeleccionado=Mesas.objects.get(id_mesa=id_mesa_mesa)
    fecha_reserva=request.POST["fecha_reserva"]
    hora_reserva = request.POST.get('hora_reserva', None)
    numero_personas_reserva=request.POST["numero_personas_reserva"]
    estado_reserva=request.POST["estado_reserva"]
    #Insertando datos mediante el ORM de DJANGO
    reservaEditar=Reservas.objects.get(reserva_id=reserva_id)
    reservaEditar.cliente=clienteSeleccionado
    reservaEditar.mesa=mesaSeleccionado
    reservaEditar.fecha_reserva=fecha_reserva
    reservaEditar.hora_reserva=hora_reserva
    reservaEditar.numero_personas_reserva=numero_personas_reserva
    reservaEditar.estado_reserva=estado_reserva
    reservaEditar.save()
    messages.success(request,
      'Reserva ACTUALIZADO Exitosamente')
    return redirect('listadoReservas')

##########################################################################################################################################################
def listadoVentas(request):
    clienteBdd = Clientes.objects.all()
    ventaBdd = Ventas.objects.all()
    return render(request, 'listadoVentas.html', {'ventas': ventaBdd,'clientes':clienteBdd})



def guardarVentas(request):
    cliente_id_cliente=request.POST["cliente_id_cliente"]
    clienteSeleccionado=Clientes.objects.get(cliente_id=cliente_id_cliente)
    fecha_venta=request.POST["fecha_venta"]
    total_venta=request.POST["total_venta"]

    nuevoVentas = Ventas.objects.create(
        fecha_venta=fecha_venta,
        total_venta=total_venta,
        cliente=clienteSeleccionado
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
    clienteBdd = Clientes.objects.all()
    return render(request, 'editarVentas.html', {'ventas': ventaEditar,'clientes':clienteBdd})

def procesarActualizacionVentas(request):
    venta_id=request.POST["venta_id"]
    cliente_id_cliente=request.POST["cliente_id_cliente"]
    clienteSeleccionado=Clientes.objects.get(cliente_id=cliente_id_cliente)
    fecha_venta=request.POST["fecha_venta"]
    total_venta=request.POST["total_venta"]
    #Insertando datos mediante el ORM de DJANGO
    ventaEditar=Ventas.objects.get(venta_id=venta_id)
    ventaEditar.cliente=clienteSeleccionado
    ventaEditar.fecha_venta=fecha_venta
    ventaEditar.total_venta=total_venta
    ventaEditar.save()
    messages.success(request,
      'Venta ACTUALIZADO Exitosamente')
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

def listadoDetalles_Ventas(request):
    detalleBdd = Detalles_Ventas.objects.all()
    ventaBdd = Ventas.objects.all()
    menuBdd = Menus.objects.all()
    return render(request, 'listadoDetalles_Ventas.html', {'detalles': detalleBdd, 'ventas': ventaBdd, 'menus': menuBdd})

def guardarDetalles_Ventas(request):
    venta_id_venta=request.POST["venta_id_venta"]
    ventaSeleccionado=Ventas.objects.get(venta_id=venta_id_venta)
    menu_id_menu=request.POST["menu_id_menu"]
    menuSeleccionado=Menus.objects.get(menu_id=menu_id_menu)
    cantidad_venta=request.POST["cantidad_venta"]
    precio_unitario_venta=request.POST["precio_unitario_venta"]

    nuevodetalle = Detalles_Ventas.objects.create(
        cantidad_venta=cantidad_venta,
        precio_unitario_venta=precio_unitario_venta,
        venta=ventaSeleccionado,
        menu=menuSeleccionado
    )

    messages.success(request, 'Detalles Reservas guardada exitosamente')
    return redirect('listadoDetalles_Ventas')


def eliminarDetalles_Ventas(request, detalle_venta_id):
    try:
        detalles = Detalles_Ventas.objects.get(pk=detalle_venta_id)
        detalles.delete()
        messages.success(request, 'Detalles Ventas eliminado correctamente.')
    except Detalles_Ventas.DoesNotExist:
        messages.error(request, 'Los Detalles Ventas que intentas eliminar no existe.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar el Detalles Ventas porque hay productos relacionados.')
    return redirect('listadoDetalles_Ventas')

def editarDetalles_Ventas(request,detalle_venta_id):
    detalleEditar=Detalles_Ventas.objects.get(detalle_venta_id=detalle_venta_id)
    ventaBdd = Ventas.objects.all()
    menuBdd = Menus.objects.all()
    return render(request, 'editarDetalles_Ventas.html', {'detalles': detalleEditar,'ventas':ventaBdd,'menus':menuBdd })

def procesarActualizacionDetalles(request):
    detalle_venta_id=request.POST["detalle_venta_id"]
    venta_id_venta=request.POST["venta_id_venta"]
    ventaSeleccionado=Ventas.objects.get(venta_id=venta_id_venta)
    menu_id_menu=request.POST["menu_id_menu"]
    menuSeleccionado=Menus.objects.get(menu_id=menu_id_menu)
    cantidad_venta=request.POST["cantidad_venta"]
    precio_unitario_venta=request.POST["precio_unitario_venta"]
    #Insertando datos mediante el ORM de DJANGO
    detalleEditar=Detalles_Ventas.objects.get(detalle_venta_id=detalle_venta_id)
    detalleEditar.menu=menuSeleccionado
    detalleEditar.venta=ventaSeleccionado
    detalleEditar.cantidad_venta=cantidad_venta
    detalleEditar.precio_unitario_venta=precio_unitario_venta
    detalleEditar.save()
    messages.success(request,
      'Detalles Ventas ACTUALIZADO Exitosamente')
    return redirect('listadoDetalles_Ventas')

#############################################################################################################################
def listadoDetalles_Reservas(request):
    detalle_ReservaBdd = Detalles_Reservas.objects.all()
    reservaBdd = Reservas.objects.all()
    menuBdd = Menus.objects.all()
    return render(request, 'listadoDetalles_Reservas.html', {'detalle_Reservas': detalle_ReservaBdd, 'reservas': reservaBdd, 'menus': menuBdd})

def guardarDetalles_Reservas(request):
    reserva_id_reserva=request.POST["reserva_id_reserva"]
    reservaSeleccionado=Reservas.objects.get(reserva_id=reserva_id_reserva)
    menu_id_menu=request.POST["menu_id_menu"]
    menuSeleccionado=Menus.objects.get(menu_id=menu_id_menu)


    nuevodetalle_Reserva = Detalles_Reservas.objects.create(
        reserva=reservaSeleccionado,
        menu=menuSeleccionado
    )

    messages.success(request, 'Detalles Reservas guardada exitosamente')
    return redirect('listadoDetalles_Reservas')


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
    detalle_reserva_id=request.POST["detalle_reserva_id"]
    reserva_id_reserva=request.POST["reserva_id_reserva"]
    reservaSeleccionado=Reservas.objects.get(reserva_id=reserva_id_reserva)
    menu_id_menu=request.POST["menu_id_menu"]
    menuSeleccionado=Menus.objects.get(menu_id=menu_id_menu)

    detalle_ReservaEditar=Detalles_Reservas.objects.get(detalle_reserva_id=detalle_reserva_id)
    detalle_ReservaEditar.menu=menuSeleccionado
    detalle_ReservaEditar.reserva=reservaSeleccionado
    detalle_ReservaEditar.save()
    messages.success(request,
      'Detalles Ventas ACTUALIZADO Exitosamente')
    return redirect('listadoDetalles_Reservas')
########################################################################################################################################################

def listadoPromociones(request):
    promocionBdd = Promociones.objects.all()
    menuBdd = Menus.objects.all()
    return render(request, 'listadoPromociones.html', {'promociones': promocionBdd,'menus':menuBdd})


def guardarPromociones(request):
    menu_id_menu=request.POST["menu_id_menu"]
    menuSeleccionado=Menus.objects.get(menu_id=menu_id_menu)
    descripcion_pro=request.POST["descripcion_pro"]
    fecha_inicio_pro = request.POST.get('fecha_inicio_pro')
    fecha_fin_pro = request.POST.get('fecha_fin_pro')
    descuento_pro=request.POST["descuento_pro"]

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
    promociones_id=request.POST["promociones_id"]
    menu_id_menu=request.POST["menu_id_menu"]
    menuSeleccionado=Menus.objects.get(menu_id=menu_id_menu)
    descripcion_pro=request.POST["descripcion_pro"]
    fecha_inicio_pro = request.POST.get('fecha_inicio_pro')
    fecha_fin_pro = request.POST.get('fecha_fin_pro')
    descuento_pro=request.POST["descuento_pro"]
    #Insertando datos mediante el ORM de DJANGO
    promocionEditar=Promociones.objects.get(promociones_id=promociones_id)
    promocionEditar.menu=menuSeleccionado
    promocionEditar.descripcion_pro=descripcion_pro
    promocionEditar.fecha_inicio_pro=fecha_inicio_pro
    promocionEditar.fecha_fin_pro=fecha_fin_pro
    promocionEditar.descuento_pro=descuento_pro
    promocionEditar.save()
    messages.success(request,
      'Procion ACTUALIZADO Exitosamente')
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
