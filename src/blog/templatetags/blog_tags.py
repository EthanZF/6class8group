# ZFH: 博客模板标签库：集中注册 blog 应用在模板中使用的 simple_tag、filter 与 inclusion_tag
# ZFH: 主要职责：文章正文渲染与摘要、侧边栏数据装配、分页链接、搜索高亮、头像以及插件资源注入
# ZFH: 标准库导入：json 负责序列化、random 负责随机配色；hashlib/urllib 为历史遗留导入，当前未直接使用
import hashlib
import json
import logging
import random
import urllib

# ZFH: Django 核心导入：template 用于注册标签库，settings 读取时间格式等配置，Q 用于构造 OR 查询条件
from django import template
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import stringfilter
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

# ZFH: 项目内部导入：模型层（文章/分类/标签/友链/侧边栏）、评论模型、通用工具以及插件钩子
from blog.models import Article, Category, Tag, Links, SideBar, LinkShowType
from comments.models import Comment
from djangoblog.utils import CommonMarkdown, sanitize_html
from djangoblog.utils import cache
from djangoblog.utils import get_current_site
from oauth.models import OAuthUser
from djangoblog.plugin_manage import hooks

# ZFH: 模块级日志器，标签执行中的异常与缓存事件统一记录到这里
logger = logging.getLogger(__name__)

# ZFH: 创建模板标签库实例，下方所有 @register 装饰器都会把函数注册到该实例
register = template.Library()


@register.simple_tag(takes_context=True)
def head_meta(context):
    # ZFH: 简单标签 head_meta，接收模板上下文，应用 head_meta 钩子过滤器，返回安全 HTML，用于注入页面 <head> 元信息
    return mark_safe(hooks.apply_filters('head_meta', '', context))


@register.simple_tag
def timeformat(data):
    # ZFH: 简单标签 timeformat，将日期对象按 settings.TIME_FORMAT 格式化为时间字符串，异常时记录日志并返回空串
    try:
        return data.strftime(settings.TIME_FORMAT)
    except Exception as e:
        logger.error(e)
        return ""


@register.simple_tag
def datetimeformat(data):
    # ZFH: 简单标签 datetimeformat，将日期对象按 settings.DATE_TIME_FORMAT 格式化为日期时间字符串，异常时记录日志并返回空串
    try:
        return data.strftime(settings.DATE_TIME_FORMAT)
    except Exception as e:
        logger.error(e)
        return ""


@register.filter()
@stringfilter
def custom_markdown(content):
    """
    ZFH: 过滤器 custom_markdown，将 Markdown 文本转为 HTML 后应用文章内容插件钩子，返回安全 HTML，用于文章内容渲染
    通用markdown过滤器，应用文章内容插件
    主要用于文章内容处理
    """
    html_content = CommonMarkdown.get_markdown(content)
    # ZFH: 调用 CommonMarkdown 把 Markdown 源码转换为 HTML 片段
    
    # 然后应用插件过滤器优化HTML
    from djangoblog.plugin_manage import hooks
    from djangoblog.plugin_manage.hook_constants import ARTICLE_CONTENT_HOOK_NAME
    # ZFH: 交给插件系统统一处理文章内容（如代码高亮、图片懒加载）
    optimized_html = hooks.apply_filters(ARTICLE_CONTENT_HOOK_NAME, html_content)
    
    return mark_safe(optimized_html)


@register.filter()
@stringfilter
def sidebar_markdown(content):
    # ZFH: 过滤器 sidebar_markdown，将侧边栏文本转为 Markdown HTML，返回安全 HTML，用于自定义侧边栏内容渲染
    # ZFH: 侧边栏内容同样走 Markdown 渲染，但不再套用文章内容插件
    html_content = CommonMarkdown.get_markdown(content)
    return mark_safe(html_content)


