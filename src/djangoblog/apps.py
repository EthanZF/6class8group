# zfh: 导入 Django 应用配置基类 AppConfig
from django.apps import AppConfig

# zfh: djangoblog 应用的配置类
class DjangoblogAppConfig(AppConfig):
    # zfh: 主键字段默认使用 BigAutoField
    default_auto_field = 'django.db.models.BigAutoField'
    # zfh: 应用名称
    name = 'djangoblog'

    # zfh: 应用加载完成后执行的初始化方法
    def ready(self):
        # zfh: 调用父类的 ready 方法
        super().ready()
        # Import and load plugins here
        # zfh: 导入插件加载函数
        from .plugin_manage.loader import load_plugins
        # zfh: 调用加载函数，加载全部插件
        load_plugins() 