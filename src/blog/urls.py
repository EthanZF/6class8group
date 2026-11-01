# ZFH: 博客应用的路由配置，将各 URL 映射到对应的视图
# ZFH: 导入 URL 路由函数与整页缓存装饰器
from django.urls import path
from django.views.decorators.cache import cache_page

# ZFH: 引入当前应用的视图模块，供下方路由逐条映射
from . import views

app_name = "blog"  # ZFH: 命名空间，模板/代码中可用 blog:xxx 反向解析
# ZFH: 路由表：按“首页/详情/分类/作者/标签/归档/链接/上传/缓存清理”的顺序注册
urlpatterns = [
    # ZFH: 首页
    path(
        r'',
        views.IndexView.as_view(),
        name='index'),
    # ZFH: 首页分页
    path(
        r'page/<int:page>/',
        views.IndexView.as_view(),
        name='index_page'),
    # ZFH: 文章详情，URL 含年月日与文章ID
    path(
        r'article/<int:year>/<int:month>/<int:day>/<int:article_id>.html',
        views.ArticleDetailView.as_view(),
        name='detailbyid'),
    # ZFH: 分类详情首页
    path(
        r'category/<slug:category_name>.html',
        views.CategoryDetailView.as_view(),
        name='category_detail'),
    # ZFH: 分类详情分页
    path(
        r'category/<slug:category_name>/<int:page>.html',
        views.CategoryDetailView.as_view(),
        name='category_detail_page'),
    # ZFH: 作者详情首页
    path(
        r'author/<author_name>.html',
        views.AuthorDetailView.as_view(),
        name='author_detail'),
    # ZFH: 作者详情分页
    path(
        r'author/<author_name>/<int:page>.html',
        views.AuthorDetailView.as_view(),
        name='author_detail_page'),
    # ZFH: 标签详情首页
    path(
        r'tag/<slug:tag_name>.html',
        views.TagDetailView.as_view(),
        name='tag_detail'),
    # ZFH: 标签详情分页
    path(
        r'tag/<slug:tag_name>/<int:page>.html',
        views.TagDetailView.as_view(),
        name='tag_detail_page'),
    # ZFH: 归档页，使用 cache_page 缓存 1 小时（60*60 秒）
    path(
        'archives.html',
        cache_page(
            60 * 60)(
            views.ArchivesView.as_view()),
        name='archives'),
    # ZFH: 友情链接页
    path(
        'links.html',
        views.LinkListView.as_view(),
        name='links'),
    # ZFH: 文件上传接口（函数视图）
    path(
        r'upload',
        views.fileupload,
        name='upload'),
    # ZFH: 清理缓存接口（函数视图）
    path(
        r'clean',
        views.clean_cache_view,
        name='clean'),
]