@register.simple_tag(takes_context=True)
def render_article_content(context, article, is_summary=False):
    """
    ZFH: 简单标签 render_article_content，将文章正文渲染为 HTML 并应用文章内容插件钩子，支持摘要截断与搜索高亮，返回安全 HTML
    渲染文章内容，包含完整的上下文信息供插件使用
    
    Args:
        context: 模板上下文
        article: 文章对象
        is_summary: 是否为摘要模式（首页使用）
    """
    if not article or not hasattr(article, 'body'):
        return ''
    
    # 先转换Markdown为HTML
    # ZFH: 第一步把 Markdown 正文转换成 HTML，后续再做摘要截断与插件处理
    html_content = CommonMarkdown.get_markdown(article.body)
    
    # 如果是摘要模式，先截断内容再应用插件
    # ZFH: 摘要模式需要限制长度，普通详情页则输出完整内容
    if is_summary:
        # 从配置中获取摘要长度
        from djangoblog.utils import get_blog_setting
        from django.template.defaultfilters import truncatechars_html

        blogsetting = get_blog_setting()
        summary_length = blogsetting.article_sub_length

        # 使用truncatechars_html保留HTML标签结构，正确截断HTML内容
        html_content = truncatechars_html(html_content, summary_length)
    
    # 然后应用插件过滤器，传递完整的上下文
    from djangoblog.plugin_manage import hooks
    from djangoblog.plugin_manage.hook_constants import ARTICLE_CONTENT_HOOK_NAME
    
    # 获取request对象
    # ZFH: 从模板上下文取出 request，供插件按登录状态或请求路径调整输出
    request = context.get('request')
    
    # 应用所有文章内容相关的插件
    # 注意：摘要模式下某些插件（如版权声明）可能不适用
    # ZFH: 把 article/request/context/is_summary 一并传给插件，插件可据此跳过摘要场景
    optimized_html = hooks.apply_filters(
        ARTICLE_CONTENT_HOOK_NAME,
        html_content,
        article=article,
        request=request,
        context=context,
        is_summary=is_summary  # 传递摘要标志，插件可以据此调整行为
    )

    # 如果有搜索查询，应用高亮
    query = context.get('query')
    # ZFH: 只有摘要模式才在服务端做高亮，避免重复处理整篇正文
    if query and is_summary:
        optimized_html = highlight_content(optimized_html, query)

    return mark_safe(optimized_html)


@register.simple_tag
def get_markdown_toc(content):
    # ZFH: 简单标签 get_markdown_toc，解析 Markdown 内容并返回其目录（TOC）HTML，用于文章目录展示
    from djangoblog.utils import CommonMarkdown
    body, toc = CommonMarkdown.get_markdown_with_toc(content)
    return mark_safe(toc)


@register.simple_tag
def current_nav_item(request):
    """ZFH: 简单标签 current_nav_item，根据 request.path 判断当前导航项，返回对应标识字符串（index/archives/links/category 或空串）"""
    path = request.path
    # ZFH: 取当前请求路径，按前缀逐段匹配所属导航区域
    if path == '/' or path.startswith('/page/'):
        return 'index'
    elif path.startswith('/archives'):
        return 'archives'
    elif path.startswith('/links'):
        return 'links'
    elif path.startswith('/category/'):
        return 'category'
    # ZFH: 标签页复用分类导航的高亮状态，避免导航栏失去选中效果
    elif path.startswith('/tag/'):
        return 'category'
    return ''


@register.filter()
@stringfilter
def comment_markdown(content):
    # ZFH: 过滤器 comment_markdown，将评论内容转为 Markdown HTML 并做安全清洗，返回安全 HTML
    content = CommonMarkdown.get_markdown(content)
    return mark_safe(sanitize_html(content))


@register.filter(is_safe=True)
def to_json(value):
    """
    ZFH: 过滤器 to_json，将 Python 对象序列化为 JSON 字符串（ensure_ascii=False 支持 emoji），失败时返回安全空对象 '{}'
    将 Python 对象转换为 JSON 字符串，用于模板中传递给 JavaScript
    使用 ensure_ascii=False 以支持 emoji 等 unicode 字符
    """
    try:
        # ZFH: ensure_ascii=False 保留中文与 emoji 原文，mark_safe 避免模板二次转义
        return mark_safe(json.dumps(value, ensure_ascii=False))
    except (TypeError, ValueError):
        # ZFH: 对象无法序列化时返回空对象字面量，保证前端 JSON 解析不报错
        return mark_safe('{}')


