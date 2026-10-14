# CTY所注：导入 Django 表单基类
from django import forms
# CTY所注：get_user_model 获取当前项目启用的用户模型；password_validation 用于密码强度校验
from django.contrib.auth import get_user_model, password_validation
# CTY所注：导入登录认证表单和用户创建（注册）表单基类
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
# CTY所注：导入表单验证异常类
from django.core.exceptions import ValidationError
# CTY所注：导入表单控件模块（文本框、密码框、邮箱框等）
from django.forms import widgets
# CTY所注：导入国际化翻译函数，支持多语言提示
from django.utils.translation import gettext_lazy as _
from . import utils
from .models import BlogUser


# CTY所注：登录表单，继承 Django 认证表单，仅定制输入框的占位符与样式
class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        # CTY所注：用户名输入框，设置占位符和 Bootstrap 样式类
        self.fields['username'].widget = widgets.TextInput(
            attrs={'placeholder': "username", "class": "form-control"})
        # CTY所注：密码输入框，设置占位符和样式类
        self.fields['password'].widget = widgets.PasswordInput(
            attrs={'placeholder': "password", "class": "form-control"})


# CTY所注：注册表单，继承 Django 用户创建表单，额外增加邮箱唯一性校验
class RegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)

        # CTY所注：依次为 用户名/邮箱/密码/确认密码 输入框设置占位符与样式
        self.fields['username'].widget = widgets.TextInput(
            attrs={'placeholder': "username", "class": "form-control"})
        self.fields['email'].widget = widgets.EmailInput(
            attrs={'placeholder': "email", "class": "form-control"})
        self.fields['password1'].widget = widgets.PasswordInput(
            attrs={'placeholder': "password", "class": "form-control"})
        self.fields['password2'].widget = widgets.PasswordInput(
            attrs={'placeholder': "repeat password", "class": "form-control"})

    def clean_email(self):
        # CTY所注：校验邮箱是否已被注册，已存在则抛出验证错误
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email=email).exists():
            raise ValidationError(_("email already exists"))
        return email

    class Meta:
        # CTY所注：关联当前项目启用的用户模型（即 BlogUser）
        model = get_user_model()
        # CTY所注：注册页显示用户名和邮箱字段（两个密码字段由父类提供）
        fields = ("username", "email")


# CTY所注：忘记密码（重置密码）表单，包含新密码、邮箱和邮箱验证码
class ForgetPasswordForm(forms.Form):
    # CTY所注：新密码输入框
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                'placeholder': _("New password")
            }
        ),
    )

    # CTY所注：确认新密码输入框
    new_password2 = forms.CharField(
        label="确认密码",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                'placeholder': _("Confirm password")
            }
        ),
    )

    # CTY所注：账号绑定的邮箱输入框
    email = forms.EmailField(
        label='邮箱',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _("Email")
            }
        ),
    )

    # CTY所注：邮箱验证码输入框
    code = forms.CharField(
        label=_('Code'),
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _("Code")
            }
        ),
    )

    def clean_new_password2(self):
        # CTY所注：校验两次新密码是否一致，并调用 Django 自带的密码强度校验
        password1 = self.data.get("new_password1")
        password2 = self.data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(_("passwords do not match"))
        password_validation.validate_password(password2)

        return password2

    def clean_email(self):
        # CTY所注：校验邮箱对应的用户是否存在，不存在则报错
        user_email = self.cleaned_data.get("email")
        if not BlogUser.objects.filter(
                email=user_email
        ).exists():
            # todo 这里的报错提示可以判断一个邮箱是不是注册过，如果不想暴露可以修改
            raise ValidationError(_("email does not exist"))
        return user_email

    def clean_code(self):
        # CTY所注：调用 utils.verify 校验邮箱验证码是否正确（与缓存中保存的验证码比对）
        code = self.cleaned_data.get("code")
        error = utils.verify(
            email=self.cleaned_data.get("email"),
            code=code,
        )
        if error:
            raise ValidationError(error)
        return code


# CTY所注：发送重置密码验证码的表单，仅需填写邮箱
class ForgetPasswordCodeForm(forms.Form):
    email = forms.EmailField(
        label=_('Email'),
    )
