#!/usr/bin/env python
# encoding: utf-8

"""
Django Blog 基础视图类
提供带有常用装饰器的视图基类，减少重复的 dispatch 方法定义
"""

# PSJ login_required：把"必须登录"这个检查做成装饰器，加到视图上即可生效。
from django.contrib.auth.decorators import login_required
# PSJ method_decorator：把给函数用的装饰器转成能给类方法用的形式。
# PSJ 下面这些视图保护装饰器原本都是为函数视图写的，用在方法上必须经过它转换。
from django.utils.decorators import method_decorator
# PSJ never_cache：告诉浏览器和缓存不要保存这个响应，避免把页面缓存下来。
from django.views.decorators.cache import never_cache
# PSJ csrf_protect：强制校验 CSRF 令牌，防止跨站请求伪造。
from django.views.decorators.csrf import csrf_protect
# PSJ sensitive_post_parameters：把指定参数（如 password）从错误报告里屏蔽掉，
# PSJ 避免出错时的调试页面把密码原文显示出来。
from django.views.decorators.debug import sensitive_post_parameters
# PSJ FormView 是"处理表单"的通用视图基类；RedirectView 是"重定向"的通用视图基类。
from django.views.generic import FormView, RedirectView


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

    # PSJ dispatch 是请求进入视图的第一个入口：不管 GET 还是 POST 都先走它。
    # PSJ 在这里统一加 CSRF 保护，子类就不用各自重复写了。
    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        """添加 CSRF 保护"""
        # PSJ 加完保护后交回父类继续处理，父类会按请求方法分发到 get()/post()。
        return super().dispatch(*args, **kwargs)


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

    # PSJ 装饰器可以叠加（多个 @ 自上而下包裹）。
    # PSJ 这里先要求登录，再校验 CSRF；未登录用户会被跳到登录页，不会执行到表单处理。
    @method_decorator(login_required)
    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        """添加登录要求和 CSRF 保护"""
        return super().dispatch(*args, **kwargs)


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

    # PSJ 登录页涉及密码，所以三层保护叠加：
    # PSJ 1) 把 password 参数标记为敏感，出错时不回显；
    # PSJ 2) 校验 CSRF 令牌；
    # PSJ 3) 禁止缓存，防止登录后的页面被别处读取。
    @method_decorator(sensitive_post_parameters('password'))
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        """添加敏感参数保护、CSRF 保护和禁用缓存"""
        return super().dispatch(request, *args, **kwargs)


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

    # PSJ 登出后如果页面被缓存，用户点"后退"可能看到已登出的内容，
    # PSJ 所以这里同样禁用缓存。
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        """禁用缓存"""
        return super().dispatch(request, *args, **kwargs)


class NoCacheFormView(FormView):
    """
    禁用缓存的 FormView

    适用于需要实时数据的表单（如验证码、动态内容等）

    Usage:
        class MyCacheDisabledFormView(NoCacheFormView):
            form_class = MyForm
            template_name = 'my_form.html'
    """

    # PSJ 需要实时数据的表单（例如带验证码的页面）不能走缓存，
    # PSJ 否则刷新后可能拿到旧数据；这里同时保留 CSRF 保护。
    @method_decorator(never_cache)
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        """禁用缓存并添加 CSRF 保护"""
        return super().dispatch(request, *args, **kwargs)
