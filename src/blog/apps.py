# ZFH: 应用配置模块，定义 blog 应用的启动初始化逻辑
from django.apps import AppConfig
# ZFH: 标准库导入：logging 用于记录索引探测与创建结果
import logging

# ZFH: 模块级日志器，以 blog.apps 作为日志来源标识
logger = logging.getLogger(__name__)


class BlogConfig(AppConfig):
    # ZFH: blog 应用的配置类，name 指明应用模块路径
    # ZFH: 应用名需与 INSTALLED_APPS 中的 'blog' 保持一致
    name = 'blog'

    def ready(self):
        """ZFH: Django 应用启动完成时回调，用于执行搜索索引的初始化检查"""
        # ZFH: 检查并创建搜索索引（如果需要）
        self.check_search_index()

    def check_search_index(self):
        """ZFH: 检查 Elasticsearch / Whoosh 搜索索引是否存在，不存在则按需创建或记录日志"""
        # ZFH: 延迟导入 settings，避免应用加载早期访问尚未就绪的配置
        from django.conf import settings

        # ZFH: 1. 检查Elasticsearch索引
        if hasattr(settings, 'ELASTICSEARCH_DSL'):
            # ZFH: 延迟导入文档模块，避免未安装 elasticsearch-dsl 时影响应用启动
            try:
                from blog.documents import ELASTICSEARCH_ENABLED, ArticleDocumentManager
                if ELASTICSEARCH_ENABLED:
                    # ZFH: 按配置构造客户端，仅用于探测 blog 索引是否存在
                    from elasticsearch import Elasticsearch
                    es_config = settings.ELASTICSEARCH_DSL['default']
                    es = Elasticsearch(hosts=[es_config['hosts']], verify_certs=False)

                    # ZFH: 检查blog索引是否存在
                    if not es.indices.exists(index='blog'):
                        logger.info("Elasticsearch blog index not found, creating empty index...")
                        manager = ArticleDocumentManager()
                        logger.info("Elasticsearch blog index created successfully")
                    else:
                        logger.debug("Elasticsearch blog index already exists")
            except Exception as e:
                # ZFH: 索引检查失败不阻断启动，仅记录警告
                logger.warning(f"Failed to check/create Elasticsearch index: {e}")

        # ZFH: 2. 检查Whoosh索引
        # ZFH: 读取 Haystack 默认后端的引擎类型，为空或非 whoosh 时跳过
        haystack_engine = settings.HAYSTACK_CONNECTIONS.get('default', {}).get('ENGINE', '')
        if 'whoosh' in haystack_engine.lower():
            # ZFH: 探测过程出错不应阻断 Django 启动，统一在末尾记录警告
            try:
                # ZFH: 局部导入 os，仅本段需要文件系统检查
                import os
                # ZFH: 获取 Whoosh 索引目录配置
                whoosh_path = settings.HAYSTACK_CONNECTIONS['default'].get('PATH')
                if whoosh_path and not os.path.exists(whoosh_path):
                    logger.info(f"Whoosh index directory not found at {whoosh_path}, will be created on first search")
                    # ZFH: Whoosh会在第一次搜索时自动创建，这里只记录日志
                elif whoosh_path and os.path.exists(whoosh_path):
                    # ZFH: 检查是否有索引文件（.seg 段文件或写锁文件）
                    index_files = [f for f in os.listdir(whoosh_path) if f.endswith('.seg') or f == '_MAIN_WRITELOCK']
                    if not index_files:
                        # ZFH: 目录为空说明尚未建立索引，等待首次搜索自动初始化
                        logger.info("Whoosh index directory exists but empty, will be initialized on first search")
                    else:
                        logger.debug("Whoosh index already exists")
            # ZFH: 任何异常（目录权限、配置缺失等）只记录警告，不影响启动
            except Exception as e:
                logger.warning(f"Failed to check Whoosh index: {e}")