@register.filter
def get_reactions_for_user(comment, user):
    """
    ZFH: 过滤器 get_reactions_for_user，获取评论的 reactions 汇总数据，已登录用户传入 user，未登录传 None，异常时返回空字典
    获取评论的 reactions 数据（过滤器方式）
    用法: {{ comment|get_reactions_for_user:user }}
    """
    try:
        # ZFH: 匿名用户传 None，模型层据此只返回公开的表情统计
        return comment.get_reactions_summary(user if user.is_authenticated else None)
    except Exception as e:
        # ZFH: 评论可能已被删除或缺少关联数据，异常时降级为空字典
        logger.error(f"Error getting reactions for comment {comment.id}: {e}")
        return {}




@register.filter(is_safe=True)
@stringfilter
def truncatechars_content(content):
    """
    ZFH: 过滤器 truncatechars_content，按配置的文章摘要长度截断 HTML 内容，返回文章摘要
    获得文章内容的摘要
    :param content:
    :return:
    """
    from django.template.defaultfilters import truncatechars_html
    from djangoblog.utils import get_blog_setting
    blogsetting = get_blog_setting()
    # ZFH: 按后台配置的文章摘要长度截断，未闭合标签由 truncatechars_html 自动补全
    return truncatechars_html(content, blogsetting.article_sub_length)


# ZFH: 过滤器 truncate：先剥离 HTML 标签再截取前 150 个字符，用于生成纯文本预览
@register.filter(is_safe=True)
@stringfilter
def truncate(content):
    from django.utils.html import strip_tags

    # ZFH: strip_tags 去掉全部标签，切片截断到固定 150 字符
    return strip_tags(content)[:150]


# ZFH: inclusion_tag load_breadcrumb：渲染文章面包屑，返回从站点根到当前分类的名称与链接列表
@register.inclusion_tag('blog/tags/breadcrumb.html')
def load_breadcrumb(article):
    """
    获得文章面包屑
    :param article:
    :return:
    """
    # ZFH: 取文章所属分类的祖先链，作为面包屑的中间层级
    names = article.get_category_tree()
    from djangoblog.utils import get_blog_setting
    blogsetting = get_blog_setting()
    site = get_current_site().domain
    names.append((blogsetting.site_name, '/'))
    # ZFH: 反转后从站点根开始排列，符合面包屑自上而下的展示顺序
    names = names[::-1]

    # ZFH: count 为层级数加一，供模板计算分隔符数量
    return {
        'names': names,
        'title': article.title,
        'count': len(names) + 1
    }


# ZFH: inclusion_tag load_articletags：渲染文章标签列表，每个标签附带链接、文章数与随机配色
@register.inclusion_tag('blog/tags/article_tag_list.html')
def load_articletags(article):
    """
    文章标签
    :param article:
    :return:
    """
    tags = article.tags.all()
    tags_list = []
    # ZFH: 遍历标签逐个计算文章数，并随机取一个 Bootstrap 颜色用于标签徽章
    for tag in tags:
        url = tag.get_absolute_url()
        count = tag.get_article_count()
        tags_list.append((
            url, count, tag, random.choice(settings.BOOTSTRAP_COLOR_TYPES)
        ))
    return {
        'article_tags_list': tags_list
    }


