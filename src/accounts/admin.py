# CTY所注：导入 Django 表单模块，用于自定义后台用户表单
from django import forms
# CTY所注：导入 Django 自带的用户后台管理基类 UserAdmin
from django.contrib.auth.admin import UserAdmin
# CTY所注：导入用户修改表单基类和专用的用户名字段控件
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import UsernameField
# CTY所注：导入国际化翻译函数，使提示文案支持多语言
from django.utils.translation import gettext_lazy as _

# Register your models here.
# CTY所注：导入本项目自定义的用户模型 BlogUser
from .models import BlogUser


# CTY所注：后台"添加用户"使用的表单，包含两次密码输入及其一致性校验
class BlogUserCreationForm(forms.ModelForm):
    # CTY所注：第一次输入密码，使用密码输入框（输入内容不可见）
    password1 = forms.CharField(label=_('password'), widget=forms.PasswordInput)
    # CTY所注：第二次输入密码，用于确认两次输入一致
    password2 = forms.CharField(label=_('Enter password again'), widget=forms.PasswordInput)

    class Meta:
        # CTY所注：表单关联的模型为 BlogUser
        model = BlogUser
        # CTY所注：除密码外，添加页面只展示邮箱字段
        fields = ('email',)

    def clean_password2(self):
        # Check that the two password entries match
        # CTY所注：校验两次输入的密码是否一致，不一致则抛出验证错误
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("passwords do not match"))
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        # CTY所注：先不落库，调用 set_password 将明文密码哈希后再保存
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            # CTY所注：标记该用户的注册来源为后台创建
            user.source = 'adminsite'
            user.save()
        return user


# CTY所注：后台"修改用户"使用的表单，继承 Django 自带的 UserChangeForm
class BlogUserChangeForm(UserChangeForm):
    class Meta:
        model = BlogUser
        # CTY所注：展示模型的全部字段
        fields = '__all__'
        # CTY所注：username 字段使用 Django 自带的 UsernameField 控件
        field_classes = {'username': UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# CTY所注：自定义用户后台管理类，配置添加页字段、列表展示、搜索等
class BlogUserAdmin(UserAdmin):
    # CTY所注：修改用户使用 BlogUserChangeForm
    form = BlogUserChangeForm
    # CTY所注：添加用户使用 BlogUserCreationForm
    add_form = BlogUserCreationForm
    # CTY所注：定义"添加用户"页面显示的字段：用户名、邮箱、两次密码
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    # CTY所注：用户列表页展示的列
    list_display = (
        'id',
        'nickname',
        'username',
        'email',
        'last_login',
        'date_joined',
        'source')
    # CTY所注：列表页中可点击进入修改页的列
    list_display_links = ('id', 'username')
    # CTY所注：列表默认按 id 倒序排列（最新创建的排前面）
    ordering = ('-id',)
    # CTY所注：支持按用户名、昵称、邮箱搜索用户
    search_fields = ('username', 'nickname', 'email')
