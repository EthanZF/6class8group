from django.core.management.base import BaseCommand

from blog.documents import ElapsedTimeDocument, ArticleDocumentManager, ElaspedTimeDocumentManager, \
    ELASTICSEARCH_ENABLED


# TODO 参数化
# ZFH: 重建搜索索引命令：当启用 Elasticsearch 时，重建文章与耗时统计文档的索引
# ZFH: 用法：python manage.py build_index，执行前需确保配置中已开启 Elasticsearch
class Command(BaseCommand):
    help = 'build search index'

    def handle(self, *args, **options):
        # ZFH: 仅当 Elasticsearch 已启用时才执行索引构建逻辑
        if ELASTICSEARCH_ENABLED:
            # ZFH: 先构建耗时统计文档的索引
            ElaspedTimeDocumentManager.build_index()
            # ZFH: 初始化耗时统计文档对象
            manager = ElapsedTimeDocument()
            manager.init()
            # ZFH: 获取文章文档管理器
            manager = ArticleDocumentManager()
            # ZFH: 先删除旧索引，避免数据残留
            manager.delete_index()
            # ZFH: 重新构建文章索引
            manager.rebuild()
