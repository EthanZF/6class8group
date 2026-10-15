# zfh: 声明源文件编码为 UTF-8
# encoding: utf-8

# zfh: 启用绝对导入、真除法、print 函数与统一字符串字面量语义
from __future__ import absolute_import, division, print_function, unicode_literals

# zfh: 导入 json，用于解析索引中存取的 JSON 值
import json
# zfh: 导入 os，用于索引目录的创建与权限检查
import os
# zfh: 导入 re，用于编译日期时间正则与查询串处理
import re
# zfh: 导入 shutil，用于删除整个索引目录
import shutil
# zfh: 导入 threading，用于保存线程局部的内存索引存储
import threading
# zfh: 导入 warnings，用于提示 Whoosh 不支持分面等特性
import warnings

# zfh: 导入 six，兼容判断整数与字符串类型
import six
# zfh: 导入 Django 配置对象，读取 HAYSTACK 相关设置
from django.conf import settings
# zfh: 导入配置异常类，路径未配置时抛出
from django.core.exceptions import ImproperlyConfigured
# zfh: 导入 datetime，用于把索引中的日期字符串还原为对象
from datetime import datetime
# zfh: 导入 force_str，统一把值转换为字符串
from django.utils.encoding import force_str
# zfh: 导入 Haystack 后端基类、查询基类、空结果集与查询日志装饰器
from haystack.backends import BaseEngine, BaseSearchBackend, BaseSearchQuery, EmptyResults, log_query
# zfh: 导入 Haystack 约定的模型类型与主键字段名常量
from haystack.constants import DJANGO_CT, DJANGO_ID, ID
# zfh: 导入 Haystack 异常：缺少依赖、后端错误、跳过文档
from haystack.exceptions import MissingDependency, SearchBackendError, SkipDocument
# zfh: 导入 Haystack 输入类型，用于清洗与包装查询值
from haystack.inputs import Clean, Exact, PythonData, Raw
# zfh: 导入搜索结果模型类
from haystack.models import SearchResult
# zfh: 导入文档唯一标识与模型类型标识的生成函数
from haystack.utils import get_identifier, get_model_ct
# zfh: 导入 Haystack 的日志工具
from haystack.utils import log as logging
# zfh: 导入按 app_label 与模型名动态加载模型的方法
from haystack.utils.app_loading import haystack_get_model
# zfh: 导入 jieba 中文分词分析器，用于中文全文检索
from jieba.analyse import ChineseAnalyzer
# zfh: 导入 whoosh 索引模块
from whoosh import index
# zfh: 导入 whoosh 英文词干分析器
from whoosh.analysis import StemmingAnalyzer
# zfh: 导入 whoosh 字段类型：布尔、日期、ID列表、关键词、N元、词N元、数值、Schema、文本
from whoosh.fields import BOOLEAN, DATETIME, IDLIST, KEYWORD, NGRAM, NGRAMWORDS, NUMERIC, Schema, TEXT
# zfh: 导入 whoosh 的 ID 字段类型并重命名为 WHOOSH_ID，避免与 Haystack 的 ID 常量冲突
from whoosh.fields import ID as WHOOSH_ID
# zfh: 导入文件存储与内存存储两种索引存储方式
from whoosh.filedb.filestore import FileStorage, RamStorage
# zfh: 导入高亮片段生成器与 HTML 格式化器
from whoosh.highlight import ContextFragmenter, HtmlFormatter
# zfh: 导入 whoosh 高亮函数并重命名，避免与后端方法同名
from whoosh.highlight import highlight as whoosh_highlight
# zfh: 导入查询解析器
from whoosh.qparser import QueryParser
# zfh: 导入搜索结果分页对象
from whoosh.searching import ResultsPage
# zfh: 导入异步写入器，减少索引写入时的锁竞争
from whoosh.writing import AsyncWriter

# zfh: 尝试导入 whoosh 包，缺失时给出依赖提示
try:
    # zfh: 导入 whoosh 包本体
    import whoosh
# zfh: 捕获导入失败
except ImportError:
    # zfh: 抛出缺少依赖异常，提示安装 Whoosh
    raise MissingDependency(
        "The 'whoosh' backend requires the installation of 'Whoosh'. Please refer to the documentation.")

# Handle minimum requirement.
# zfh: 校验 whoosh 版本，缺失版本号或低于 2.5.0 时报错
if not hasattr(whoosh, '__version__') or whoosh.__version__ < (2, 5, 0):
    # zfh: 抛出版本过低异常
    raise MissingDependency(
        "The 'whoosh' backend requires version 2.5.0 or greater.")

# Bubble up the correct error.

# zfh: 编译日期时间格式正则，用于把索引中的字符串还原为 datetime
DATETIME_REGEX = re.compile(
    '^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(\.\d{3,6}Z?)?$')
# zfh: 线程局部存储对象，用于按线程隔离内存索引
LOCALS = threading.local()
# zfh: 线程局部的内存索引存储，初始为空
LOCALS.RAM_STORE = None


# zfh: 自定义高亮格式化器，保证与 Solr、Xapian、Elasticsearch 后端输出格式一致
class WhooshHtmlFormatter(HtmlFormatter):
    """
    This is a HtmlFormatter simpler than the whoosh.HtmlFormatter.
    We use it to have consistent results across backends. Specifically,
    Solr, Xapian and Elasticsearch are using this formatting.
    """
    # zfh: 高亮标签模板，用 tag 标签包裹命中词
    template = '<%(tag)s>%(t)s</%(tag)s>'