# ZFH: inclusion_tag load_sidebar：装配侧边栏所需的文章、分类、友链、评论与标签云，并按 linktype 缓存
@register.inclusion_tag('blog/tags/sidebar.html')
def load_sidebar(user, linktype):
    """
    加载侧边栏
    :return:
    """
    # ZFH: 先按 linktype 读取整份侧边栏缓存，命中时只需替换当前用户对象
    value = cache.get("sidebar" + linktype)
    if value:
        value['user'] = user
        return value
    else:
    # ZFH: 缓存未命中，重新查询数据库组装侧边栏数据
        logger.info('load sidebar')
        from djangoblog.utils import get_blog_setting
        blogsetting = get_blog_setting()

        # 优化：添加select_related/prefetch_related减少查询
    # ZFH: 只取已发布文章（status='p'），并用 select_related 预取作者与分类避免 N+1 查询
        recent_articles = Article.objects.filter(
            status='p'
        ).select_related('author', 'category')[:blogsetting.sidebar_article_count]

    # ZFH: 全部分类与启用中的自定义侧边栏，后者按 sequence 排序控制展示顺序
        sidebar_categorys = Category.objects.all()

        extra_sidebars = SideBar.objects.filter(
            is_enable=True
        ).order_by('sequence')

    # ZFH: 按浏览量倒序取热门文章，数量同样受侧边栏配置限制
        most_read_articles = Article.objects.filter(
            status='p'
        ).select_related('author', 'category').order_by(
            '-views'
        )[:blogsetting.sidebar_article_count]

    # ZFH: 提取文章发布月份用于归档列表，DESC 保证最新月份排在前面
        dates = Article.objects.datetimes('creation_time', 'month', order='DESC')

    # ZFH: 友链按显示类型过滤：匹配当前 linktype 或设置为“全部显示”的友链
        links = Links.objects.filter(is_enable=True).filter(
            Q(show_type=str(linktype)) | Q(show_type=LinkShowType.A)
        )

    # ZFH: 最新评论只取启用状态的前若干条，供侧边栏评论区块展示
        commment_list = Comment.objects.filter(
            is_enable=True
        ).select_related('author').order_by('-id')[:blogsetting.sidebar_comment_count]
        # 标签云 — 按文章数排序，取 top 20，size = (count/avg)*5+10
    # ZFH: 标签云字号系数：(文章数/平均值)*5+10，取前 20 个热门标签
        increment = 5
        tags = Tag.objects.all()
        sidebar_tags = None
        if tags and len(tags) > 0:
    # ZFH: 过滤掉文章数为 0 的标签后按文章数降序排序，再取前 20 个
            s = sorted(
                [t for t in [(t, t.get_article_count()) for t in tags] if t[1]],
                key=lambda x: x[1], reverse=True
            )[:20]
    # ZFH: 计算平均文章数，为 0 时退化为 1，避免后续除法报错
            count = sum([t[1] for t in s])
            dd = 1 if (count == 0 or not len(s)) else count / len(s)
            sidebar_tags = list(
                map(lambda x: (x[0], x[1], (x[1] / dd) * increment + 10), s))

    # ZFH: 汇总所有侧边栏数据为一个字典，直接作为 inclusion_tag 的渲染上下文
        value = {
            'recent_articles': recent_articles,
            'sidebar_categorys': sidebar_categorys,
            'most_read_articles': most_read_articles,
            'article_dates': dates,
            'sidebar_comments': commment_list,
            'sidabar_links': links,
            'show_google_adsense': blogsetting.show_google_adsense,
            'google_adsense_codes': blogsetting.google_adsense_codes,
            'open_site_comment': blogsetting.open_site_comment,
            'show_gongan_code': blogsetting.show_gongan_code,
            'sidebar_tags': sidebar_tags,
            'extra_sidebars': extra_sidebars
        }
    # ZFH: 整份侧边栏缓存 3 小时（60*60*60*3 秒），显著减少首页的重复查询
        cache.set("sidebar" + linktype, value, 60 * 60 * 60 * 3)
        logger.info('set sidebar cache.key:{key}'.format(key="sidebar" + linktype))
    # ZFH: 缓存中不保存用户对象，返回前再注入当前用户，避免不同会话串用缓存
        value['user'] = user
        return value


# ZFH: inclusion_tag load_article_metas：把文章与当前用户直接交给 meta 信息模板片段
@register.inclusion_tag('blog/tags/article_meta_info.html')
def load_article_metas(article, user):
    """
    获得文章meta信息
    :param article:
    :return:
    """
    return {
        'article': article,
        'user': user
    }


