"""
oauth 应用的 AppConfig 模块。

Django 3.2 之后推荐用 AppConfig 显式声明应用名，本模块只做这一件事。
类名 OauthConfig 与模型 OAuthConfig 同名，但两者属于不同命名空间，不冲突。

SJQ: 模块级注释，说明本模块仅承担应用注册职责，并提示类名与模型同名这一易混点。
"""
# SJQ: AppConfig 是应用配置的基类
from django.apps import AppConfig


class OauthConfig(AppConfig):
    """oauth 应用的配置类，Django 启动时按 name 定位包。"""

    # SJQ: 应用包名，必须与 INSTALLED_APPS 中的 'oauth' 一致
    name = 'oauth'
