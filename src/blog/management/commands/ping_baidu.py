from django.core.management.base import BaseCommand

from djangoblog.spider_notify import SpiderNotify
from djangoblog.utils import get_current_site
from blog.models import Article, Tag, Category

# ZFH: 站点域名，用于拼接完整 URL 后通知百度
site = get_current_site().domain


# ZFH: 通知百度命令：将文章、标签、分类等页面 URL 提交给百度蜘蛛
# ZFH: 用法：python manage.py ping_baidu <all|article|tag|category>，用于站点内容更新后推送链接
class Command(BaseCommand):
    help = 'notify baidu url'

    def add_arguments(self, parser):
        # ZFH: 定义可选参数 data_type，支持 all/article/tag/category
        parser.add_argument(
            'data_type',
            type=str,
            choices=[
                'all',
                'article',
                'tag',
                'category'],
            help='article : all article,tag : all tag,category: all category,all: All of these')

    def get_full_url(self, path):
        # ZFH: 将相对路径拼接为带站点域名的完整 URL
        url = "https://{site}{path}".format(site=site, path=path)
        return url

    def handle(self, *args, **options):
        # ZFH: 读取命令行指定的提交类型
        type = options['data_type']
        self.stdout.write('start get %s' % type)

        # ZFH: 收集待通知的 URL 列表
        urls = []
        # ZFH: 收集已发布文章的完整 URL
        if type == 'article' or type == 'all':
            for article in Article.objects.filter(status='p'):
                urls.append(article.get_full_url())
        # ZFH: 收集所有标签的完整 URL
        if type == 'tag' or type == 'all':
            for tag in Tag.objects.all():
                url = tag.get_absolute_url()
                urls.append(self.get_full_url(url))
        # ZFH: 收集所有分类的完整 URL
        if type == 'category' or type == 'all':
            for category in Category.objects.all():
                url = category.get_absolute_url()
                urls.append(self.get_full_url(url))

        # ZFH: 输出本次待通知的 URL 数量
        self.stdout.write(
            self.style.SUCCESS(
                'start notify %d urls' %
                len(urls)))
        # ZFH: 调用 SpiderNotify 将 URL 提交给百度
        SpiderNotify.baidu_notify(urls)
        self.stdout.write(self.style.SUCCESS('finish notify'))