# ZFH: inclusion_tag load_pagination_info：为首页/标签/分类/作者归档计算上一页、下一页与数字页码
@register.inclusion_tag('blog/tags/article_pagination.html')
def load_pagination_info(page_obj, page_type, tag_name):
    previous_url = ''
    next_url = ''

    # ZFH: 标签与分类分页需要 slug 而非名称，提前查一次避免在页码循环里重复查询
    # Pre-resolve slug for tag/category to avoid repeated DB queries
    _slug = None
    if page_type == '分类标签归档':
        _slug = get_object_or_404(Tag, name=tag_name).slug
    elif page_type == '分类目录归档':
        _slug = get_object_or_404(Category, name=tag_name).slug

    # ZFH: 内部函数按 page_type 选择对应路由名，并复用已解析的 slug 生成指定页码的 URL
    def _build_url(page_number):
        """Build URL for a given page number based on page_type."""
        if page_type == '':
            return reverse('blog:index_page', kwargs={'page': page_number})
        elif page_type == '分类标签归档':
            return reverse('blog:tag_detail_page',
                           kwargs={'page': page_number, 'tag_name': _slug})
        elif page_type == '作者文章归档':
            return reverse('blog:author_detail_page',
                           kwargs={'page': page_number, 'author_name': tag_name})
        elif page_type == '分类目录归档':
            return reverse('blog:category_detail_page',
                           kwargs={'page': page_number, 'category_name': _slug})
        return ''

    # ZFH: 分别生成下一页与上一页链接，到达边界时保持空串
    if page_obj.has_next():
        next_url = _build_url(page_obj.next_page_number())
    if page_obj.has_previous():
        previous_url = _build_url(page_obj.previous_page_number())

    # ZFH: 构造数字页码区间：页数少时全展示，页数多时只保留首尾与当前页附近
    # Build page range with URLs for numbered pagination
    current_page = page_obj.number
    total_pages = page_obj.paginator.num_pages
    page_range = []

    if total_pages > 1:
        # Show at most 5 page numbers centered around current page
        # with ellipsis indicators
        # ZFH: 总页数不超过 7 页时直接全部列出，无需省略号
        if total_pages <= 7:
            nums = range(1, total_pages + 1)
        else:
            # ZFH: 页数较多时固定保留首页与末页，并加入当前页前后各两页
            nums = set()
            nums.add(1)
            nums.add(total_pages)
            for i in range(max(1, current_page - 2), min(total_pages + 1, current_page + 3)):
                nums.add(i)
            nums = sorted(nums)

        # ZFH: 相邻页码不连续时插入省略号标记，由模板渲染为 ...
        last_num = 0
        for num in nums:
            if num - last_num > 1:
                page_range.append({'type': 'ellipsis'})
            page_range.append({
                'type': 'page',
                'number': num,
                'url': _build_url(num),
                'is_current': num == current_page,
            })
            last_num = num

    # ZFH: 返回给分页模板片段：前后页 URL、分页对象以及数字页码列表
    return {
        'previous_url': previous_url,
        'next_url': next_url,
        'page_obj': page_obj,
        'page_range': page_range,
    }


# ZFH: inclusion_tag load_article_detail：渲染文章列表或详情，isindex 控制是否只展示摘要
@register.inclusion_tag('blog/tags/article_info.html')
def load_article_detail(article, isindex, user, query=None):
    """
    加载文章详情
    :param article:
    :param isindex:是否列表页，若是列表页只显示摘要
    :param query: 搜索查询词（用于高亮）
    :return:
    """
    from djangoblog.utils import get_blog_setting
    blogsetting = get_blog_setting()

    # ZFH: 附带站点评论开关与搜索词，模板据此决定评论区与关键词标记
    return {
        'article': article,
        'isindex': isindex,
        'user': user,
        'query': query,  # 传递查询词
        'open_site_comment': blogsetting.open_site_comment,
    }


# ZFH: inclusion_tag load_article_detail_with_highlight：在文章详情片段中额外传入高亮数据，供搜索页使用
@register.inclusion_tag('blog/tags/article_info_highlight.html')
def load_article_detail_with_highlight(article, highlighted, isindex, user):
    """
    加载文章详情（带搜索高亮）
    :param article: 文章对象
    :param highlighted: 高亮数据字典 {'title': [...], 'body': [...]}
    :param isindex: 是否列表页，若是列表页只显示摘要
    :param user: 当前用户
    :return:
    """
    from djangoblog.utils import get_blog_setting
    blogsetting = get_blog_setting()

    # ZFH: highlighted 为 {'title': [...], 'body': [...]} 结构，模板直接取用已切分的高亮片段
    return {
        'article': article,
        'highlighted': highlighted,
        'isindex': isindex,
        'user': user,
        'open_site_comment': blogsetting.open_site_comment,
    }


