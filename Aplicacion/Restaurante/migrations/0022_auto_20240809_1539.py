# Generated by Django 3.2.25 on 2024-08-09 20:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Restaurante', '0021_similitudusuarios'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preferenciasusuario',
            name='cliente',
        ),
        migrations.RemoveField(
            model_name='preferenciasusuario',
            name='menus_favoritos',
        ),
        migrations.AlterUniqueTogether(
            name='similitudusuarios',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='similitudusuarios',
            name='usuario1',
        ),
        migrations.RemoveField(
            model_name='similitudusuarios',
            name='usuario2',
        ),
        migrations.DeleteModel(
            name='HistorialInteracciones',
        ),
        migrations.DeleteModel(
            name='PreferenciasUsuario',
        ),
        migrations.DeleteModel(
            name='SimilitudUsuarios',
        ),
    ]
