# ZFH: Elasticsearch 文档定义与索引管理模块（基于 elasticsearch-dsl），仅在配置了 ELASTICSEARCH_DSL 时生效
# ZFH: 标准库导入：time 用于生成毫秒级时间戳作为性能文档的主键
import time

# ZFH: 第三方导入：elasticsearch 客户端、Django 配置及 elasticsearch-dsl 的文档/字段建模组件
import elasticsearch.client
from django.conf import settings
from elasticsearch_dsl import Document, InnerDoc, Date, Integer, Long, Text, Object, GeoPoint, Keyword, Boolean
from elasticsearch_dsl.connections import connections

# ZFH: 项目内导入：文章模型，供文档字段转换与全量重建索引使用
from blog.models import Article

# ZFH: 是否启用 ES：以 settings 中是否存在 ELASTICSEARCH_DSL 配置为准
ELASTICSEARCH_ENABLED = hasattr(settings, 'ELASTICSEARCH_DSL')

# ZFH: 启用时初始化客户端、连接与 GeoIP pipeline；未配置则整段跳过，不影响其他搜索后端
if ELASTICSEARCH_ENABLED:
    from elasticsearch import Elasticsearch

    es_config = settings.ELASTICSEARCH_DSL['default']

    # ZFH: 处理 hosts 配置，确保每个 host 都带 scheme（http:// 或 https://）
    hosts = es_config['hosts']
    if isinstance(hosts, str):
        # ZFH: 如果没有 scheme，自动添加 http://
        if not hosts.startswith(('http://', 'https://')):
            hosts = f'http://{hosts}'
        hosts = [hosts]
    elif isinstance(hosts, list):
        # ZFH: 处理列表中的每个 host
        processed_hosts = []
        for host in hosts:
            if not host.startswith(('http://', 'https://')):
                host = f'http://{host}'
            processed_hosts.append(host)
        hosts = processed_hosts

    # ZFH: ES 连接配置（动态适配认证方式）
    es_params = {
        'hosts': hosts,
        'verify_certs': es_config.get('verify_certs', False),
    }

    # ZFH: 支持用户名密码认证（ES 8.x 默认启用安全特性）
    if 'username' in es_config and 'password' in es_config:
        es_params['basic_auth'] = (es_config['username'], es_config['password'])

    # ZFH: 支持 API Key 认证
    if 'api_key' in es_config:
        es_params['api_key'] = es_config['api_key']

    # ZFH: 支持证书认证
    if 'ca_certs' in es_config:
        es_params['ca_certs'] = es_config['ca_certs']

    # ZFH: 支持客户端证书
    if 'client_cert' in es_config and 'client_key' in es_config:
        es_params['client_cert'] = es_config['client_cert']
        es_params['client_key'] = es_config['client_key']

    # ZFH: 创建客户端实例并注册默认 DSL 连接
    es = Elasticsearch(**es_params)
    connections.create_connection(**es_params)

    # ZFH: 设置 GeoIP pipeline：不存在时创建，用于把 ip 字段解析为地理位置
    try:
        es.ingest.get_pipeline(id='geoip')
    except elasticsearch.exceptions.NotFoundError:
        es.ingest.put_pipeline(id='geoip', body={
            "description": "Add geoip info",
            "processors": [
                {
                    "geoip": {
                        "field": "ip"
                    }
                }
            ]
        })


class GeoIp(InnerDoc):
    # ZFH: GeoIP 内嵌文档，保存 IP 对应的地理位置信息
    # ZFH: 大洲名称，keyword 类型便于精确过滤与聚合
    continent_name = Keyword()
    # ZFH: 国家 ISO 代码，用于按国家维度统计
    country_iso_code = Keyword()
    # ZFH: 国家名称，便于直接展示
    country_name = Keyword()
    # ZFH: 经纬度坐标，geo_point 类型支持地理距离与范围查询
    location = GeoPoint()


class UserAgentBrowser(InnerDoc):
    # ZFH: 浏览器信息内嵌文档
    # ZFH: 浏览器名称（如 Chrome、Firefox）
    Family = Keyword()
    # ZFH: 浏览器版本号
    Version = Keyword()