# ZFH: 过滤器 highlight_search_term：对纯文本按空格分词并用 <mark> 包裹，实现大小写不敏感高亮
@register.filter
def highlight_search_term(text, query):
    """
    在文本中高亮搜索关键词
    :param text: 原始文本
    :param query: 搜索查询词
    :return: 高亮后的HTML
    """
    if not query or not text:
        return text

    import re
    # 分词处理（支持空格分隔的多个词）
    # ZFH: 按空格切分查询词，支持多关键词同时高亮
    terms = query.split()

    for term in terms:
        # ZFH: 跳过单字符词，避免匹配范围过大导致页面到处是标记
        if len(term) < 2:  # 忽略单字符
            continue
        # 使用正则替换，不区分大小写，但保留原文本的大小写
        # ZFH: re.escape 转义正则特殊字符，IGNORECASE 保证大小写不敏感且保留原文大小写
        pattern = re.compile(r'(' + re.escape(term) + r')', re.IGNORECASE)
        text = pattern.sub(r'<mark>\1</mark>', text)

    return mark_safe(text)


# ZFH: 过滤器 highlight_content：先剥离 HTML 得到纯文本再高亮，用于搜索结果摘要展示
@register.filter
def highlight_content(html_content, query):
    """
    对HTML内容提取纯文本并进行搜索高亮
    会去除HTML标签，只保留文本内容，并高亮搜索关键词
    跳过代码块中的内容
    :param html_content: HTML内容
    :param query: 搜索查询词
    :return: 高亮后的纯文本（包含mark标签）
    """
    if not query or not html_content:
        return html_content

    from bs4 import BeautifulSoup
    import re

    # 使用BeautifulSoup解析HTML
    # ZFH: 用 BeautifulSoup 解析 HTML 片段，便于按标签精确剔除内容
    soup = BeautifulSoup(html_content, 'html.parser')

    # 移除代码块、脚本等标签（不要它们的内容）
    # ZFH: 移除 code/pre/script/style 节点，避免高亮破坏代码或脚本内容
    for tag in soup.find_all(['code', 'pre', 'script', 'style']):
        tag.decompose()

    # 提取纯文本
    # ZFH: 提取纯文本并用空格连接，防止相邻标签的文字粘连在一起
    text = soup.get_text(separator=' ', strip=True)

    # 分词处理（支持空格分隔的多个词）
    # ZFH: 只保留长度不少于 2 的有效查询词
    terms = [term for term in query.split() if len(term) >= 2]

    # ZFH: 没有有效关键词时直接返回纯文本，不再做正则替换
    if not terms:
        return text

    # 对纯文本进行高亮
    # ZFH: 逐个关键词做不区分大小写替换，并包裹 <mark> 标签
    for term in terms:
        # 使用正则替换，不区分大小写
        pattern = re.compile(r'(' + re.escape(term) + r')', re.IGNORECASE)
        text = pattern.sub(r'<mark>\1</mark>', text)

    return mark_safe(text)


# 返回用户头像URL
# 模板使用方法:  {{ email|gravatar_url:150 }}
# ZFH: 过滤器 gravatar_url：返回用户头像 URL，优先取 OAuth 头像，否则回退到站点默认头像
@register.filter
def gravatar_url(email, size=40):
    """获得用户头像 - 优先使用OAuth头像，否则使用默认头像"""
    # ZFH: 头像 URL 以 'avatar/邮箱' 为键缓存，避免每次渲染都查库
    cachekey = 'avatar/' + email
    url = cache.get(cachekey)
    # ZFH: 命中缓存直接返回，缓存有效期为 24 小时
    if url:
        return url
    
    # 检查OAuth用户是否有自定义头像
    # ZFH: 查询该邮箱绑定的所有 OAuth 用户，同一邮箱可能存在多个第三方账号
    usermodels = OAuthUser.objects.filter(email=email)
    if usermodels:
        # 过滤出有头像的用户
        # ZFH: 只保留 picture 字段非空的账号，其余无法提供头像
        users_with_picture = list(filter(lambda x: x.picture is not None, usermodels))
        if users_with_picture:
            # 获取默认头像路径用于比较
            # ZFH: 取站点默认头像路径作为基准，用于识别 OAuth 返回的是否只是占位图
            default_avatar_path = static('blog/img/avatar.png')
            
            # 优先选择非默认头像的用户，否则选择第一个
            # ZFH: 优先选择非默认头像，排除与默认图相同或以 /avatar.png 结尾的地址
            non_default_users = [u for u in users_with_picture if u.picture != default_avatar_path and not u.picture.endswith('/avatar.png')]
            selected_user = non_default_users[0] if non_default_users else users_with_picture[0]
            
            # ZFH: 选定头像后写入缓存，并记录来源类型便于排查头像问题
            url = selected_user.picture
            cache.set(cachekey, url, 60 * 60 * 24)  # 缓存24小时
            
            avatar_type = 'non-default' if non_default_users else 'default'
            logger.info('Using {} OAuth avatar for {} from {}'.format(avatar_type, email, selected_user.type))
            return url
    
    # 使用默认头像
    url = static('blog/img/avatar.png')
    cache.set(cachekey, url, 60 * 60 * 24)  # 缓存24小时
    logger.info('Using default avatar for {}'.format(email))
    return url