# zfh: Whoosh 搜索后端，实现索引的建立、写入、删除与查询
class WhooshSearchBackend(BaseSearchBackend):
    # Word reserved by Whoosh for special use.
    # zfh: Whoosh 查询语法保留字
    RESERVED_WORDS = (
        'AND',
        'NOT',
        'OR',
        'TO',
    )

    # Characters reserved by Whoosh for special use.
    # The '\\' must come first, so as not to overwrite the other slash
    # replacements.
    # zfh: Whoosh 查询语法保留字符
    RESERVED_CHARACTERS = (
        '\\', '+', '-', '&&', '||', '!', '(', ')', '{', '}',
        '[', ']', '^', '"', '~', '*', '?', ':', '.',
    )

    # zfh: 初始化后端，读取连接配置并设置索引路径与存储方式
    def __init__(self, connection_alias, **connection_options):
        # zfh: 调用父类初始化，保存连接别名与配置
        super(
            WhooshSearchBackend,
            self).__init__(
            connection_alias,
            **connection_options)
        # zfh: 标记初始化尚未完成，索引延迟到首次使用时加载
        self.setup_complete = False
        # zfh: 默认使用文件存储保存索引
        self.use_file_storage = True
        # zfh: 单次提交的数据量上限，默认 128MB
        self.post_limit = getattr(
            connection_options,
            'POST_LIMIT',
            128 * 1024 * 1024)
        # zfh: 索引文件存放路径
        self.path = connection_options.get('PATH')

        # zfh: 配置的存储方式不是 file 时改用内存存储
        if connection_options.get('STORAGE', 'file') != 'file':
            # zfh: 关闭文件存储
            self.use_file_storage = False

        # zfh: 使用文件存储但未配置路径时抛出异常
        if self.use_file_storage and not self.path:
            # zfh: 提示必须为该连接指定 PATH
            raise ImproperlyConfigured(
                "You must specify a 'PATH' in your settings for connection '%s'." %
                connection_alias)

        # zfh: 获取 haystack 日志记录器
        self.log = logging.getLogger('haystack')

    # zfh: 初始化索引存储与 schema，延迟到需要时执行
    def setup(self):
        """
        Defers loading until needed.
        """
        # zfh: 导入 haystack 连接管理器，用于获取统一索引
        from haystack import connections
        # zfh: 标记本次是否需要新建索引
        new_index = False

        # Make sure the index is there.
        # zfh: 使用文件存储且索引目录不存在时创建目录
        if self.use_file_storage and not os.path.exists(self.path):
            # zfh: 递归创建索引目录
            os.makedirs(self.path)
            # zfh: 记录需要新建索引
            new_index = True

        # zfh: 检查索引路径是否可写，不可写则报错
        if self.use_file_storage and not os.access(self.path, os.W_OK):
            # zfh: 抛出 IO 错误提示路径不可写
            raise IOError(
                "The path to your Whoosh index '%s' is not writable for the current user/group." %
                self.path)

        # zfh: 文件存储方式下使用 FileStorage
        if self.use_file_storage:
            # zfh: 以索引路径创建文件存储对象
            self.storage = FileStorage(self.path)
        # zfh: 否则使用内存存储
        else:
            # zfh: 声明使用模块级的线程局部变量
            global LOCALS

            # zfh: 当前线程还没有内存存储时创建一个
            if getattr(LOCALS, 'RAM_STORE', None) is None:
                # zfh: 创建内存存储对象
                LOCALS.RAM_STORE = RamStorage()

            # zfh: 使用线程局部的内存存储
            self.storage = LOCALS.RAM_STORE

        # zfh: 根据所有 SearchField 构建 schema，并得到主内容字段名
        self.content_field_name, self.schema = self.build_schema(
            connections[self.connection_alias].get_unified_index().all_searchfields())
        # zfh: 创建查询解析器，指定默认搜索字段
        self.parser = QueryParser(self.content_field_name, schema=self.schema)

        # zfh: 索引目录是新建的，直接创建索引
        if new_index is True:
            # zfh: 按 schema 创建新索引
            self.index = self.storage.create_index(self.schema)
        # zfh: 否则尝试打开已有索引
        else:
            # zfh: 捕获索引为空的异常
            try:
                # zfh: 打开已有索引并校验 schema
                self.index = self.storage.open_index(schema=self.schema)
            # zfh: 索引为空异常
            except index.EmptyIndexError:
                # zfh: 按 schema 新建索引
                self.index = self.storage.create_index(self.schema)

        # zfh: 标记初始化完成
        self.setup_complete = True

    # zfh: 根据 Haystack 的字段定义构建 Whoosh schema
    def build_schema(self, fields):
        # zfh: schema 字段字典，先放入三个 Haystack 固定字段
        schema_fields = {
            ID: WHOOSH_ID(stored=True, unique=True),
            DJANGO_CT: WHOOSH_ID(stored=True),
            DJANGO_ID: WHOOSH_ID(stored=True),
        }
        # Grab the number of keys that are hard-coded into Haystack.
        # We'll use this to (possibly) fail slightly more gracefully later.
        # zfh: 记录硬编码字段数量，用于后续判断是否存在自定义字段
        initial_key_count = len(schema_fields)
        # zfh: 主内容字段名，稍后由标记为 document 的字段覆盖
        content_field_name = ''

        # zfh: 遍历所有 SearchField 逐个映射为 Whoosh 字段
        for field_name, field_class in fields.items():
            # zfh: 多值字段
            if field_class.is_multivalued:
                # zfh: 多值且不参与索引时使用 IDLIST
                if field_class.indexed is False:
                    # zfh: 存储型 ID 列表字段
                    schema_fields[field_class.index_fieldname] = IDLIST(
                        stored=True, field_boost=field_class.boost)
                # zfh: 多值且需要索引时使用 KEYWORD
                else:
                    # zfh: 逗号分隔、可打分的关键词字段
                    schema_fields[field_class.index_fieldname] = KEYWORD(
                        stored=True, commas=True, scorable=True, field_boost=field_class.boost)
            # zfh: 日期或时间类型字段
            elif field_class.field_type in ['date', 'datetime']:
                # zfh: 可排序的日期时间字段
                schema_fields[field_class.index_fieldname] = DATETIME(
                    stored=field_class.stored, sortable=True)
            # zfh: 整数类型字段
            elif field_class.field_type == 'integer':
                # zfh: 整数数值字段
                schema_fields[field_class.index_fieldname] = NUMERIC(
                    stored=field_class.stored, numtype=int, field_boost=field_class.boost)
            # zfh: 浮点类型字段
            elif field_class.field_type == 'float':
                # zfh: 浮点数值字段
                schema_fields[field_class.index_fieldname] = NUMERIC(
                    stored=field_class.stored, numtype=float, field_boost=field_class.boost)
            # zfh: 布尔类型字段
            elif field_class.field_type == 'boolean':
                # Field boost isn't supported on BOOLEAN as of 1.8.2.
                # zfh: 布尔字段，不支持 boost
                schema_fields[field_class.index_fieldname] = BOOLEAN(
                    stored=field_class.stored)
            # zfh: ngram 类型字段
            elif field_class.field_type == 'ngram':
                # zfh: 3 到 15 字符的 N 元字段
                schema_fields[field_class.index_fieldname] = NGRAM(
                    minsize=3, maxsize=15, stored=field_class.stored, field_boost=field_class.boost)
            # zfh: edge_ngram 类型字段
            elif field_class.field_type == 'edge_ngram':
                # zfh: 从词首开始的 2 到 15 字符 N 元词字段
                schema_fields[field_class.index_fieldname] = NGRAMWORDS(minsize=2, maxsize=15, at='start',
                                                                        stored=field_class.stored,
                                                                        field_boost=field_class.boost)
            # zfh: 其余类型按全文检索处理
            else:
                # schema_fields[field_class.index_fieldname] = TEXT(stored=True, analyzer=StemmingAnalyzer(), field_boost=field_class.boost, sortable=True)
                # zfh: 使用 jieba 中文分词分析器的可排序文本字段
                schema_fields[field_class.index_fieldname] = TEXT(
                    stored=True, analyzer=ChineseAnalyzer(), field_boost=field_class.boost, sortable=True)
            # zfh: 该字段被指定为文档主内容字段
            if field_class.document is True:
                # zfh: 记录主内容字段名
                content_field_name = field_class.index_fieldname
                # zfh: 为主内容字段开启拼写检查支持
                schema_fields[field_class.index_fieldname].spelling = True

        # Fail more gracefully than relying on the backend to die if no fields
        # are found.
        # zfh: 没有找到任何自定义字段时抛出后端错误
        if len(schema_fields) <= initial_key_count:
            # zfh: 提示 search_indexes 中缺少字段定义
            raise SearchBackendError(
                "No fields were found in any search_indexes. Please correct this before attempting to search.")

        # zfh: 返回主内容字段名与构建好的 Schema
        return (content_field_name, Schema(**schema_fields))

    # zfh: 批量更新索引中的文档
    def update(self, index, iterable, commit=True):
        # zfh: 首次使用时先完成初始化
        if not self.setup_complete:
            # zfh: 执行初始化
            self.setup()

        # zfh: 刷新索引对象，获取最新状态
        self.index = self.index.refresh()
        # zfh: 创建异步写入器
        writer = AsyncWriter(self.index)

        # zfh: 遍历待索引的对象
        for obj in iterable:
            # zfh: 捕获需要跳过该文档的异常
            try:
                # zfh: 把模型对象准备成待写入的文档字典
                doc = index.full_prepare(obj)
            # zfh: 该对象被标记为跳过索引
            except SkipDocument:
                # zfh: 记录跳过索引的调试日志
                self.log.debug(u"Indexing for object `%s` skipped", obj)
            # zfh: 文档准备成功
            else:
                # Really make sure it's unicode, because Whoosh won't have it any
                # other way.
                # zfh: 逐个字段转换值类型，确保 Whoosh 可接受
                for key in doc:
                    # zfh: 把 Python 值转换为可索引的字符串形式
                    doc[key] = self._from_python(doc[key])

                # Document boosts aren't supported in Whoosh 2.5.0+.
                # zfh: Whoosh 2.5.0 起不支持文档级 boost，需要删除该字段
                if 'boost' in doc:
                    # zfh: 删除 boost 键
                    del doc['boost']

                # zfh: 捕获写入单个文档时的异常
                try:
                    # zfh: 写入或更新该文档
                    writer.update_document(**doc)
                # zfh: 记录异常对象
                except Exception as e:
                    # zfh: 未开启静默失败时直接抛出
                    if not self.silently_fail:
                        # zfh: 抛出异常
                        raise

                    # We'll log the object identifier but won't include the actual object
                    # to avoid the possibility of that generating encoding errors while
                    # processing the log message:
                    # zfh: 记录错误日志，只带对象标识不带对象本身
                    self.log.error(
                        u"%s while preparing object for update" %
                        e.__class__.__name__,
                        exc_info=True,
                        extra={
                            "data": {
                                "index": index,
                                "object": get_identifier(obj)}})

        # zfh: 有待写入文档时提交一次
        if len(iterable) > 0:
            # For now, commit no matter what, as we run into locking issues
            # otherwise.
            # zfh: 提交写入器，释放索引锁
            writer.commit()

    # zfh: 从索引中删除单个文档
    def remove(self, obj_or_string, commit=True):
        # zfh: 首次使用时先完成初始化
        if not self.setup_complete:
            # zfh: 执行初始化
            self.setup()

        # zfh: 刷新索引对象
        self.index = self.index.refresh()
        # zfh: 计算该对象的文档唯一标识
        whoosh_id = get_identifier(obj_or_string)

        # zfh: 捕获删除过程中的异常
        try:
            # zfh: 按 ID 字段查询并删除对应文档
            self.index.delete_by_query(
                q=self.parser.parse(
                    u'%s:"%s"' %
                    (ID, whoosh_id)))
        # zfh: 记录异常对象
        except Exception as e:
            # zfh: 未开启静默失败时直接抛出
            if not self.silently_fail:
                # zfh: 抛出异常
                raise

            # zfh: 记录删除文档失败的日志
            self.log.error(
                "Failed to remove document '%s' from Whoosh: %s",
                whoosh_id,
                e,
                exc_info=True)

    # zfh: 清空索引，可按模型列表定向清理
    def clear(self, models=None, commit=True):
        # zfh: 首次使用时先完成初始化
        if not self.setup_complete:
            # zfh: 执行初始化
            self.setup()

        # zfh: 刷新索引对象
        self.index = self.index.refresh()

        # zfh: 指定了模型列表时校验其类型
        if models is not None:
            # zfh: 断言 models 必须是列表或元组
            assert isinstance(models, (list, tuple))

        # zfh: 捕获清理过程中的异常
        try:
            # zfh: 未指定模型时清空整个索引
            if models is None:
                # zfh: 删除索引文件并重建
                self.delete_index()
            # zfh: 指定模型时按模型类型定向删除
            else:
                # zfh: 待删除的模型查询条件列表
                models_to_delete = []

                # zfh: 遍历要清理的模型
                for model in models:
                    # zfh: 拼出 content_type 查询条件
                    models_to_delete.append(
                        u"%s:%s" %
                        (DJANGO_CT, get_model_ct(model)))

                # zfh: 用 OR 连接各条件执行删除
                self.index.delete_by_query(
                    q=self.parser.parse(
                        u" OR ".join(models_to_delete)))
        # zfh: 记录异常对象
        except Exception as e:
            # zfh: 未开启静默失败时直接抛出
            if not self.silently_fail:
                # zfh: 抛出异常
                raise

            # zfh: 指定了模型时记录对应的错误日志
            if models is not None:
                # zfh: 记录按模型清理失败的日志
                self.log.error(
                    "Failed to clear Whoosh index of models '%s': %s",
                    ','.join(models_to_delete),
                    e,
                    exc_info=True)
            # zfh: 否则记录整体清理失败的日志
            else:
                # zfh: 记录清空索引失败的日志
                self.log.error(
                    "Failed to clear Whoosh index: %s", e, exc_info=True)

    # zfh: 删除整个索引并重建
    def delete_index(self):
        # Per the Whoosh mailing list, if wiping out everything from the index,
        # it's much more efficient to simply delete the index files.
        # zfh: 文件存储且目录存在时直接删除索引目录
        if self.use_file_storage and os.path.exists(self.path):
            # zfh: 递归删除索引目录
            shutil.rmtree(self.path)
        # zfh: 内存存储时清空内存索引
        elif not self.use_file_storage:
            # zfh: 清理内存存储中的索引
            self.storage.clean()

        # Recreate everything.
        # zfh: 重新初始化索引
        self.setup()

    # zfh: 优化索引，合并段文件以提升检索性能
    def optimize(self):
        # zfh: 首次使用时先完成初始化
        if not self.setup_complete:
            # zfh: 执行初始化
            self.setup()

        # zfh: 刷新索引对象
        self.index = self.index.refresh()
        # zfh: 执行索引优化
        self.index.optimize()

    # zfh: 根据偏移量计算 Whoosh 所需的页码与每页长度
    def calculate_page(self, start_offset=0, end_offset=None):
        # Prevent against Whoosh throwing an error. Requires an end_offset
        # greater than 0.
        # zfh: 结束偏移量小于等于 0 时修正为 1
        if end_offset is not None and end_offset <= 0:
            # zfh: 修正结束偏移量
            end_offset = 1

        # Determine the page.
        # zfh: 页码从 0 开始计算
        page_num = 0

        # zfh: 未指定结束偏移量时使用很大的默认值
        if end_offset is None:
            # zfh: 设置默认结束偏移量
            end_offset = 1000000

        # zfh: 起始偏移量为空时置为 0
        if start_offset is None:
            # zfh: 设置默认起始偏移量
            start_offset = 0

        # zfh: 每页长度等于结束与起始偏移量之差
        page_length = end_offset - start_offset

        # zfh: 页长有效时按偏移量计算页码
        if page_length and page_length > 0:
            # zfh: 用整除得到页码
            page_num = int(start_offset / page_length)

        # Increment because Whoosh uses 1-based page numbers.
        # zfh: Whoosh 页码从 1 开始，因此加一
        page_num += 1
        # zfh: 返回页码与每页长度
        return page_num, page_length

    # zfh: 记录查询日志的装饰器
    @log_query
    # zfh: 执行搜索，返回结果列表、命中数与拼写建议
    def search(
            self,
            query_string,
            sort_by=None,
            start_offset=0,
            end_offset=None,
            fields='',
            highlight=False,
            facets=None,
            date_facets=None,
            query_facets=None,
            narrow_queries=None,
            spelling_query=None,
            within=None,
            dwithin=None,
            distance_point=None,
            models=None,
            limit_to_registered_models=None,
            result_class=None,
            **kwargs):
        # zfh: 首次使用时先完成初始化
        if not self.setup_complete:
            # zfh: 执行初始化
            self.setup()

        # A zero length query should return no results.
        # zfh: 空查询串直接返回空结果
        if len(query_string) == 0:
            # zfh: 返回空结果字典
            return {
                'results': [],
                'hits': 0,
            }

        # zfh: 统一把查询串转换为字符串
        query_string = force_str(query_string)

        # A one-character query (non-wildcard) gets nabbed by a stopwords
        # filter and should yield zero results.
        # zfh: 单字符查询（非通配符）会被停用词过滤，直接返回空结果
        if len(query_string) <= 1 and query_string != u'*':
            # zfh: 返回空结果字典
            return {
                'results': [],
                'hits': 0,
            }

        # zfh: 是否反向排序，默认否
        reverse = False

        # zfh: 指定了排序字段时解析排序方向
        if sort_by is not None:
            # Determine if we need to reverse the results and if Whoosh can
            # handle what it's being asked to sort by. Reversing is an
            # all-or-nothing action, unfortunately.
            # zfh: 去掉负号后的排序字段列表
            sort_by_list = []
            # zfh: 降序排序字段计数
            reverse_counter = 0

            # zfh: 统计降序排序字段的个数
            for order_by in sort_by:
                # zfh: 字段以负号开头表示降序
                if order_by.startswith('-'):
                    # zfh: 降序计数加一
                    reverse_counter += 1

            # zfh: 排序方向不一致时 Whoosh 无法处理，抛出异常
            if reverse_counter and reverse_counter != len(sort_by):
                # zfh: 提示所有排序字段必须方向一致
                raise SearchBackendError("Whoosh requires all order_by fields"
                                         " to use the same sort direction")

            # zfh: 逐个处理排序字段，去掉负号并确定方向
            for order_by in sort_by:
                # zfh: 降序字段
                if order_by.startswith('-'):
                    # zfh: 去掉负号后加入排序列表
                    sort_by_list.append(order_by[1:])

                    # zfh: 第一个字段决定整体方向为降序
                    if len(sort_by_list) == 1:
                        # zfh: 标记反向排序
                        reverse = True
                # zfh: 升序字段
                else:
                    # zfh: 直接加入排序列表
                    sort_by_list.append(order_by)

                    # zfh: 第一个字段决定整体方向为升序
                    if len(sort_by_list) == 1:
                        # zfh: 标记正向排序
                        reverse = False

            # zfh: Whoosh 只支持单个排序字段，取第一个
            sort_by = sort_by_list[0]

        # zfh: Whoosh 不支持分面查询，给出警告
        if facets is not None:
            # zfh: 提示不支持 faceting
            warnings.warn(
                "Whoosh does not handle faceting.",
                Warning,
                stacklevel=2)

        # zfh: Whoosh 不支持日期分面，给出警告
        if date_facets is not None:
            # zfh: 提示不支持日期分面
            warnings.warn(
                "Whoosh does not handle date faceting.",
                Warning,
                stacklevel=2)

        # zfh: Whoosh 不支持查询分面，给出警告
        if query_facets is not None:
            # zfh: 提示不支持查询分面
            warnings.warn(
                "Whoosh does not handle query faceting.",
                Warning,
                stacklevel=2)

        # zfh: 缩小结果范围的查询结果，初始为空
        narrowed_results = None
        # zfh: 刷新索引对象
        self.index = self.index.refresh()

        # zfh: 未指定是否限制模型时读取 Haystack 配置，默认限制
        if limit_to_registered_models is None:
            # zfh: 从 settings 读取 HAYSTACK_LIMIT_TO_REGISTERED_MODELS
            limit_to_registered_models = getattr(
                settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)

        # zfh: 显式指定了模型列表时使用指定模型
        if models and len(models):
            # zfh: 生成排序后的模型类型标识列表
            model_choices = sorted(get_model_ct(model) for model in models)
        # zfh: 否则按配置限制到已注册模型
        elif limit_to_registered_models:
            # Using narrow queries, limit the results to only models handled
            # with the current routers.
            # zfh: 使用后端已注册的模型列表
            model_choices = self.build_models_list()
        # zfh: 都不满足时不限制模型
        else:
            # zfh: 模型列表置空
            model_choices = []

        # zfh: 存在模型限制时加入缩小查询条件
        if len(model_choices) > 0:
            # zfh: 缩小查询集合为空时新建
            if narrow_queries is None:
                # zfh: 创建空集合
                narrow_queries = set()

            # zfh: 用 OR 连接各模型的 content_type 条件加入缩小查询
            narrow_queries.add(' OR '.join(
                ['%s:%s' % (DJANGO_CT, rm) for rm in model_choices]))

        # zfh: 缩小查询用的搜索器，初始为空
        narrow_searcher = None

        # zfh: 存在缩小查询条件时先执行缩小查询
        if narrow_queries is not None:
            # Potentially expensive? I don't see another way to do it in
            # Whoosh...
            # zfh: 打开一个搜索器用于缩小查询
            narrow_searcher = self.index.searcher()

            # zfh: 逐个执行缩小查询
            for nq in narrow_queries:
                # zfh: 执行该缩小查询，不限制返回条数
                recent_narrowed_results = narrow_searcher.search(
                    self.parser.parse(force_str(nq)), limit=None)

                # zfh: 缩小查询无结果时直接返回空结果
                if len(recent_narrowed_results) <= 0:
                    # zfh: 返回空结果字典
                    return {
                        'results': [],
                        'hits': 0,
                    }

                # zfh: 已有缩小结果时与其取交集
                if narrowed_results:
                    # zfh: 对已有结果做过滤取交集
                    narrowed_results.filter(recent_narrowed_results)
                # zfh: 首次得到缩小结果时直接赋值
                else:
                    # zfh: 保存缩小查询结果
                    narrowed_results = recent_narrowed_results

        # zfh: 再次刷新索引对象
        self.index = self.index.refresh()

        # zfh: 索引中存在文档时才执行检索
        if self.index.doc_count():
            # zfh: 打开搜索器
            searcher = self.index.searcher()
            # zfh: 把查询串解析为查询对象
            parsed_query = self.parser.parse(query_string)

            # In the event of an invalid/stopworded query, recover gracefully.
            # zfh: 查询解析失败（无效或全为停用词）时返回空结果
            if parsed_query is None:
                # zfh: 返回空结果字典
                return {
                    'results': [],
                    'hits': 0,
                }

            # zfh: 计算页码与每页长度
            page_num, page_length = self.calculate_page(
                start_offset, end_offset)

            # zfh: 组装搜索参数：每页长度、排序字段与排序方向
            search_kwargs = {
                'pagelen': page_length,
                'sortedby': sort_by,
                'reverse': reverse,
            }

            # Handle the case where the results have been narrowed.
            # zfh: 有缩小结果时作为过滤器加入搜索参数
            if narrowed_results is not None:
                # zfh: 设置结果过滤器
                search_kwargs['filter'] = narrowed_results

            # zfh: 捕获分页搜索的取值异常
            try:
                # zfh: 执行分页搜索
                raw_page = searcher.search_page(
                    parsed_query,
                    page_num,
                    **search_kwargs
                )
            # zfh: 页码越界等取值异常
            except ValueError:
                # zfh: 未开启静默失败时直接抛出
                if not self.silently_fail:
                    # zfh: 抛出异常
                    raise

                # zfh: 返回空结果与空的拼写建议
                return {
                    'results': [],
                    'hits': 0,
                    'spelling_suggestion': None,
                }

            # Because as of Whoosh 2.5.1, it will return the wrong page of
            # results if you request something too high. :(
            # zfh: 请求页码超过实际页码时返回空结果
            if raw_page.pagenum < page_num:
                # zfh: 返回空结果与空的拼写建议
                return {
                    'results': [],
                    'hits': 0,
                    'spelling_suggestion': None,
                }

            # zfh: 把原始结果加工为 Haystack 的搜索结果
            results = self._process_results(
                raw_page,
                highlight=highlight,
                query_string=query_string,
                spelling_query=spelling_query,
                result_class=result_class)
            # zfh: 关闭搜索器释放资源
            searcher.close()

            # zfh: 缩小查询搜索器存在关闭方法时一并关闭
            if hasattr(narrow_searcher, 'close'):
                # zfh: 关闭缩小查询搜索器
                narrow_searcher.close()

            # zfh: 返回搜索结果
            return results
        # zfh: 索引为空时走拼写建议分支
        else:
            # zfh: 开启了拼写建议功能
            if self.include_spelling:
                # zfh: 指定了拼写查询串时用它生成建议
                if spelling_query:
                    # zfh: 按指定的拼写查询串生成建议
                    spelling_suggestion = self.create_spelling_suggestion(
                        spelling_query)
                # zfh: 否则用原查询串生成建议
                else:
                    # zfh: 按原查询串生成拼写建议
                    spelling_suggestion = self.create_spelling_suggestion(
                        query_string)
            # zfh: 未开启拼写建议时置空
            else:
                # zfh: 拼写建议为空
                spelling_suggestion = None

            # zfh: 返回空结果与拼写建议
            return {
                'results': [],
                'hits': 0,
                'spelling_suggestion': spelling_suggestion,
            }

    # zfh: 查找与给定对象相似的文档
    def more_like_this(
            self,
            model_instance,
            additional_query_string=None,
            start_offset=0,
            end_offset=None,
            models=None,
            limit_to_registered_models=None,
            result_class=None,
            **kwargs):
        # zfh: 首次使用时先完成初始化
        if not self.setup_complete:
            # zfh: 执行初始化
            self.setup()

        # Deferred models will have a different class ("RealClass_Deferred_fieldname")
        # which won't be in our registry:
        # zfh: 取对象的真实模型类，避免延迟加载产生的子类找不到注册信息
        model_klass = model_instance._meta.concrete_model

        # zfh: 相似查询使用的字段名，即主内容字段
        field_name = self.content_field_name
        # zfh: 缩小查询条件集合
        narrow_queries = set()
        # zfh: 缩小结果，初始为空
        narrowed_results = None
        # zfh: 刷新索引对象
        self.index = self.index.refresh()

        # zfh: 未指定是否限制模型时读取 Haystack 配置，默认限制
        if limit_to_registered_models is None:
            # zfh: 从 settings 读取 HAYSTACK_LIMIT_TO_REGISTERED_MODELS
            limit_to_registered_models = getattr(
                settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)

        # zfh: 显式指定了模型列表时使用指定模型
        if models and len(models):
            # zfh: 生成排序后的模型类型标识列表
            model_choices = sorted(get_model_ct(model) for model in models)
        # zfh: 否则按配置限制到已注册模型
        elif limit_to_registered_models:
            # Using narrow queries, limit the results to only models handled
            # with the current routers.
            # zfh: 使用后端已注册的模型列表
            model_choices = self.build_models_list()
        # zfh: 都不满足时不限制模型
        else:
            # zfh: 模型列表置空
            model_choices = []

        # zfh: 存在模型限制时加入缩小查询条件
        if len(model_choices) > 0:
            # zfh: 缩小查询集合为空时新建
            if narrow_queries is None:
                # zfh: 创建空集合
                narrow_queries = set()

            # zfh: 用 OR 连接各模型的 content_type 条件加入缩小查询
            narrow_queries.add(' OR '.join(
                ['%s:%s' % (DJANGO_CT, rm) for rm in model_choices]))

        # zfh: 附加查询串有效时加入缩小查询
        if additional_query_string and additional_query_string != '*':
            # zfh: 加入附加查询条件
            narrow_queries.add(additional_query_string)

        # zfh: 缩小查询用的搜索器，初始为空
        narrow_searcher = None

        # zfh: 存在缩小查询条件时先执行缩小查询
        if narrow_queries is not None:
            # Potentially expensive? I don't see another way to do it in
            # Whoosh...
            # zfh: 打开一个搜索器用于缩小查询
            narrow_searcher = self.index.searcher()

            # zfh: 逐个执行缩小查询
            for nq in narrow_queries:
                # zfh: 执行该缩小查询，不限制返回条数
                recent_narrowed_results = narrow_searcher.search(
                    self.parser.parse(force_str(nq)), limit=None)

                # zfh: 缩小查询无结果时直接返回空结果
                if len(recent_narrowed_results) <= 0:
                    # zfh: 返回空结果字典
                    return {
                        'results': [],
                        'hits': 0,
                    }

                # zfh: 已有缩小结果时与其取交集
                if narrowed_results:
                    # zfh: 对已有结果做过滤取交集
                    narrowed_results.filter(recent_narrowed_results)
                # zfh: 首次得到缩小结果时直接赋值
                else:
                    # zfh: 保存缩小查询结果
                    narrowed_results = recent_narrowed_results

        # zfh: 计算页码与每页长度
        page_num, page_length = self.calculate_page(start_offset, end_offset)

        # zfh: 再次刷新索引对象
        self.index = self.index.refresh()
        # zfh: 原始结果集，默认为空结果
        raw_results = EmptyResults()

        # zfh: 索引中存在文档时才执行相似查询
        if self.index.doc_count():
            # zfh: 构造按文档 ID 查询的查询串
            query = "%s:%s" % (ID, get_identifier(model_instance))
            # zfh: 打开搜索器
            searcher = self.index.searcher()
            # zfh: 把查询串解析为查询对象
            parsed_query = self.parser.parse(query)
            # zfh: 先查出该对象自身对应的文档
            results = searcher.search(parsed_query)

            # zfh: 找到该文档时执行 more_like_this
            if len(results):
                # zfh: 按主内容字段查找相似文档
                raw_results = results[0].more_like_this(
                    field_name, top=end_offset)

            # Handle the case where the results have been narrowed.
            # zfh: 有缩小结果且支持过滤时取交集
            if narrowed_results is not None and hasattr(raw_results, 'filter'):
                # zfh: 对相似结果做过滤
                raw_results.filter(narrowed_results)

        # zfh: 捕获构造分页对象时的取值异常
        try:
            # zfh: 用原始结果构造分页对象
            raw_page = ResultsPage(raw_results, page_num, page_length)
        # zfh: 页码越界等取值异常
        except ValueError:
            # zfh: 未开启静默失败时直接抛出
            if not self.silently_fail:
                # zfh: 抛出异常
                raise

            # zfh: 返回空结果与空的拼写建议
            return {
                'results': [],
                'hits': 0,
                'spelling_suggestion': None,
            }

        # Because as of Whoosh 2.5.1, it will return the wrong page of
        # results if you request something too high. :(
        # zfh: 请求页码超过实际页码时返回空结果
        if raw_page.pagenum < page_num:
            # zfh: 返回空结果与空的拼写建议
            return {
                'results': [],
                'hits': 0,
                'spelling_suggestion': None,
            }

        # zfh: 把原始结果加工为 Haystack 的搜索结果
        results = self._process_results(raw_page, result_class=result_class)
        # zfh: 关闭搜索器释放资源
        searcher.close()

        # zfh: 缩小查询搜索器存在关闭方法时一并关闭
        if hasattr(narrow_searcher, 'close'):
            # zfh: 关闭缩小查询搜索器
            narrow_searcher.close()

        # zfh: 返回搜索结果
        return results

    # zfh: 把 Whoosh 原始结果页转换为 Haystack 的搜索结果结构
    def _process_results(
            self,
            raw_page,
            highlight=False,
            query_string='',
            spelling_query=None,
            result_class=None):
        # zfh: 导入 haystack 连接管理器
        from haystack import connections
        # zfh: 结果对象列表
        results = []

        # It's important to grab the hits first before slicing. Otherwise, this
        # can cause pagination failures.
        # zfh: 先取出命中总数，避免分页错乱
        hits = len(raw_page)

        # zfh: 未指定结果类时使用默认的 SearchResult
        if result_class is None:
            # zfh: 使用 SearchResult
            result_class = SearchResult

        # zfh: 分面结果，Whoosh 不支持故为空字典
        facets = {}
        # zfh: 拼写建议，默认空
        spelling_suggestion = None
        # zfh: 获取统一索引对象
        unified_index = connections[self.connection_alias].get_unified_index()
        # zfh: 获取所有已建立索引的模型
        indexed_models = unified_index.get_indexed_models()

        # zfh: 遍历原始结果页中的每条文档
        for doc_offset, raw_result in enumerate(raw_page):
            # zfh: 取该文档的得分，无得分时记为 0
            score = raw_page.score(doc_offset) or 0
            # zfh: 从 content_type 拆出 app_label 与模型名
            app_label, model_name = raw_result[DJANGO_CT].split('.')
            # zfh: 附加字段字典
            additional_fields = {}
            # zfh: 按 app_label 与模型名加载模型类
            model = haystack_get_model(app_label, model_name)

            # zfh: 模型存在且已建立索引时处理其字段
            if model and model in indexed_models:
                # zfh: 遍历文档中的每个字段
                for key, value in raw_result.items():
                    # zfh: 取该模型对应的索引
                    index = unified_index.get_index(model)
                    # zfh: 字段名转为字符串
                    string_key = str(key)

                    # zfh: 字段在索引定义中存在且支持类型转换
                    if string_key in index.fields and hasattr(
                            index.fields[string_key], 'convert'):
                        # Special-cased due to the nature of KEYWORD fields.
                        # zfh: 多值字段特殊处理
                        if index.fields[string_key].is_multivalued:
                            # zfh: 值为空时给空列表
                            if value is None or len(value) == 0:
                                # zfh: 置为空列表
                                additional_fields[string_key] = []
                            # zfh: 有值时按逗号切分为列表
                            else:
                                # zfh: 逗号切分多值
                                additional_fields[string_key] = value.split(
                                    ',')
                        # zfh: 单值字段按字段类型转换
                        else:
                            # zfh: 调用字段的 convert 转换值
                            additional_fields[string_key] = index.fields[string_key].convert(
                                value)
                    # zfh: 未定义的字段按通用规则转换
                    else:
                        # zfh: 使用通用转换方法
                        additional_fields[string_key] = self._to_python(value)

                # zfh: 删除 content_type 附加字段
                del (additional_fields[DJANGO_CT])
                # zfh: 删除文档 ID 附加字段
                del (additional_fields[DJANGO_ID])

                # zfh: 需要高亮时生成高亮片段
                if highlight:
                    # 使用中文分词器
                    # zfh: 创建 jieba 中文分词分析器
                    ca = ChineseAnalyzer()

                    # zfh: 高亮结果字典
                    highlighted = {}

                    # 高亮标题（如果存在）
                    # zfh: 标题字段存在且有内容时进行高亮
                    if 'title' in additional_fields and additional_fields['title']:
                        # zfh: 导入正则模块用于替换
                        import re
                        # zfh: 取出标题文本
                        title_text = additional_fields['title']
                        # 使用正则表达式高亮，不转义HTML
                        # zfh: 逐个查询词在标题中做不区分大小写的替换
                        for term in query_string.split():
                            # zfh: 只处理长度不小于 2 的词
                            if len(term) >= 2:
                                # 不区分大小写地替换
                                # zfh: 用 mark 标签包裹命中的词
                                title_text = re.sub(
                                    r'(' + re.escape(term) + r')',
                                    r'<mark>\1</mark>',
                                    title_text,
                                    flags=re.IGNORECASE
                                )
                        # zfh: 标题中有命中时写入高亮结果
                        if '<mark>' in title_text:
                            # zfh: 保存高亮后的标题
                            highlighted['title'] = [title_text]

                    # 高亮正文 - 返回markdown片段，让模板处理
                    # zfh: 正文字段存在且有内容时提取高亮片段
                    if 'body' in additional_fields and additional_fields['body']:
                        # zfh: 导入正则模块
                        import re
                        # zfh: 导入项目的 Markdown 渲染工具
                        from djangoblog.utils import CommonMarkdown

                        # 先转换为HTML，便于提取摘要
                        # zfh: 先把 Markdown 正文渲染成 HTML
                        html_content = CommonMarkdown.get_markdown(additional_fields['body'])

                        # 提取纯文本用于搜索匹配的上下文
                        # zfh: 导入去除 HTML 标签的工具
                        from django.utils.html import strip_tags
                        # zfh: 去掉 HTML 标签得到纯文本
                        plain_text = strip_tags(html_content)

                        # 找到关键词的位置，提取上下文
                        # zfh: 匹配位置，-1 表示未找到
                        match_pos = -1
                        # zfh: 逐个查询词在纯文本中查找位置
                        for term in query_string.split():
                            # zfh: 只处理长度不小于 2 的词
                            if len(term) >= 2:
                                # zfh: 不区分大小写查找该词的位置
                                pos = plain_text.lower().find(term.lower())
                                # zfh: 找到位置时记录并结束查找
                                if pos >= 0:
                                    # zfh: 记录匹配位置
                                    match_pos = pos
                                    # zfh: 跳出循环
                                    break

                        # zfh: 找到匹配位置时截取上下文片段
                        if match_pos >= 0:
                            # 提取匹配位置前后的内容
                            # zfh: 片段起始位置，向前 150 个字符
                            start = max(0, match_pos - 150)
                            # zfh: 片段结束位置，向后 350 个字符
                            end = min(len(plain_text), match_pos + 350)
                            # zfh: 截取上下文片段
                            snippet = plain_text[start:end]

                            # 对snippet进行高亮
                            # zfh: 逐个查询词对片段做高亮替换
                            for term in query_string.split():
                                # zfh: 只处理长度不小于 2 的词
                                if len(term) >= 2:
                                    # zfh: 用 mark 标签包裹命中的词
                                    snippet = re.sub(
                                        r'(' + re.escape(term) + r')',
                                        r'<mark>\1</mark>',
                                        snippet,
                                        flags=re.IGNORECASE
                                    )

                            # zfh: 保存高亮后的正文片段
                            highlighted['body'] = [snippet]

                    # zfh: 有高亮结果时写入附加字段
                    if highlighted:
                        # zfh: 设置 highlighted 附加字段
                        additional_fields['highlighted'] = highlighted

                # zfh: 构造 SearchResult 对象
                result = result_class(
                    app_label,
                    model_name,
                    raw_result[DJANGO_ID],
                    score,
                    **additional_fields)
                # zfh: 加入结果列表
                results.append(result)
            # zfh: 模型不存在或未建立索引时命中数减一
            else:
                # zfh: 命中总数减一
                hits -= 1

        # zfh: 开启了拼写建议时生成建议
        if self.include_spelling:
            # zfh: 指定了拼写查询串时用它生成
            if spelling_query:
                # zfh: 按指定查询串生成拼写建议
                spelling_suggestion = self.create_spelling_suggestion(
                    spelling_query)
            # zfh: 否则用原查询串生成
            else:
                # zfh: 按原查询串生成拼写建议
                spelling_suggestion = self.create_spelling_suggestion(
                    query_string)

        # zfh: 返回结果列表、命中数、分面与拼写建议
        return {
            'results': results,
            'hits': hits,
            'facets': facets,
            'spelling_suggestion': spelling_suggestion,
        }

    # zfh: 根据查询串生成拼写纠错建议
    def create_spelling_suggestion(self, query_string):
        # zfh: 拼写建议，默认空
        spelling_suggestion = None
        # zfh: 打开索引读取器
        reader = self.index.reader()
        # zfh: 取主内容字段的纠错器
        corrector = reader.corrector(self.content_field_name)
        # zfh: 把查询串统一转换为字符串
        cleaned_query = force_str(query_string)

        # zfh: 查询串为空时直接返回空建议
        if not query_string:
            # zfh: 返回空建议
            return spelling_suggestion

        # Clean the string.
        # zfh: 去掉查询串中的保留字
        for rev_word in self.RESERVED_WORDS:
            # zfh: 删除该保留字
            cleaned_query = cleaned_query.replace(rev_word, '')

        # zfh: 去掉查询串中的保留字符
        for rev_char in self.RESERVED_CHARACTERS:
            # zfh: 删除该保留字符
            cleaned_query = cleaned_query.replace(rev_char, '')

        # Break it down.
        # zfh: 按空白把查询串切分成词
        query_words = cleaned_query.split()
        # zfh: 建议词列表
        suggested_words = []

        # zfh: 逐个词生成纠错建议
        for word in query_words:
            # zfh: 取最相似的一个候选词
            suggestions = corrector.suggest(word, limit=1)

            # zfh: 有候选词时加入建议列表
            if len(suggestions) > 0:
                # zfh: 追加第一个候选词
                suggested_words.append(suggestions[0])

        # zfh: 用空格拼接建议词
        spelling_suggestion = ' '.join(suggested_words)
        # zfh: 返回拼写建议
        return spelling_suggestion

    # zfh: 把 Python 值转换为 Whoosh 可存储的形式
    def _from_python(self, value):
        """
        Converts Python values to a string for Whoosh.

        Code courtesy of pysolr.
        """
        # zfh: 值带 strftime 说明是日期时间对象
        if hasattr(value, 'strftime'):
            # zfh: 只有日期没有小时时补成当天零点
            if not hasattr(value, 'hour'):
                # zfh: 构造当天零点的 datetime
                value = datetime(value.year, value.month, value.day, 0, 0, 0)
        # zfh: 布尔值转为小写字符串
        elif isinstance(value, bool):
            # zfh: 真值处理
            if value:
                # zfh: 转成 true
                value = 'true'
            # zfh: 假值处理
            else:
                # zfh: 转成 false
                value = 'false'
        # zfh: 列表或元组用逗号拼接
        elif isinstance(value, (list, tuple)):
            # zfh: 逗号连接各元素
            value = u','.join([force_str(v) for v in value])
        # zfh: 整数或浮点数保持原样
        elif isinstance(value, (six.integer_types, float)):
            # Leave it alone.
            # zfh: 不做转换
            pass
        # zfh: 其余类型统一转为字符串
        else:
            # zfh: 转为字符串
            value = force_str(value)
        # zfh: 返回转换后的值
        return value

    # zfh: 把 Whoosh 返回的值转换为原生 Python 值
    def _to_python(self, value):
        """
        Converts values from Whoosh to native Python values.

        A port of the same method in pysolr, as they deal with data the same way.
        """
        # zfh: 字符串 true 转为布尔真
        if value == 'true':
            # zfh: 返回 True
            return True
        # zfh: 字符串 false 转为布尔假
        elif value == 'false':
            # zfh: 返回 False
            return False

        # zfh: 值非空且为字符串时尝试解析为日期时间
        if value and isinstance(value, six.string_types):
            # zfh: 用正则匹配日期时间格式
            possible_datetime = DATETIME_REGEX.search(value)

            # zfh: 匹配成功时构造 datetime 对象
            if possible_datetime:
                # zfh: 取各命名分组组成的字典
                date_values = possible_datetime.groupdict()

                # zfh: 把各分组的值转为整数
                for dk, dv in date_values.items():
                    # zfh: 字符串转整数
                    date_values[dk] = int(dv)

                # zfh: 返回构造好的 datetime 对象
                return datetime(
                    date_values['year'],
                    date_values['month'],
                    date_values['day'],
                    date_values['hour'],
                    date_values['minute'],
                    date_values['second'])

        # zfh: 尝试把值当作 JSON 解析
        try:
            # Attempt to use json to load the values.
            # zfh: 用 json 解析该值
            converted_value = json.loads(value)

            # Try to handle most built-in types.
            # zfh: 解析结果为常见内置类型时直接返回
            if isinstance(
                    converted_value,
                    (list,
                     tuple,
                     set,
                     dict,
                     six.integer_types,
                     float,
                     complex)):
                # zfh: 返回解析后的值
                return converted_value
        # zfh: 解析失败时忽略异常继续往下走
        except BaseException:
            # If it fails (SyntaxError or its ilk) or we don't trust it,
            # continue on.
            # zfh: 不做处理
            pass

        # zfh: 无法转换时原样返回
        return value


