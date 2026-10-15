#!/usr/bin/env python
# encoding: utf-8
# zfh: 模块说明：Django Blog 通用工具函数集合


# zfh: 导入日志模块，用于记录运行时日志
import logging
# zfh: 导入操作系统接口，用于路径拼接与目录创建
import os
# zfh: 导入随机数模块，用于生成随机验证码
import random
# zfh: 导入字符串常量集合，提供数字字符
import string
# zfh: 导入 uuid，用于生成唯一文件名
import uuid
# zfh: 导入哈希库，提供 sha256 算法
import hashlib
# zfh: 导入 hmac，用于带密钥的消息摘要
import hmac

# zfh: 导入 bleach，用于 HTML 白名单过滤
import bleach
# zfh: 导入 markdown，用于把 Markdown 文本转成 HTML
import markdown
# zfh: 导入 requests，用于发起 HTTP 请求
import requests
# zfh: 导入 Django 配置对象，读取 settings 中的全局设置
from django.conf import settings
# zfh: 导入 Site 模型，获取当前站点信息
from django.contrib.sites.models import Site
# zfh: 导入 Django 缓存对象
from django.core.cache import cache
# zfh: 导入 static，用于生成静态资源 URL
from django.templatetags.static import static

# zfh: 创建本模块的 logger 实例
logger = logging.getLogger(__name__)


# zfh: 获取文章与评论的最大主键，供全文检索增量更新使用
def get_max_articleid_commentid():
    # zfh: 延迟导入 Article 模型，避免循环导入
    from blog.models import Article
    # zfh: 延迟导入 Comment 模型，避免循环导入
    from comments.models import Comment
    # zfh: 返回最新文章主键与最新评论主键组成的元组
    return (Article.objects.latest().pk, Comment.objects.latest().pk)


# zfh: 用 SECRET_KEY 对给定值做 HMAC-SHA256 摘要
def get_sha256(value):
    # zfh: 把 SECRET_KEY 编码成字节作为密钥
    key = settings.SECRET_KEY.encode('utf-8')
    # zfh: 把传入值转成字符串并编码成字节
    msg = str(value).encode('utf-8')
    # zfh: 返回 HMAC-SHA256 的十六进制摘要字符串
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


# zfh: 带过期时间的缓存装饰器，默认缓存 3 分钟
def cache_decorator(expiration=3 * 60):
    # zfh: 接收被装饰函数的包装层
    def wrapper(func):
        # zfh: 实际替换被装饰函数的新函数
        def news(*args, **kwargs):
            # zfh: 尝试从视图对象上获取自定义缓存 key
            try:
                # zfh: 取第一个位置参数作为视图实例
                view = args[0]
                # zfh: 调用视图的 get_cache_key 获取缓存 key
                key = view.get_cache_key()
            # zfh: 取不到缓存 key 时忽略异常
            except:
                # zfh: 缓存 key 置空，后续用哈希生成
                key = None
            # zfh: 没有缓存 key 时根据函数与参数生成
            if not key:
                # zfh: 用函数与参数的可读表示作为唯一字符串
                unique_str = repr((func, args, kwargs))

                # zfh: 计算唯一字符串的 sha256 摘要
                m = hashlib.sha256(unique_str.encode('utf-8'))
                # zfh: 用摘要十六进制值作为缓存 key
                key = m.hexdigest()
            # zfh: 从缓存读取 key 对应的值
            value = cache.get(key)
            # zfh: 缓存中存在该值时直接使用
            if value is not None:
                # logger.info('cache_decorator get cache:%s key:%s' % (func.__name__, key))
                # zfh: 值为空结果标记时返回 None
                if str(value) == '__default_cache_value__':
                    # zfh: 返回 None，代表原函数结果为空
                    return None
                # zfh: 否则返回缓存中的真实结果
                else:
                    # zfh: 返回缓存值
                    return value
            # zfh: 缓存未命中时执行原函数
            else:
                # zfh: 记录写入缓存的调试日志
                logger.debug(
                    'cache_decorator set cache:%s key:%s' %
                    (func.__name__, key))
                # zfh: 调用原函数取得结果
                value = func(*args, **kwargs)
                # zfh: 结果为 None 时写入空值标记，避免反复穿透查询
                if value is None:
                    # zfh: 用特殊标记占位写入缓存
                    cache.set(key, '__default_cache_value__', expiration)
                # zfh: 结果非空时按过期时间写入缓存
                else:
                    # zfh: 写入真实结果到缓存
                    cache.set(key, value, expiration)
                # zfh: 返回函数执行结果
                return value

        # zfh: 返回包装后的函数
        return news

    # zfh: 返回装饰器本体
    return wrapper


