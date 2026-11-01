#!/usr/bin/env python
# encoding: utf-8

# zfh: 模块文档字符串，说明本文件为 Django Blog 全局常量定义
"""
Django Blog 全局常量定义
包含缓存超时时间、缓存键模板等配置
"""


# ===== 缓存过期时间（秒）=====
# zfh: 缓存超时时间常量类，集中管理各类缓存的过期秒数
class CacheTimeout:
    """
    缓存超时时间常量
    集中管理所有缓存过期时间，便于统一调整缓存策略
    """
    # 分钟级
    # zfh: 1分钟，60秒
    MINUTE_1 = 60
    # zfh: 5分钟，300秒
    MINUTE_5 = 60 * 5
    # zfh: 10分钟，600秒
    MINUTE_10 = 60 * 10
    # zfh: 30分钟，1800秒
    MINUTE_30 = 60 * 30

    # 小时级
    # zfh: 1小时，3600秒
    HOUR_1 = 60 * 60
    # zfh: 2小时，7200秒
    HOUR_2 = 60 * 60 * 2
    # zfh: 10小时，36000秒
    HOUR_10 = 60 * 60 * 10
    # zfh: 24小时，86400秒
    HOUR_24 = 60 * 60 * 24

    # 天级
    # zfh: 7天
    DAY_7 = 60 * 60 * 24 * 7
    # zfh: 30天
    DAY_30 = 60 * 60 * 24 * 30

    # 默认缓存时间
    # zfh: 默认缓存超时时间，取10小时
    DEFAULT = HOUR_10  # 10小时


# ===== 缓存键前缀 =====
# zfh: 缓存键模板类，统一管理各业务缓存键的命名格式
class CacheKey:
    """
    缓存键模板
    使用字符串格式化模板，避免缓存键拼写错误
    """
    # 文章相关
    # zfh: 文章评论列表缓存键模板，按文章id区分
    ARTICLE_COMMENTS = 'article_comments_{article_id}'
    # zfh: 文章下一篇缓存键模板，按文章id区分
    ARTICLE_NEXT = 'article_next_{article_id}'
    # zfh: 文章上一篇缓存键模板，按文章id区分
    ARTICLE_PREV = 'article_prev_{article_id}'
    # zfh: 文章所属分类树缓存键模板，按文章id区分
    ARTICLE_CATEGORY_TREE = 'article_category_tree_{article_id}'

    # 列表页缓存
    # zfh: 首页文章列表缓存键模板，按页码区分
    INDEX_LIST = 'index_{page}'
    # zfh: 分类文章列表缓存键模板，按分类名和页码区分
    CATEGORY_LIST = 'category_list_{name}_{page}'
    # zfh: 标签文章列表缓存键模板，按标签名和页码区分
    TAG_LIST = 'tag_{name}_{page}'
    # zfh: 作者文章列表缓存键模板，按作者名和页码区分
    AUTHOR_LIST = 'author_{name}_{page}'
    # zfh: 文章归档页缓存键
    ARCHIVES = 'archives'

    # 分类和标签
    # zfh: 分类树缓存键模板，按分类id区分
    CATEGORY_TREE = 'category_tree_{category_id}'
    # zfh: 子分类列表缓存键模板，按分类id区分
    SUB_CATEGORIES = 'sub_categories_{category_id}'
    # zfh: 标签文章数缓存键模板，按标签id区分
    TAG_ARTICLE_COUNT = 'tag_article_count_{tag_id}'

    # 全局设置
    # zfh: 博客全局设置缓存键
    BLOG_SETTINGS = 'blog_settings'
    # zfh: 当前站点信息缓存键
    CURRENT_SITE = 'current_site'
    # zfh: 侧边栏缓存键模板，按侧边栏类型区分
    SIDEBAR = 'sidebar_{type}'

    # 侧边栏相关
    # zfh: 侧边栏最新文章缓存键
    SIDEBAR_LATEST_ARTICLES = 'sidebar_latest_articles'
    # zfh: 侧边栏热门文章缓存键
    SIDEBAR_HOT_ARTICLES = 'sidebar_hot_articles'
    # zfh: 侧边栏最新评论缓存键
    SIDEBAR_LATEST_COMMENTS = 'sidebar_latest_comments'


# ===== HTTP 状态码 =====
# zfh: HTTP 状态码常量类
class HttpStatus:
    """HTTP 状态码常量"""
    # zfh: 请求成功
    OK = 200
    # zfh: 资源创建成功
    CREATED = 201
    # zfh: 请求成功且无返回内容
    NO_CONTENT = 204

    # zfh: 请求参数错误
    BAD_REQUEST = 400
    # zfh: 未通过认证
    UNAUTHORIZED = 401
    # zfh: 无访问权限
    FORBIDDEN = 403
    # zfh: 资源不存在
    NOT_FOUND = 404

    # zfh: 服务器内部错误
    INTERNAL_SERVER_ERROR = 500
    # zfh: 网关错误
    BAD_GATEWAY = 502
    # zfh: 服务不可用
    SERVICE_UNAVAILABLE = 503


# ===== 分页配置 =====
# zfh: 分页相关常量类
class Pagination:
    """分页相关常量"""
    # zfh: 默认每页条数
    DEFAULT_PAGE_SIZE = 10
    # zfh: 每页最大条数
    MAX_PAGE_SIZE = 100
    # zfh: 页码查询参数名
    PAGE_QUERY_PARAM = 'page'
