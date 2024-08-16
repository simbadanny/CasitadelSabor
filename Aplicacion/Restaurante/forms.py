from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email


class LoginForm(forms.Form):
    username = forms.CharField(label='Nombre de usuario o Correo electrónico')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if '@' in username:
            # Validar si el correo electrónico existe
            from django.contrib.auth.models import User
            if not User.objects.filter(email=username).exists():
                raise forms.ValidationError("El correo electrónico incorrecto o no está registrado.")
        else:
            # Validar si el nombre de usuario existe
            from django.contrib.auth.models import User
            if not User.objects.filter(username=username).exists():
                raise forms.ValidationError("El nombre de usuario incorrecto o no está registrado.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError("La combinación de nombre de usuario/correo electrónico y contraseña es incorrecta.")

        return cleaned_data