# zfh: 按路径与服务器信息失效对应的视图缓存
def expire_view_cache(path, servername, serverport, key_prefix=None):
    '''
    刷新视图缓存
    :param path:url路径
    :param servername:host
    :param serverport:端口
    :param key_prefix:前缀
    :return:是否成功
    '''
    # zfh: 延迟导入 HttpRequest，用于构造请求对象
    from django.http import HttpRequest
    # zfh: 延迟导入 get_cache_key，用于计算视图缓存 key
    from django.utils.cache import get_cache_key

    # zfh: 构造一个空的请求对象
    request = HttpRequest()
    # zfh: 设置请求的服务器名与端口
    request.META = {'SERVER_NAME': servername, 'SERVER_PORT': serverport}
    # zfh: 设置请求路径
    request.path = path

    # zfh: 根据请求计算缓存 key
    key = get_cache_key(request, key_prefix=key_prefix, cache=cache)
    # zfh: 成功算出缓存 key 时执行删除
    if key:
        # zfh: 记录即将失效的缓存 key 日志
        logger.info('expire_view_cache:get key:{path}'.format(path=path))
        # zfh: 缓存中确实存在该 key 时删除它
        if cache.get(key):
            # zfh: 删除缓存项
            cache.delete(key)
        # zfh: 返回失效成功
        return True
    # zfh: 未取到缓存 key 时返回失败
    return False


# zfh: 缓存装饰器：缓存当前站点对象
@cache_decorator()
# zfh: 获取当前 Django Site 对象
def get_current_site():
    # zfh: 按 SITE_ID 查询当前站点
    site = Site.objects.get_current()
    # zfh: 返回站点对象
    return site


# zfh: Markdown 转换工具类，提供带目录与不带目录的转换
class CommonMarkdown:
    # zfh: 静态方法：把 Markdown 文本转换为 HTML 与目录
    @staticmethod
    def _convert_markdown(value):
        # zfh: 创建 Markdown 解析器并启用扩展
        md = markdown.Markdown(
            extensions=[
                'extra',
                'codehilite',
                'toc',
                'tables',
            ]
        )
        # zfh: 把 Markdown 文本转换成 HTML 正文
        body = md.convert(value)
        # zfh: 取出解析过程中生成的目录
        toc = md.toc
        # zfh: 返回正文与目录
        return body, toc

    # zfh: 静态方法：返回正文与目录
    @staticmethod
    def get_markdown_with_toc(value):
        # zfh: 调用内部方法完成转换
        body, toc = CommonMarkdown._convert_markdown(value)
        # zfh: 返回正文与目录
        return body, toc

    # zfh: 静态方法：只返回正文 HTML
    @staticmethod
    def get_markdown(value):
        # zfh: 调用内部方法完成转换
        body, toc = CommonMarkdown._convert_markdown(value)
        # zfh: 只返回正文
        return body


# zfh: 通过信号异步发送邮件
def send_email(emailto, title, content):
    # zfh: 延迟导入邮件信号，避免循环导入
    from djangoblog.blog_signals import send_email_signal
    # zfh: 发送信号，由接收方执行实际邮件发送
    send_email_signal.send(
        send_email.__class__,
        emailto=emailto,
        title=title,
        content=content)


# zfh: 生成 6 位随机数字验证码
def generate_code() -> str:
    """生成随机数验证码"""
    # zfh: 从数字字符中随机取 6 位拼成验证码
    return ''.join(random.sample(string.digits, 6))


# zfh: 把字典拼接成 URL 查询字符串
def parse_dict_to_url(dict):
    # zfh: 延迟导入 quote，用于对参数做 URL 编码
    from urllib.parse import quote
    # zfh: 按 k=v 拼接并用 & 连接，键值都做 URL 编码
    url = '&'.join(['{}={}'.format(quote(k, safe='/'), quote(v, safe='/'))
                    for k, v in dict.items()])
    # zfh: 返回拼接好的查询字符串
    return url


