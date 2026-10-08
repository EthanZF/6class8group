"""djangoblog URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))

=====================================================================
本文件是整个项目的【总路由表】:浏览器访问的每一个网址,都由这里
决定交给谁来处理。分发规则:
  1. Django 从 urlpatterns 里自上而下逐条匹配,命中即停止;
  2. include() 把请求转发给各子应用的 urls.py 继续匹配;
  3. 各子应用自己维护自己的路由,本文件只负责"分流量"。
=====================================================================
"""
# ==================== 导入模块 ====================
from django.conf import settings            # 读取全局配置(settings.py 里的变量)
from django.conf.urls.i18n import i18n_patterns  # 带语言前缀的路由(如 /en/...、/zh-hans/...)
from django.conf.urls.static import static  # 让 Django 在开发模式下提供静态/媒体文件服务
from django.contrib.sitemaps.views import sitemap  # 站点地图视图(生成 sitemap.xml,给搜索引擎看)
from django.urls import path, include       # path:普通路由;include:转发给子应用路由表
from django.urls import re_path             # 正则路由(用正则表达式匹配 URL)
from haystack.views import search_view_factory    # haystack 搜索视图工厂(生成搜索页视图)
from django.http import JsonResponse        # 直接返回 JSON 数据的响应类
import time                                 # 取时间戳(健康检查接口用)

from blog.views import EsSearchView                                          # 全文搜索视图(对接 Elasticsearch)
from djangoblog.admin_site import admin_site                                 # 自定义的后台管理站点(非 Django 默认 admin)
from djangoblog.elasticsearch_backend import ElasticSearchModelSearchForm    # ES 搜索表单(定义搜哪些字段)
from djangoblog.feeds import DjangoBlogFeed                                  # RSS 订阅源(文章 feed 流)
from djangoblog.sitemap import ArticleSiteMap, CategorySiteMap, StaticViewSitemap, TagSiteMap, UserSiteMap
                              # ↑ 五种站点地图:文章/分类/静态页/标签/用户,各自定义"哪些网址要被收录"

# ==================== 站点地图注册 ====================
# sitemap.xml 会按下面 5 个分区罗列全站可被搜索引擎收录的网址
sitemaps = {

    'blog': ArticleSiteMap,          # 所有文章的网址
    'Category': CategorySiteMap,     # 所有分类的网址
    'Tag': TagSiteMap,               # 所有标签的网址
    'User': UserSiteMap,             # 所有用户的网址
    'static': StaticViewSitemap      # 关于我们等静态页面的网址
}

# ==================== 自定义错误页 ====================
# 把 HTTP 错误码指向自己写的视图(代替 Django 默认的英文错误页)
handler404 = 'blog.views.page_not_found_view'     # 404 页面不存在 → blog 应用里的自定义视图
handler500 = 'blog.views.server_error_view'       # 500 服务器内部错误 → 自定义视图
handle403 = 'blog.views.permission_denied_view'   # ⚠ 注意:Django 认的标准名是 handler403,
                                                  # 这里写成 handle403(少了 r)实际不会生效,
                                                  # 403 会仍走 Django 默认页面——属原项目遗留拼写问题,
                                                  # 标注时不修改代码,如需生效请自行更名


# ==================== 健康检查接口 ====================
def health_check(request):
    """
    健康检查接口
    简单返回服务健康状态
    用途:运维/负载均衡/监控平台定时访问 /health/,
          只要能返回 JSON 就说明服务活着(容器编排的探活针常指向它)
    """
    return JsonResponse({
        'status': 'healthy',      # 固定返回 healthy 表示服务正常
        'timestamp': time.time()  # 当前时间戳,证明响应是实时生成的而非缓存
    })

# ==================== 基础路由(不带语言前缀) ====================
urlpatterns = [
    # 语言切换:处理 /i18n/setlang/ 等请求,把用户选的语言写进 cookie
    path('i18n/', include('django.conf.urls.i18n')),
    # 健康检查:GET /health/ 返回服务状态 JSON
    path('health/', health_check, name='health_check'),
]

# ==================== 业务路由(带国际化支持) ====================
# i18n_patterns 会给包在里面的路由自动加语言前缀,如 /en/admin/、/zh-hans/admin/;
# prefix_default_language=False 表示默认语言(简体中文)不加前缀——
# 中文用户访问 /admin/ 直接命中,英文用户才需要 /en/ 开头,URL 更干净。
urlpatterns += i18n_patterns(
    # 后台管理:/admin/ → 自定义管理站点(djangoblog/admin_site.py)
    re_path(r'^admin/', admin_site.urls),
    # 博客核心:前缀为空,由 blog/urls.py 处理首页、文章详情、归档、分类、标签等
    re_path(r'', include('blog.urls', namespace='blog')),
    # Markdown 编辑器:/mdeditor/ 提供编辑器图片上传等接口
    re_path(r'mdeditor/', include('mdeditor.urls')),
    # 评论模块:前缀为空,具体路径在 comments/urls.py 里定义
    re_path(r'', include('comments.urls', namespace='comment')),
    # 用户模块:登录/注册/找回密码等,前缀为空
    re_path(r'', include('accounts.urls', namespace='account')),
    # 第三方登录:OAuth 授权回调等,前缀为空
    re_path(r'', include('oauth.urls', namespace='oauth')),
    # 站点地图:GET /sitemap.xml → 汇总上面 5 种 sitemap 输出给搜索引擎
    re_path(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps},
            name='django.contrib.sitemaps.views.sitemap'),
    # RSS 订阅:两个网址等价,都是输出全站文章的 RSS feed
    re_path(r'^feed/$', DjangoBlogFeed()),
    re_path(r'^rss/$', DjangoBlogFeed()),
    # 站内搜索:/search?q=关键词 → haystack + Elasticsearch 全文搜索
    re_path('^search', search_view_factory(view_class=EsSearchView, form_class=ElasticSearchModelSearchForm),
            name='search'),
    # 服务器管理模块:前缀为空,路径在 servermanager/urls.py 里定义
    re_path(r'', include('servermanager.urls', namespace='servermanager'))
    , prefix_default_language=False) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # ↑ static(...):把 /static/xxx 映射到 collectedstatic 目录(开发模式兜底;生产由 Nginx 处理)
    # ⚠ 注意:多个 include 前缀为空时按顺序匹配,所以"前缀为空"的模块放的位置会影响
    #   更具体的路由(如 ^admin/)必须排在前面,否则可能被空前缀的路由提前"截胡"。

# ==================== 媒体文件(仅开发模式) ====================
# DEBUG=True 时,让 /media/xxx 能访问 uploads/ 目录里的用户上传文件;
# 生产环境(DEBUG=False)这段不生效,必须交给 Nginx 等服务器处理
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
