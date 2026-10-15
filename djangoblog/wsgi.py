"""
WSGI config for djangoblog project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

# zfh: djangoblog 项目的 WSGI 配置，把 Django 应用暴露为 WSGI 可调用对象
# zfh: 导入 os 模块，用于设置环境变量
import os

# zfh: 导入 Django 的 WSGI 应用获取函数
from django.core.wsgi import get_wsgi_application

# zfh: 设置默认使用的 Django 配置文件
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangoblog.settings")

# zfh: 创建 WSGI 应用对象，供 Web 服务器调用
application = get_wsgi_application()
