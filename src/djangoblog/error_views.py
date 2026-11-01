#!/usr/bin/env python
# encoding: utf-8

# zfh: Django Blog 统一错误处理视图，集中渲染各类错误页面
"""
Django Blog 统一错误处理视图
提供统一的错误页面渲染，减少重复代码
"""

# zfh: 导入 logging 模块，用于记录错误日志
import logging
# zfh: 导入 render，把模板渲染为 HttpResponse
from django.shortcuts import render
# zfh: 导入 gettext_lazy，延迟翻译错误提示文本
from django.utils.translation import gettext_lazy as _

# zfh: 以当前模块名创建 logger 对象
logger = logging.getLogger(__name__)


# zfh: 通用错误页面渲染函数，统一处理各类 HTTP 错误
def render_error_page(request, status_code, message, exception=None):
    """
    通用错误页面渲染函数

    统一处理各种 HTTP 错误，提供一致的错误页面展示

    Args:
        request: HTTP 请求对象
        status_code: HTTP 状态码（404, 403, 500等）
        message: 错误消息（支持国际化）
        exception: 异常对象（可选），会被记录到日志

    Returns:
        HttpResponse: 渲染后的错误页面

    Usage:
        def my_error_handler(request, exception):
            return render_error_page(request, 404, "Page not found", exception)
    """
    # zfh: 如果传入了异常对象，则记录错误日志
    if exception:
        # zfh: 记录错误日志，exc_info 为 True 时附带异常堆栈
        logger.error(
            f'HTTP {status_code} Error: {exception}',
            exc_info=True,
            extra={
                'request': request,
                'status_code': status_code
            }
        )

    # zfh: 渲染错误页模板并返回指定状态码的响应
    return render(
        request,
        'blog/error_page.html',
        {
            'message': message,
            'statuscode': str(status_code)
        },
        status=status_code
    )


# zfh: 404 错误页面处理器
def page_not_found_view(request, exception, template_name='blog/error_page.html'):
    """
    404 错误页面处理器

    当用户访问不存在的页面时显示

    Args:
        request: HTTP 请求对象
        exception: 异常对象
        template_name: 模板名称（保留参数以兼容 Django 标准）

    Returns:
        HttpResponse: 404 错误页面
    """
    # zfh: 调用通用渲染函数，返回 404 页面与未找到提示
    return render_error_page(
        request,
        404,
        _('Sorry, the page you requested is not found, please click the home page to see other?'),
        exception
    )


# zfh: 500 错误页面处理器
def server_error_view(request, template_name='blog/error_page.html'):
    """
    500 错误页面处理器

    当服务器内部错误时显示

    Args:
        request: HTTP 请求对象
        template_name: 模板名称（保留参数以兼容 Django 标准）

    Returns:
        HttpResponse: 500 错误页面
    """
    # zfh: 调用通用渲染函数，返回 500 页面与服务器繁忙提示
    return render_error_page(
        request,
        500,
        _('Sorry, the server is busy, please click the home page to see other?')
    )


# zfh: 403 错误页面处理器
def permission_denied_view(request, exception, template_name='blog/error_page.html'):
    """
    403 错误页面处理器

    当用户无权限访问时显示

    Args:
        request: HTTP 请求对象
        exception: 异常对象
        template_name: 模板名称（保留参数以兼容 Django 标准）

    Returns:
        HttpResponse: 403 错误页面
    """
    # zfh: 调用通用渲染函数，返回 403 页面与无权限提示
    return render_error_page(
        request,
        403,
        _('Sorry, you do not have permission to access this page?'),
        exception
    )


# zfh: 400 错误页面处理器
def bad_request_view(request, exception, template_name='blog/error_page.html'):
    """
    400 错误页面处理器

    当请求格式错误时显示

    Args:
        request: HTTP 请求对象
        exception: 异常对象
        template_name: 模板名称（保留参数以兼容 Django 标准）

    Returns:
        HttpResponse: 400 错误页面
    """
    # zfh: 调用通用渲染函数，返回 400 页面与请求无效提示
    return render_error_page(
        request,
        400,
        _('Sorry, the request was invalid?'),
        exception
    )