# ZFH: 过滤器 gravatar：把头像 URL 包装成固定宽高的 <img> 标签，size 同时控制宽和高
@register.filter
def gravatar(email, size=40):
    """获得用户头像HTML标签"""
    url = gravatar_url(email, size)
    return mark_safe(
        '<img src="%s" height="%d" width="%d" class="avatar" alt="用户头像">' %
        (url, size, size))


# ZFH: simple_tag query：在模板中对 queryset 做动态过滤，等价于调用 qs.filter(**kwargs)
@register.simple_tag
def query(qs, **kwargs):
    """ template tag which allows queryset filtering. Usage:
          {% query books author=author as mybooks %}
          {% for book in mybooks %}
            ...
          {% endfor %}
    """
    return qs.filter(**kwargs)


# ZFH: 过滤器 addstr：把两个参数转成字符串后拼接，用于模板里拼接文本
@register.filter
def addstr(arg1, arg2):
    """concatenate arg1 & arg2"""
    return str(arg1) + str(arg2)


# === 插件系统模板标签 ===
# ZFH: 以下标签负责把插件系统提供的挂件、head/body 资源与静态文件注入模板

# ZFH: simple_tag render_plugin_widgets：收集指定位置上所有插件的挂件，按优先级拼接为 HTML
@register.simple_tag(takes_context=True)
def render_plugin_widgets(context, position, **kwargs):
    """
    渲染指定位置的所有插件组件
    
    Args:
        context: 模板上下文
        position: 位置标识
        **kwargs: 传递给插件的额外参数
    
    Returns:
        按优先级排序的所有插件HTML内容
    """
    from djangoblog.plugin_manage.loader import get_loaded_plugins
    
    # ZFH: 逐个插件尝试渲染，单个插件出错不影响其他挂件的输出
    widgets = []
    
    for plugin in get_loaded_plugins():
        try:
        # ZFH: 把上下文与额外参数透传给插件，由插件决定在该位置输出什么
            widget_data = plugin.render_position_widget(
                position=position,
                context=context,
                **kwargs
            )
            if widget_data:
                widgets.append(widget_data)
        except Exception as e:
            logger.error(f"Error rendering widget from plugin {plugin.PLUGIN_NAME}: {e}")
    
    # ZFH: 按 priority 升序排序，数字越小越靠前
    # 按优先级排序（数字越小优先级越高）
    widgets.sort(key=lambda x: x['priority'])
    
    # 合并HTML内容
    # ZFH: 只拼接 html 字段，最终整体标记为安全 HTML 输出
    html_parts = [widget['html'] for widget in widgets]
    return mark_safe(''.join(html_parts))


# ZFH: simple_tag plugin_critical_head_resources：输出插件中必须阻塞加载的关键 head 脚本（如防闪烁）
@register.simple_tag(takes_context=True)
def plugin_critical_head_resources(context):
    """
    渲染所有插件的关键head资源（阻塞式加载）

    用于防闪烁脚本等必须在页面渲染前执行的关键代码。
    这些资源会在<head>标签的最开始位置加载，在所有CSS之前。
    """
    from djangoblog.plugin_manage.loader import get_loaded_plugins

    # ZFH: 收集各插件的关键 HTML，异常时记录日志并跳过该插件
    resources = []

    for plugin in get_loaded_plugins():
        try:
            critical_html = plugin.get_critical_head_html(context)
            if critical_html:
                resources.append(critical_html)

        except Exception as e:
            logger.error(f"Error loading critical head resources from plugin {plugin.PLUGIN_NAME}: {e}")

    return mark_safe('\n'.join(resources))