# zfh: 获取博客全局配置，优先读缓存
def get_blog_setting():
    # zfh: 从缓存读取博客配置
    value = cache.get('get_blog_setting')
    # zfh: 缓存命中时直接返回
    if value:
        # zfh: 返回缓存中的配置对象
        return value
    # zfh: 缓存未命中时查询数据库
    else:
        # zfh: 延迟导入博客配置模型，避免循环导入
        from blog.models import BlogSettings
        # zfh: 配置表为空时创建默认配置
        if not BlogSettings.objects.count():
            # zfh: 实例化一个配置对象
            setting = BlogSettings()
            # zfh: 设置站点名称
            setting.site_name = 'djangoblog'
            # zfh: 设置站点描述
            setting.site_description = '基于Django的博客系统'
            # zfh: 设置 SEO 描述
            setting.site_seo_description = '基于Django的博客系统'
            # zfh: 设置站点关键词
            setting.site_keywords = 'Django,Python'
            # zfh: 设置文章摘要截取长度
            setting.article_sub_length = 300
            # zfh: 设置侧边栏文章显示数量
            setting.sidebar_article_count = 10
            # zfh: 设置侧边栏评论显示数量
            setting.sidebar_comment_count = 5
            # zfh: 关闭 Google AdSense 广告
            setting.show_google_adsense = False
            # zfh: 开启站点评论功能
            setting.open_site_comment = True
            # zfh: 统计代码留空
            setting.analytics_code = ''
            # zfh: 备案号留空
            setting.beian_code = ''
            # zfh: 关闭公安备案展示
            setting.show_gongan_code = False
            # zfh: 关闭评论审核
            setting.comment_need_review = False
            # zfh: 保存默认配置到数据库
            setting.save()
        # zfh: 取出配置表中的第一条配置
        value = BlogSettings.objects.first()
        # zfh: 记录配置已写入缓存
        logger.info('set cache get_blog_setting')
        # zfh: 把配置对象写入缓存
        cache.set('get_blog_setting', value)
        # zfh: 返回配置对象
        return value


# zfh: 下载并保存用户头像到本地静态目录
def save_user_avatar(url):
    '''
    保存用户头像
    :param url:头像url
    :return: 本地路径
    '''
    # zfh: 记录待处理的头像地址
    logger.info(url)

    # zfh: 捕获下载与保存过程中的异常
    try:
        # zfh: 拼接头像保存目录
        basedir = os.path.join(settings.STATICFILES, 'avatar')
        # zfh: 请求头像地址，超时 2 秒
        rsp = requests.get(url, timeout=2)
        # zfh: 仅当响应状态码为 200 时处理
        if rsp.status_code == 200:
            # zfh: 保存目录不存在时创建
            if not os.path.exists(basedir):
                # zfh: 递归创建目录
                os.makedirs(basedir)

            # zfh: 可识别的图片后缀列表
            image_extensions = ['.jpg', '.png', 'jpeg', '.gif']
            # zfh: 判断 url 是否以图片后缀结尾
            isimage = len([i for i in image_extensions if url.endswith(i)]) > 0
            # zfh: 是图片则取原后缀，否则统一用 .jpg
            ext = os.path.splitext(url)[1] if isimage else '.jpg'
            # zfh: 用 uuid 生成不重复的文件名
            save_filename = str(uuid.uuid4().hex) + ext
            # zfh: 记录保存路径日志
            logger.info('保存用户头像:' + basedir + save_filename)
            # zfh: 以二进制写模式打开目标文件
            with open(os.path.join(basedir, save_filename), 'wb+') as file:
                # zfh: 写入响应内容
                file.write(rsp.content)
            # zfh: 返回头像的静态资源 URL
            return static('avatar/' + save_filename)
    # zfh: 出现异常时记录错误并返回默认头像
    except Exception as e:
        # zfh: 记录异常信息
        logger.error(e)
        # zfh: 返回默认头像地址
        return static('blog/img/avatar.png')


# zfh: 删除侧边栏相关的全部缓存
def delete_sidebar_cache():
    # zfh: 延迟导入链接展示类型，避免循环导入
    from blog.models import LinkShowType
    # zfh: 为每种链接展示类型生成对应的缓存 key
    keys = ["sidebar" + x for x in LinkShowType.values]
    # zfh: 逐个删除侧边栏缓存
    for k in keys:
        # zfh: 记录即将删除的缓存 key
        logger.info('delete sidebar key:' + k)
        # zfh: 删除该缓存项
        cache.delete(k)


