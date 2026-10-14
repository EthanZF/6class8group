from django.urls import path
from django.urls import re_path

from . import views
from .forms import LoginForm

# CTY所注：应用命名空间，reverse 或模板 {% url %} 中以 "accounts:xxx" 形式引用本应用路由
app_name = "accounts"

# CTY所注：accounts 应用的 URL 路由表
urlpatterns = [# CTY所注：登录页路由，通过 kwargs 指定使用自定义的 LoginForm 表单
               re_path(r'^login/$',
                       views.LoginView.as_view(success_url='/'),
                       name='login',
                       kwargs={'authentication_form': LoginForm}),
               # CTY所注：注册页路由，注册成功后跳转到首页
               re_path(r'^register/$',
                       views.RegisterView.as_view(success_url="/"),
                       name='register'),
               # CTY所注：退出登录路由
               re_path(r'^logout/$',
                       views.LogoutView.as_view(),
                       name='logout'),
               # CTY所注：操作结果提示页（注册成功、邮箱验证成功等）
               path(r'account/result.html',
                    views.account_result,
                    name='result'),
               # CTY所注：忘记密码（重置密码）页路由
               re_path(r'^forget_password/$',
                       views.ForgetPasswordView.as_view(),
                       name='forget_password'),
               # CTY所注：发送重置密码邮箱验证码的接口路由
               re_path(r'^forget_password_code/$',
                       views.ForgetPasswordEmailCode.as_view(),
                       name='forget_password_code'),
               ]
