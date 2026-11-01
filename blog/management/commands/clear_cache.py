from django.core.management.base import BaseCommand

from djangoblog.utils import cache


# ZFH: 清空缓存命令：清理系统中缓存的全部数据
# ZFH: 用法：python manage.py clear_cache，用于数据更新后手动刷新缓存
class Command(BaseCommand):
    help = 'clear the whole cache'

    def handle(self, *args, **options):
        # ZFH: 调用缓存工具清空整个缓存
        cache.clear()
        # ZFH: 输出成功提示信息
        self.stdout.write(self.style.SUCCESS('Cleared cache\n'))