# zfh: 按模板片段前缀与参数删除对应的模板缓存
def delete_view_cache(prefix, keys):
    # zfh: 延迟导入模板片段缓存 key 生成函数
    from django.core.cache.utils import make_template_fragment_key
    # zfh: 根据前缀与参数生成模板片段缓存 key
    key = make_template_fragment_key(prefix, keys)
    # zfh: 删除该缓存项
    cache.delete(key)


# zfh: 获取静态资源的基础 URL
def get_resource_url():
    # zfh: 配置了 STATIC_URL 时直接使用
    if settings.STATIC_URL:
        # zfh: 返回配置中的静态资源前缀
        return settings.STATIC_URL
    # zfh: 未配置时按站点域名拼接默认地址
    else:
        # zfh: 获取当前站点对象
        site = get_current_site()
        # zfh: 拼接并返回默认静态资源地址
        return 'http://' + site.domain + '/static/'


# 允许的HTML标签白名单 - 支持markdown常用元素
# zfh: 允许保留的 HTML 标签白名单
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'ul', 'pre', 'strong',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',  # 标题
    'p', 'span', 'div', 'br', 'hr',  # 段落和分隔
    'table', 'thead', 'tbody', 'tr', 'th', 'td',  # 表格
    'dl', 'dt', 'dd',  # 定义列表
    'img',  # 图片（需配合ALLOWED_ATTRIBUTES限制src）
    'del', 'ins', 'sub', 'sup',  # 文本修饰
]

# 安全的class值白名单 - 只允许代码高亮相关的class
# zfh: 允许保留的 CSS class 白名单，主要是代码高亮类名
ALLOWED_CLASSES = [
    'codehilite', 'highlight', 'hll', 'c', 'err', 'k', 'l', 'n', 'o', 'p', 'cm', 'cp', 'c1', 'cs',
    'gd', 'ge', 'gr', 'gh', 'gi', 'go', 'gp', 'gs', 'gu', 'gt', 'kc', 'kd', 'kn', 'kp', 'kr', 'kt',
    'ld', 'm', 'mf', 'mh', 'mi', 'mo', 'na', 'nb', 'nc', 'no', 'nd', 'ni', 'ne', 'nf', 'nl', 'nn',
    'nt', 'nv', 'ow', 'w', 'mb', 'mh', 'mi', 'mo', 'sb', 'sc', 'sd', 'se', 'sh', 'si', 'sx', 's2',
    's1', 'ss', 'bp', 'vc', 'vg', 'vi', 'il'
]

# zfh: bleach 属性过滤器：只保留白名单内的 class 值
def class_filter(tag, name, value):
    """自定义class属性过滤器"""
    # zfh: 只处理 class 属性
    if name == 'class':
        # 只允许预定义的安全class值
        # zfh: 过滤出白名单中的 class 值
        allowed_classes = [cls for cls in value.split() if cls in ALLOWED_CLASSES]
        # zfh: 有合法 class 时拼接返回，否则返回 False 表示丢弃
        return ' '.join(allowed_classes) if allowed_classes else False
    # zfh: 非 class 属性原样返回
    return value

# 安全的属性白名单
# zfh: 各标签允许保留的属性白名单
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],  # rel="nofollow" 用于外部链接
    'abbr': ['title'], 
    'acronym': ['title'],
    'img': ['src', 'alt', 'title', 'width', 'height'],  # 图片属性
    'table': ['border', 'cellpadding', 'cellspacing'],
    'th': ['align', 'valign'],
    'td': ['align', 'valign'],
    'span': class_filter,
    'div': class_filter,
    'pre': class_filter,
    'code': class_filter
}

# 安全的协议白名单 - 防止javascript:等危险协议
# zfh: 允许出现在链接中的协议白名单
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

# zfh: 用 bleach 白名单清理 HTML，防止 XSS 攻击
def sanitize_html(html):
    """
    安全的HTML清理函数
    使用bleach库进行白名单过滤，防止XSS攻击
    """
    # zfh: 按标签、属性、协议白名单过滤 HTML
    cleaned = bleach.clean(
        html, 
        tags=ALLOWED_TAGS, 
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,  # 限制允许的协议
        strip=True,  # 移除不允许的标签而不是转义
        strip_comments=True  # 移除HTML注释
    )
    
    # 移除空的 style 属性（bleach 有时会保留 style=""）
    # zfh: 延迟导入正则模块
    import re
    # zfh: 删除内容为空的 style 属性
    cleaned = re.sub(r'\s*style\s*=\s*["\'][\s]*["\']', '', cleaned)
    
    # zfh: 返回清理后的 HTML
    return cleaned
