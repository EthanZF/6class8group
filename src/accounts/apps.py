"""
CTY所注：accounts 应用配置模块
模块功能：声明 accounts（账户认证）应用的配置类，Django 启动时通过它加载应用，
在 settings 的 INSTALLED_APPS 中注册生效。
"""
from django.apps import AppConfig


# CTY所注：accounts 应用的配置类，Django 启动时会加载它
class AccountsConfig(AppConfig):
    # CTY所注：应用名称，需与应用目录名保持一致
    name = 'accounts'
