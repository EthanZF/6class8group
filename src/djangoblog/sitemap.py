# zfh: 导入 Django 站点地图基类 Sitemap
from django.contrib.sitemaps import Sitemap
# zfh: 导入 reverse，用于把路由名反向解析成 URL
from django.urls import reverse

# zfh: 导入文章、分类、标签模型，供站点地图取数据
from blog.models import Article, Category, Tag


# zfh: 静态视图站点地图，收录首页等固定页面
class StaticViewSitemap(Sitemap):
    # zfh: 该站点地图的页面优先级
    priority = 0.5
    # zfh: 更新频率为每天
    changefreq = 'daily'

    # zfh: 返回该站点地图包含的视图名列表
    def items(self):
        # zfh: 只包含博客首页的路由名
        return ['blog:index', ]

    # zfh: 返回条目对应的实际 URL
    def location(self, item):
        # zfh: 用路由名反向解析出首页地址
        return reverse(item)


# zfh: 文章站点地图，收录所有已发布的文章
class ArticleSiteMap(Sitemap):
    # zfh: 更新频率为每月
    changefreq = "monthly"
    # zfh: 页面优先级
    priority = "0.6"

    # zfh: 返回已发布文章组成的查询集
    def items(self):
        # zfh: 筛选 status 为 p（已发布）的文章
        return Article.objects.filter(status='p')

    # zfh: 返回该文章的最后修改时间
    def lastmod(self, obj):
        # zfh: 取文章的最后修改时间作为 lastmod
        return obj.last_modify_time


# zfh: 分类站点地图，收录所有分类页面
class CategorySiteMap(Sitemap):
    # zfh: 更新频率为每周
    changefreq = "Weekly"
    # zfh: 页面优先级
    priority = "0.6"

    # zfh: 返回全部分类组成的查询集
    def items(self):
        # zfh: 查询所有分类对象
        return Category.objects.all()

    # zfh: 返回该分类的最后修改时间
    def lastmod(self, obj):
        # zfh: 取分类的最后修改时间作为 lastmod
        return obj.last_modify_time


# zfh: 标签站点地图，收录所有标签页面
class TagSiteMap(Sitemap):
    # zfh: 更新频率为每周
    changefreq = "Weekly"
    # zfh: 页面优先级
    priority = "0.3"

    # zfh: 返回全部标签组成的查询集
    def items(self):
        # zfh: 查询所有标签对象
        return Tag.objects.all()

    # zfh: 返回该标签的最后修改时间
    def lastmod(self, obj):
        # zfh: 取标签的最后修改时间作为 lastmod
        return obj.last_modify_time


# zfh: 用户站点地图，收录所有文章作者的个人主页
class UserSiteMap(Sitemap):
    # zfh: 更新频率为每周
    changefreq = "Weekly"
    # zfh: 页面优先级
    priority = "0.3"

    # zfh: 返回所有发表过文章的作者
    def items(self):
        # zfh: 取出全部文章的作者并用集合去重
        return list(set(map(lambda x: x.author, Article.objects.all())))

    # zfh: 返回该用户的注册时间
    def lastmod(self, obj):
        # zfh: 取用户注册时间作为 lastmod
        return obj.date_joined
