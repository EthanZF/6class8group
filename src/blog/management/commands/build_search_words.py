from django.core.management.base import BaseCommand

from blog.models import Tag, Category


# TODO 参数化
# ZFH: 构建搜索词命令：汇总所有标签与分类名称，输出为搜索提示词
# ZFH: 用法：python manage.py build_search_words，输出结果可作为搜索框的候选提示词
class Command(BaseCommand):
    help = 'build search words'

    def handle(self, *args, **options):
        # ZFH: 收集全部标签名与分类名，并用 set 去重
        datas = set([t.name for t in Tag.objects.all()] +
                    [t.name for t in Category.objects.all()])
        # ZFH: 逐行打印去重后的搜索词
        print('\n'.join(datas))
