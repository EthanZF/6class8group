from django.apps import AppConfig


# CTY所注：accounts 应用的配置类，Django 启动时会加载它
class AccountsConfig(AppConfig):
    # CTY所注：应用名称，需与应用目录名保持一致
    name = 'accounts'
