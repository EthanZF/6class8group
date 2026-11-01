"""oauth 应用包入口。

本文件刻意保持为空：oauth 是标准 Django 应用包，包级不需要初始化逻辑。
Django 通过 apps.py 中的 OauthConfig 完成应用注册，通过 models.py/views.py/urls.py
分别提供模型、视图与路由，因此这里不导入任何子模块，避免循环导入。

SJQ: 模块级注释，说明本包为空文件的原因，避免后来者误以为漏写初始化代码。
"""
