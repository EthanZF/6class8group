#!/usr/bin/env python
# encoding: utf-8

# zfh: Django Blog 基础视图类，提供带常用装饰器的视图基类
"""
Django Blog 基础视图类
提供带有常用装饰器的视图基类，减少重复的 dispatch 方法定义
"""

# zfh: 导入 login_required 装饰器，限制视图必须登录后访问
from django.contrib.auth.decorators import login_required
# zfh: 导入 method_decorator，把函数装饰器应用到类方法上
from django.utils.decorators import method_decorator
# zfh: 导入 never_cache，禁止浏览器和中间件缓存响应
from django.views.decorators.cache import never_cache
# zfh: 导入 csrf_protect，为视图开启 CSRF 防护
from django.views.decorators.csrf import csrf_protect
# zfh: 导入 sensitive_post_parameters，避免密码等敏感参数被写入错误报告
from django.views.decorators.debug import sensitive_post_parameters
# zfh: 导入 FormView 与 RedirectView 两个通用视图基类
from django.views.generic import FormView, RedirectView


# zfh: 带 CSRF 保护的表单视图基类
class SecureFormView(FormView):
    """
    安全的 FormView 基类

    自动添加 CSRF 保护，适用于所有需要表单提交的视图

    Usage:
        class MyFormView(SecureFormView):
            form_class = MyForm
            template_name = 'my_form.html'

            def form_valid(self, form):
                # 处理表单数据
                return super().form_valid(form)
    """

    # zfh: 用 csrf_protect 装饰 dispatch，使所有请求方法都经过 CSRF 校验
    @method_decorator(csrf_protect)
    # zfh: 重写 dispatch，作为该类所有请求方法的统一入口
    def dispatch(self, *args, **kwargs):
        """添加 CSRF 保护"""
        # zfh: 调用父类 dispatch，继续正常的视图分发流程
        return super().dispatch(*args, **kwargs)


# zfh: 需要登录的表单视图基类
class AuthenticatedFormView(FormView):
    """
    需要登录的 FormView

    自动检查用户登录状态并添加 CSRF 保护
    未登录用户会被重定向到登录页面

    Usage:
        class MyAuthFormView(AuthenticatedFormView):
            form_class = MyForm
            template_name = 'my_form.html'
    """

    # zfh: 用 login_required 装饰 dispatch，未登录用户跳转到登录页
    @method_decorator(login_required)
    # zfh: 用 csrf_protect 装饰 dispatch，开启 CSRF 校验
    @method_decorator(csrf_protect)
    # zfh: 重写 dispatch，统一处理登录检查与 CSRF 保护
    def dispatch(self, *args, **kwargs):
        """添加登录要求和 CSRF 保护"""
        # zfh: 调用父类 dispatch，继续正常的视图分发流程
        return super().dispatch(*args, **kwargs)


# zfh: 登录专用表单视图基类
class LoginFormView(FormView):
    """
    登录专用 FormView

    包含以下保护措施：
    - 敏感参数保护（password 等）
    - CSRF 保护
    - 禁用缓存（防止登录状态被缓存）

    Usage:
        class LoginView(LoginFormView):
            form_class = LoginForm
            template_name = 'login.html'

            def form_valid(self, form):
                # 处理登录逻辑
                return super().form_valid(form)
    """

    # zfh: 用 sensitive_post_parameters 装饰 dispatch，过滤 password 参数
    @method_decorator(sensitive_post_parameters('password'))
    # zfh: 用 csrf_protect 装饰 dispatch，开启 CSRF 校验
    @method_decorator(csrf_protect)
    # zfh: 用 never_cache 装饰 dispatch，禁止缓存登录页面
    @method_decorator(never_cache)
    # zfh: 重写 dispatch，统一应用登录页的三项保护措施
    def dispatch(self, request, *args, **kwargs):
        """添加敏感参数保护、CSRF 保护和禁用缓存"""
        # zfh: 调用父类 dispatch，继续正常的视图分发流程
        return super().dispatch(request, *args, **kwargs)


# zfh: 登出专用重定向视图基类
class LogoutRedirectView(RedirectView):
    """
    登出专用 RedirectView

    自动禁用缓存，确保登出操作不会被缓存

    Usage:
        class LogoutView(LogoutRedirectView):
            url = '/login/'

            def get(self, request, *args, **kwargs):
                logout(request)
                return super().get(request, *args, **kwargs)
    """

    # zfh: 用 never_cache 装饰 dispatch，禁止缓存登出响应
    @method_decorator(never_cache)
    # zfh: 重写 dispatch，作为登出请求的统一入口
    def dispatch(self, request, *args, **kwargs):
        """禁用缓存"""
        # zfh: 调用父类 dispatch，继续正常的视图分发流程
        return super().dispatch(request, *args, **kwargs)


# zfh: 禁用缓存的表单视图基类
class NoCacheFormView(FormView):
    """
    禁用缓存的 FormView

    适用于需要实时数据的表单（如验证码、动态内容等）

    Usage:
        class MyCacheDisabledFormView(NoCacheFormView):
            form_class = MyForm
            template_name = 'my_form.html'
    """

    # zfh: 用 never_cache 装饰 dispatch，禁止缓存表单页面
    @method_decorator(never_cache)
    # zfh: 用 csrf_protect 装饰 dispatch，开启 CSRF 校验
    @method_decorator(csrf_protect)
    # zfh: 重写 dispatch，统一应用禁用缓存与 CSRF 保护
    def dispatch(self, request, *args, **kwargs):
        """禁用缓存并添加 CSRF 保护"""
        # zfh: 调用父类 dispatch，继续正常的视图分发流程
        return super().dispatch(request, *args, **kwargs)