class UserAgentOS(UserAgentBrowser):
    # ZFH: 操作系统信息内嵌文档，复用浏览器的 Family/Version 字段
    pass


class UserAgentDevice(InnerDoc):
    # ZFH: 设备信息内嵌文档
    # ZFH: 设备类型（如 smartphone、pc）
    Family = Keyword()
    # ZFH: 设备品牌
    Brand = Keyword()
    # ZFH: 设备型号
    Model = Keyword()


class UserAgent(InnerDoc):
    # ZFH: 用户代理聚合文档，组合浏览器/系统/设备及原始 UA 字符串、是否为爬虫
    # ZFH: 浏览器信息，required=False 表示该子文档可以缺省
    browser = Object(UserAgentBrowser, required=False)
    # ZFH: 操作系统信息
    os = Object(UserAgentOS, required=False)
    # ZFH: 设备信息
    device = Object(UserAgentDevice, required=False)
    # ZFH: 原始 User-Agent 字符串，保留完整信息便于排查
    string = Text()
    # ZFH: 是否被识别为爬虫
    is_bot = Boolean()


class ElapsedTimeDocument(Document):
    # ZFH: 页面耗时性能日志的 ES 文档，索引名为 performance
    # ZFH: 被访问的 URL，keyword 便于按页面精确统计
    url = Keyword()
    # ZFH: 请求耗时，Long 保存较大的毫秒数值
    time_taken = Long()
    # ZFH: 日志记录时间，Date 类型支持时间范围查询
    log_datetime = Date()
    # ZFH: 客户端 IP，原始值，供 GeoIP pipeline 解析
    ip = Keyword()
    # ZFH: 由 IP 解析出的地理位置，可能为空
    geoip = Object(GeoIp, required=False)
    # ZFH: 客户端 User-Agent 解析结果，可能为空
    useragent = Object(UserAgent, required=False)

    class Index:
        # ZFH: ES 索引配置：单分片、0 副本（适合单机/开发）
        name = 'performance'
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }


class ElaspedTimeDocumentManager:
    # ZFH: 性能文档管理器（类名拼写为 Elasped），负责索引创建、删除与写入
    @staticmethod
    def build_index():
        # ZFH: 若 performance 索引不存在则初始化
        from elasticsearch import Elasticsearch
        # ZFH: 使用已配置好的连接参数
        client = Elasticsearch(**es_params)
        # ZFH: 先探测索引是否已存在，避免重复初始化
        res = client.indices.exists(index="performance")
        if not res:
            ElapsedTimeDocument.init()

    @staticmethod
    def delete_index():
        # ZFH: 删除 performance 索引，索引不存在时忽略异常
        from elasticsearch import Elasticsearch
        es = Elasticsearch(**es_params)
        try:
            es.indices.delete(index='performance')
        except elasticsearch.exceptions.NotFoundError:
            pass

    @staticmethod
    def create(url, time_taken, log_datetime, useragent, ip):
        # ZFH: 组装并保存一条页面耗时记录；useragent 为 user_agents 解析对象
        ElaspedTimeDocumentManager.build_index()
        # ZFH: 初始化嵌套文档容器，下面按浏览器/系统/设备逐层赋值
        ua = UserAgent()
        ua.browser = UserAgentBrowser()
        ua.browser.Family = useragent.browser.family
        ua.browser.Version = useragent.browser.version_string

        # ZFH: 填充操作系统名称与版本
        ua.os = UserAgentOS()
        ua.os.Family = useragent.os.family
        ua.os.Version = useragent.os.version_string

        # ZFH: 填充设备类型、品牌与型号
        ua.device = UserAgentDevice()
        ua.device.Family = useragent.device.family
        ua.device.Brand = useragent.device.brand
        ua.device.Model = useragent.device.model
        # ZFH: 保留原始 UA 字符串及爬虫标记
        ua.string = useragent.ua_string
        ua.is_bot = useragent.is_bot

        doc = ElapsedTimeDocument(
            meta={
                'id': int(
                    round(
                        time.time() *
                        1000))  # ZFH: 用毫秒时间戳作为文档ID
            },
            url=url,
            time_taken=time_taken,
            log_datetime=log_datetime,
            useragent=ua, ip=ip)
        doc.save(pipeline="geoip")  # ZFH: 保存时应用 geoip pipeline 解析 IP


