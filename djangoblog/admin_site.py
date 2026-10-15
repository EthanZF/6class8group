# zfh: 导入 Django 后台管理站点基类 AdminSite
from django.contrib.admin import AdminSite
# zfh: 导入后台操作日志模型 LogEntry
from django.contrib.admin.models import LogEntry
# zfh: 导入站点模型的后台管理类 SiteAdmin
from django.contrib.sites.admin import SiteAdmin
# zfh: 导入站点模型 Site
from django.contrib.sites.models import Site

# zfh: 导入 accounts 应用的后台注册配置
from accounts.admin import *
# zfh: 导入 blog 应用的后台注册配置
from blog.admin import *
# zfh: 导入 blog 应用的模型
from blog.models import *
# zfh: 导入 comments 应用的后台注册配置
from comments.admin import *
# zfh: 导入 comments 应用的模型
from comments.models import *
# zfh: 导入自定义的日志条目后台管理类
from djangoblog.logentryadmin import LogEntryAdmin
# zfh: 导入 oauth 应用的后台注册配置
from oauth.admin import *
# zfh: 导入 oauth 应用的模型
from oauth.models import *
# zfh: 导入 servermanager 应用的后台注册配置
from servermanager.admin import *
# zfh: 导入 servermanager 应用的模型
from servermanager.models import *


# zfh: 项目自定义后台管理站点，继承 Django 的 AdminSite
class DjangoBlogAdminSite(AdminSite):
    # zfh: 后台页面顶部显示的站点标题
    site_header = 'djangoblog administration'
    # zfh: 后台页面浏览器标题栏显示的站点名称
    site_title = 'djangoblog site admin'

    # zfh: 初始化方法，name 为站点在 URL 配置中的名称
    def __init__(self, name='admin'):
        # zfh: 调用父类构造方法完成站点初始化
        super().__init__(name)

    # zfh: 判断当前用户是否有权访问后台
    def has_permission(self, request):
        # zfh: 仅超级用户返回 True
        return request.user.is_superuser

    # def get_urls(self):
    #     urls = super().get_urls()
    #     from django.urls import path
    #     from blog.views import refresh_memcache
    #
    #     my_urls = [
    #         path('refresh/', self.admin_view(refresh_memcache), name="refresh"),
    #     ]
    #     return urls + my_urls


# zfh: 实例化自定义后台站点对象
admin_site = DjangoBlogAdminSite(name='admin')

# zfh: 注册文章模型及其后台管理类
admin_site.register(Article, ArticlelAdmin)
# zfh: 注册分类模型及其后台管理类
admin_site.register(Category, CategoryAdmin)
# zfh: 注册标签模型及其后台管理类
admin_site.register(Tag, TagAdmin)
# zfh: 注册友情链接模型及其后台管理类
admin_site.register(Links, LinksAdmin)
# zfh: 注册侧边栏模型及其后台管理类
admin_site.register(SideBar, SideBarAdmin)
# zfh: 注册博客配置模型及其后台管理类
admin_site.register(BlogSettings, BlogSettingsAdmin)

# zfh: 注册命令模型及其后台管理类
admin_site.register(commands, CommandsAdmin)
# zfh: 注册邮件发送记录模型及其后台管理类
admin_site.register(EmailSendLog, EmailSendLogAdmin)

# zfh: 注册自定义用户模型及其后台管理类
admin_site.register(BlogUser, BlogUserAdmin)

# zfh: 注册评论模型及其后台管理类
admin_site.register(Comment, CommentAdmin)

# zfh: 注册 OAuth 用户模型及其后台管理类
admin_site.register(OAuthUser, OAuthUserAdmin)
# zfh: 注册 OAuth 配置模型及其后台管理类
admin_site.register(OAuthConfig, OAuthConfigAdmin)

# zfh: 注册站点模型及其后台管理类
admin_site.register(Site, SiteAdmin)

# zfh: 注册后台操作日志模型及其自定义管理类
admin_site.register(LogEntry, LogEntryAdmin)
