from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Master, PhoneVerification

class PhoneRegistrationForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67',
            'type': 'tel'
        })
    )
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваше имя'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваша фамилия'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if CustomUser.objects.filter(phone=phone).exists():
            raise forms.ValidationError('Пользователь с таким телефоном уже существует')
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Пароли не совпадают')
        
        return cleaned_data

class PhoneVerificationForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': 'Введите код из 6 цифр',
            'type': 'text',
            'maxlength': '6'
        })
    )