class ArticleDocument(Document):
    # ZFH: 文章搜索文档，字段使用 ik 分词器以支持中文搜索
    # ZFH: 正文：ik_max_word 建索引提升召回，ik_smart 查询提升精度
    body = Text(analyzer='ik_max_word', search_analyzer='ik_smart')
    # ZFH: 标题：与正文相同的分词策略，标题命中通常权重更高
    title = Text(analyzer='ik_max_word', search_analyzer='ik_smart')
    # ZFH: 作者信息以 object 内嵌，nickname 支持按作者名检索，id 用于精确定位
    author = Object(properties={
        'nickname': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
        'id': Integer()
    })
    # ZFH: 分类信息内嵌，保留名称用于搜索与展示、ID 用于关联原模型
    category = Object(properties={
        'name': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
        'id': Integer()
    })
    # ZFH: 标签数组内嵌，每个标签同样保存名称与 ID
    tags = Object(properties={
        'name': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
        'id': Integer()
    })

    # ZFH: 发布时间，用于按时间排序或过滤
    pub_time = Date()
    # ZFH: 文章状态（如已发布/草稿）
    status = Text()
    # ZFH: 评论开关状态
    comment_status = Text()
    # ZFH: 文章类型
    type = Text()
    # ZFH: 浏览量，可用于按热度排序
    views = Integer()
    # ZFH: 文章置顶/排序权重
    article_order = Integer()

    class Index:
        # ZFH: ES 索引配置：索引名 blog，单分片、0 副本
        name = 'blog'
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }


class ArticleDocumentManager():
    # ZFH: 文章文档管理器，负责索引创建/删除、模型转文档及重建索引

    def __init__(self):
        # ZFH: 实例化时即创建（或确保）blog 索引
        self.create_index()

    def create_index(self):
        # ZFH: 初始化 ArticleDocument 对应的索引
        ArticleDocument.init()

    def delete_index(self):
        # ZFH: 删除 blog 索引，不存在时忽略异常
        from elasticsearch import Elasticsearch
        es = Elasticsearch(**es_params)
        try:
            es.indices.delete(index='blog')
        except elasticsearch.exceptions.NotFoundError:
            pass

    def convert_to_doc(self, articles):
        # ZFH: 将 Article 模型实例列表转换为 ArticleDocument 列表（含作者/分类/标签嵌套）
        return [
            ArticleDocument(
                meta={
                    'id': article.id},  # ZFH: 用文章ID作为文档ID
                body=article.body,
                title=article.title,
                # ZFH: 作者只保留昵称与 ID，避免把无关的用户字段写入索引
                author={
                    'nickname': article.author.username,
                    'id': article.author.id},
                # ZFH: 分类写入名称与 ID，便于搜索结果直接展示
                category={
                    'name': article.category.name,
                    'id': article.category.id},
                # ZFH: 将全部关联标签转换为内嵌文档列表
                tags=[
                    {
                        'name': t.name,
                        'id': t.id} for t in article.tags.all()],
                pub_time=article.pub_time,
                status=article.status,
                comment_status=article.comment_status,
                type=article.type,
                views=article.views,
                article_order=article.article_order) for article in articles]

    def rebuild(self, articles=None):
        # ZFH: 重建索引：不传 articles 时默认重建全部文章
        ArticleDocument.init()
        articles = articles if articles else Article.objects.all()
        docs = self.convert_to_doc(articles)
        # ZFH: 逐条写入索引，save 会按 meta.id 覆盖同 ID 的旧文档
        for doc in docs:
            doc.save()

    def update_docs(self, docs):
        # ZFH: 批量保存（更新）文档到索引
        for doc in docs:
            doc.save()