# ZFH: simple_tag plugin_head_resources：输出插件自定义的 head HTML，CSS 文件已由压缩系统统一处理
@register.simple_tag(takes_context=True)
def plugin_head_resources(context):
    """渲染所有插件的head资源（仅自定义HTML，CSS已集成到压缩系统）"""
    from djangoblog.plugin_manage.loader import get_loaded_plugins

    # ZFH: 遍历已加载插件逐个取 head HTML，空值直接忽略
    resources = []

    for plugin in get_loaded_plugins():
        try:
            # 只处理自定义head HTML（CSS文件已通过压缩系统处理）
            head_html = plugin.get_head_html(context)
            if head_html:
                resources.append(head_html)

        except Exception as e:
            logger.error(f"Error loading head resources from plugin {plugin.PLUGIN_NAME}: {e}")

    return mark_safe('\n'.join(resources))


# ZFH: simple_tag plugin_body_resources：输出插件自定义的 body 末尾 HTML，JS 文件已由压缩系统统一处理
@register.simple_tag(takes_context=True)
def plugin_body_resources(context):
    """渲染所有插件的body资源（仅自定义HTML，JS已集成到压缩系统）"""
    from djangoblog.plugin_manage.loader import get_loaded_plugins
    
    # ZFH: 收集插件追加到 body 末尾的 HTML（如统计脚本、浮层组件）
    resources = []
    
    for plugin in get_loaded_plugins():
        try:
            # 只处理自定义body HTML（JS文件已通过压缩系统处理）
            body_html = plugin.get_body_html(context)
            if body_html:
                resources.append(body_html)
                
        except Exception as e:
            logger.error(f"Error loading body resources from plugin {plugin.PLUGIN_NAME}: {e}")
    
    return mark_safe('\n'.join(resources))


# ZFH: inclusion_tag plugin_compressed_css：汇总所有插件声明的 CSS 文件 URL，交给压缩包含模板渲染
@register.inclusion_tag('plugins/css_includes.html')
def plugin_compressed_css():
    """插件CSS压缩包含模板"""
    from djangoblog.plugin_manage.loader import get_loaded_plugins
    
    # ZFH: 把插件的相对静态路径转换为可访问 URL 后收集
    css_files = []
    for plugin in get_loaded_plugins():
        for css_file in plugin.get_css_files():
            css_url = plugin.get_static_url(css_file)
            css_files.append(css_url)
    
    return {'css_files': css_files}


# ZFH: inclusion_tag plugin_compressed_js：汇总所有插件声明的 JS 文件 URL，交给压缩包含模板渲染
@register.inclusion_tag('plugins/js_includes.html')
def plugin_compressed_js():
    """插件JS压缩包含模板"""
    from djangoblog.plugin_manage.loader import get_loaded_plugins
    
    # ZFH: 遍历插件声明的 JS 文件并解析为最终静态 URL
    js_files = []
    for plugin in get_loaded_plugins():
        for js_file in plugin.get_js_files():
            js_url = plugin.get_static_url(js_file)
            js_files.append(js_url)
    
    return {'js_files': js_files}




# ZFH: simple_tag plugin_widget：按名称渲染单个插件的指定组件模板，可在页面任意位置插入插件内容
@register.simple_tag(takes_context=True)
def plugin_widget(context, plugin_name, widget_type='default', **kwargs):
    """
    渲染指定插件的组件
    
    使用方式：
    {% plugin_widget 'article_recommendation' 'bottom' article=article count=5 %}
    """
    from djangoblog.plugin_manage.loader import get_plugin_by_slug
    
    # ZFH: 先按 slug 找到插件，再确认它实现了 render_template 能力
    plugin = get_plugin_by_slug(plugin_name)
    if plugin and hasattr(plugin, 'render_template'):
        try:
        # ZFH: 合并模板上下文与额外参数，作为插件组件的渲染上下文
            widget_context = {**context.flatten(), **kwargs}
            template_name = f"{widget_type}.html"
            return mark_safe(plugin.render_template(template_name, widget_context))
        except Exception as e:
            logger.error(f"Error rendering plugin widget {plugin_name}.{widget_type}: {e}")
    
    # ZFH: 插件不存在或渲染失败时返回空串，保证页面其余部分正常输出
    return ""