# zfh: Whoosh 查询构造类，把 Haystack 查询条件拼成 Whoosh 查询串
class WhooshSearchQuery(BaseSearchQuery):
    # zfh: 把日期对象转换为 Whoosh 支持的日期字符串
    def _convert_datetime(self, date):
        # zfh: 带小时信息时按完整时间格式化
        if hasattr(date, 'hour'):
            # zfh: 格式化为年月日时分秒
            return force_str(date.strftime('%Y%m%d%H%M%S'))
        # zfh: 否则只取日期部分
        else:
            # zfh: 格式化为年月日加零时分秒
            return force_str(date.strftime('%Y%m%d000000'))

    # zfh: 清洗用户输入，处理 Whoosh 保留字与保留字符
    def clean(self, query_fragment):
        """
        Provides a mechanism for sanitizing user input before presenting the
        value to the backend.

        Whoosh 1.X differs here in that you can no longer use a backslash
        to escape reserved characters. Instead, the whole word should be
        quoted.
        """
        # zfh: 按空白把查询片段切分为词
        words = query_fragment.split()
        # zfh: 清洗后的词列表
        cleaned_words = []

        # zfh: 逐个词处理
        for word in words:
            # zfh: 词是保留字时转为小写
            if word in self.backend.RESERVED_WORDS:
                # zfh: 转为小写
                word = word.replace(word, word.lower())

            # zfh: 检查词中是否含保留字符
            for char in self.backend.RESERVED_CHARACTERS:
                # zfh: 含保留字符时用单引号包裹整个词
                if char in word:
                    # zfh: 用单引号包裹
                    word = "'%s'" % word
                    # zfh: 已包裹，结束内层循环
                    break

            # zfh: 加入清洗结果
            cleaned_words.append(word)

        # zfh: 用空格拼接清洗后的词
        return ' '.join(cleaned_words)

    # zfh: 根据字段、过滤类型与值构造查询片段
    def build_query_fragment(self, field, filter_type, value):
        # zfh: 导入 haystack 连接管理器
        from haystack import connections
        # zfh: 查询片段，初始为空
        query_frag = ''
        # zfh: 值是否为日期时间类型
        is_datetime = False

        # zfh: 值不是 InputType 时先包装
        if not hasattr(value, 'input_type_name'):
            # Handle when we've got a ``ValuesListQuerySet``...
            # zfh: 值带 values_list 说明是 QuerySet，转为列表
            if hasattr(value, 'values_list'):
                # zfh: 转为列表
                value = list(value)

            # zfh: 值带 strftime 说明是日期时间
            if hasattr(value, 'strftime'):
                # zfh: 标记为日期时间
                is_datetime = True

            # zfh: 字符串且不是空格时按 Clean 处理
            if isinstance(value, six.string_types) and value != ' ':
                # It's not an ``InputType``. Assume ``Clean``.
                # zfh: 用 Clean 包装做转义清洗
                value = Clean(value)
            # zfh: 其余值按 PythonData 处理
            else:
                # zfh: 用 PythonData 包装
                value = PythonData(value)

        # Prepare the query using the InputType.
        # zfh: 用输入类型准备最终的值
        prepared_value = value.prepare(self)

        # zfh: 非集合类型的值再转换一次
        if not isinstance(prepared_value, (set, list, tuple)):
            # Then convert whatever we get back to what pysolr wants if needed.
            # zfh: 把值转换为后端可用的形式
            prepared_value = self.backend._from_python(prepared_value)

        # 'content' is a special reserved word, much like 'pk' in
        # Django's ORM layer. It indicates 'no special field'.
        # zfh: content 字段表示不限定字段，字段名前缀留空
        if field == 'content':
            # zfh: 字段名前缀为空
            index_fieldname = ''
        # zfh: 其他字段取出索引字段名并加冒号
        else:
            # zfh: 拼接索引字段名前缀
            index_fieldname = u'%s:' % connections[self._using].get_unified_index(
            ).get_index_fieldname(field)

        # zfh: 各过滤类型对应的查询片段模板
        filter_types = {
            'content': '%s',
            'contains': '*%s*',
            'endswith': "*%s",
            'startswith': "%s*",
            'exact': '%s',
            'gt': "{%s to}",
            'gte': "[%s to]",
            'lt': "{to %s}",
            'lte': "[to %s]",
            'fuzzy': u'%s~',
        }

        # zfh: 输入类型不要求后处理时直接使用准备好的值
        if value.post_process is False:
            # zfh: 直接作为查询片段
            query_frag = prepared_value
        # zfh: 否则按过滤类型分别拼接
        else:
            # zfh: 这几类过滤类型按词逐个拼接
            if filter_type in [
                'content',
                'contains',
                'startswith',
                'endswith',
                'fuzzy']:
                # zfh: exact 输入类型不做分词处理
                if value.input_type_name == 'exact':
                    # zfh: 直接使用准备好的值
                    query_frag = prepared_value
                # zfh: 否则拆分查询词
                else:
                    # Iterate over terms & incorportate the converted form of
                    # each into the query.
                    # zfh: 查询词片段列表
                    terms = []

                    # zfh: 字符串值按空格切分
                    if isinstance(prepared_value, six.string_types):
                        # zfh: 按空格拆成多个可能值
                        possible_values = prepared_value.split(' ')
                    # zfh: 非字符串值作为单个值处理
                    else:
                        # zfh: 日期时间值先转成日期字符串
                        if is_datetime is True:
                            # zfh: 转换日期时间格式
                            prepared_value = self._convert_datetime(
                                prepared_value)

                        # zfh: 包成单元素列表
                        possible_values = [prepared_value]

                    # zfh: 逐个值套用模板生成查询片段
                    for possible_value in possible_values:
                        # zfh: 按过滤类型模板拼接片段
                        terms.append(
                            filter_types[filter_type] %
                            self.backend._from_python(possible_value))

                    # zfh: 只有一个片段时直接使用
                    if len(terms) == 1:
                        # zfh: 取唯一片段
                        query_frag = terms[0]
                    # zfh: 多个片段时用 AND 连接
                    else:
                        # zfh: 用 AND 连接并加括号
                        query_frag = u"(%s)" % " AND ".join(terms)
            # zfh: in 过滤类型逐个值拼接
            elif filter_type == 'in':
                # zfh: in 选项列表
                in_options = []

                # zfh: 遍历 in 的每个取值
                for possible_value in prepared_value:
                    # zfh: 重置日期时间标记
                    is_datetime = False

                    # zfh: 值带 strftime 说明是日期时间
                    if hasattr(possible_value, 'strftime'):
                        # zfh: 标记为日期时间
                        is_datetime = True

                    # zfh: 转换为后端可用的值
                    pv = self.backend._from_python(possible_value)

                    # zfh: 日期时间值需再转成日期字符串
                    if is_datetime is True:
                        # zfh: 转换日期时间格式
                        pv = self._convert_datetime(pv)

                    # zfh: 字符串且非日期时用引号包裹
                    if isinstance(pv, six.string_types) and not is_datetime:
                        # zfh: 加双引号作为精确值
                        in_options.append('"%s"' % pv)
                    # zfh: 其他值直接使用
                    else:
                        # zfh: 直接加入选项
                        in_options.append('%s' % pv)

                # zfh: 用 OR 连接所有选项并加括号
                query_frag = "(%s)" % " OR ".join(in_options)
            # zfh: range 过滤类型构造区间查询
            elif filter_type == 'range':
                # zfh: 区间起始值
                start = self.backend._from_python(prepared_value[0])
                # zfh: 区间结束值
                end = self.backend._from_python(prepared_value[1])

                # zfh: 起始值是日期时间时转换格式
                if hasattr(prepared_value[0], 'strftime'):
                    # zfh: 转换起始值
                    start = self._convert_datetime(start)

                # zfh: 结束值是日期时间时转换格式
                if hasattr(prepared_value[1], 'strftime'):
                    # zfh: 转换结束值
                    end = self._convert_datetime(end)

                # zfh: 拼接闭区间查询片段
                query_frag = u"[%s to %s]" % (start, end)
            # zfh: exact 过滤类型构造精确匹配
            elif filter_type == 'exact':
                # zfh: 输入类型本身就是 exact 时直接使用
                if value.input_type_name == 'exact':
                    # zfh: 直接使用准备好的值
                    query_frag = prepared_value
                # zfh: 否则用 Exact 包装后再拼接
                else:
                    # zfh: 用 Exact 包装并准备值
                    prepared_value = Exact(prepared_value).prepare(self)
                    # zfh: 按模板拼接查询片段
                    query_frag = filter_types[filter_type] % prepared_value
            # zfh: 其余过滤类型走默认处理
            else:
                # zfh: 日期时间值先转换格式
                if is_datetime is True:
                    # zfh: 转换日期时间格式
                    prepared_value = self._convert_datetime(prepared_value)

                # zfh: 按模板拼接查询片段
                query_frag = filter_types[filter_type] % prepared_value

        # zfh: 查询片段非空且不是原始输入时补全括号
        if len(query_frag) and not isinstance(value, Raw):
            # zfh: 片段未用括号包裹时加上括号
            if not query_frag.startswith('(') and not query_frag.endswith(')'):
                # zfh: 用括号包裹片段
                query_frag = "(%s)" % query_frag

        # zfh: 返回字段名前缀加查询片段
        return u"%s%s" % (index_fieldname, query_frag)

        # if not filter_type in ('in', 'range'):
        #     # 'in' is a bit of a special case, as we don't want to
        #     # convert a valid list/tuple to string. Defer handling it
        #     # until later...
        #     value = self.backend._from_python(value)


# zfh: Whoosh 搜索引擎，绑定后端与查询类
class WhooshEngine(BaseEngine):
    # zfh: 指定搜索后端类
    backend = WhooshSearchBackend
    # zfh: 指定查询构造类
    query = WhooshSearchQuery
