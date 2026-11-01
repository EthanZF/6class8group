# ZFH: 博客视图模块：集中实现前台文章列表/详情、分类/标签/作者归档、搜索、文件上传与缓存清理等视图
import logging
import os
import uuid

# ZFH: 导入 Django 配置、分页、HTTP 响应、快捷函数、静态资源、时区与国际化等核心依赖
from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
# ZFH: 引入 Haystack 提供的搜索视图基类，用于实现全文搜索页面
from haystack.views import SearchView

# ZFH: 导入本项目模型、评论表单、插件钩子、通用工具函数等业务依赖
from blog.models import Article, Category, LinkShowType, Links, Tag
from comments.forms import CommentForm
from djangoblog.plugin_manage import hooks
from djangoblog.plugin_manage.hook_constants import ARTICLE_CONTENT_HOOK_NAME
from djangoblog.utils import cache, get_blog_setting, get_sha256
# ZFH: 导入列表视图 Mixin，复用 slug 缓存、文章查询优化、列表缓存与分页逻辑
from djangoblog.mixins import (
    SlugCachedMixin,
    ArticleListMixin,
    OptimizedArticleQueryMixin,
    CachedListViewMixin,
    PageNumberMixin
)

# ZFH: 获取当前模块的日志记录器，用于输出调试与运行日志
logger = logging.getLogger(__name__)


# ZFH: 文章列表视图基类，继承缓存、分页、通用列表三个 Mixin，统一封装列表页的查询、缓存与上下文逻辑
class ArticleListView(CachedListViewMixin, PageNumberMixin, ListView):
    """
    文章列表视图基类（重构版）

    使用 Mixin 简化代码，消除重复逻辑
    子类只需实现 get_queryset_data() 和 get_queryset_cache_key() 方法
    """
    # template_name属性用于指定使用哪个模板进行渲染
    template_name = 'blog/article_index.html'

    # context_object_name属性用于给上下文变量取名（在模板中使用该名字）
    context_object_name = 'article_list'

    # 页面类型，分类目录或标签列表等
    page_type = ''
    # ZFH: 每页文章数取自全局配置，决定列表分页大小
    paginate_by = settings.PAGINATE_BY
    # ZFH: 分页参数名，URL 中以 ?page=N 的形式指定页码
    page_kwarg = 'page'
    # ZFH: 默认友情链接展示类型，子类可按页面场景覆盖
    link_type = LinkShowType.L

    # ZFH: 返回列表视图的缓存键，用于命中/写入列表页缓存
    def get_view_cache_key(self):
        # ZFH: 从查询参数 pages 中读取缓存标识，沿用项目既有的缓存键约定
        return self.request.get['pages']

    # ZFH: 向模板上下文注入友情链接展示类型 linktype，再交由父类补充分页等上下文
    def get_context_data(self, **kwargs):
        # ZFH: 将 linktype 放入上下文，模板据此筛选不同类型的友情链接
        kwargs['linktype'] = self.link_type
        return super(ArticleListView, self).get_context_data(**kwargs)


# ZFH: 博客首页视图，复用优化后的文章查询并展示首页文章列表
class IndexView(OptimizedArticleQueryMixin, ArticleListView):
    """
    首页视图（重构版）

    继承 OptimizedArticleQueryMixin 获得优化的查询方法
    """
    # 友情链接类型
    # ZFH: 首页使用首页专用友情链接类型，与列表页的链接区分
    link_type = LinkShowType.I

    # ZFH: 首页文章数据源：经优化查询后仅保留文章类型(type='a')且已发布(status='p')的记录
    def get_queryset_data(self):
        # 使用 Mixin 提供的优化查询方法
        return self.get_optimized_article_queryset().filter(
            type='a', status='p'
        )

    # ZFH: 首页列表缓存键，按页码区分不同分页的缓存
    def get_queryset_cache_key(self):
        return f'index_{self.page_number}'

    # ZFH: 在父类上下文基础上补充站点级 SEO 标题、描述与关键词
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ZFH: 读取站点配置，用于拼接首页标题、描述与关键词
        blog_setting = get_blog_setting()
        # 提供基础SEO数据
        context['seo_title'] = f"{blog_setting.site_name} | {blog_setting.site_description}"
        context['seo_description'] = blog_setting.site_seo_description
        context['seo_keywords'] = blog_setting.site_keywords
        return context


# ZFH: 文章详情视图，按 article_id 查询单篇文章并渲染详情模板，同时装配评论、分页与 SEO 数据
class ArticleDetailView(DetailView):
    '''
    文章详情页面
    '''
    template_name = 'blog/article_detail.html'
    # ZFH: 绑定文章模型，并通过 article_id 作为 URL 主键参数查询单篇文章
    model = Article
    pk_url_kwarg = 'article_id'
    # ZFH: 模板中使用的文章对象变量名
    context_object_name = "article"

    # ZFH: 详情页上下文装配：构建评论表单、父评论分页、评论总数、上下篇导航及 SEO 数据
    def get_context_data(self, **kwargs):
        # ZFH: 实例化空评论表单，供模板渲染评论提交区域
        comment_form = CommentForm()

        # 优化：直接查询父评论，减少数据库查询
        # ZFH: 延迟导入评论模型，避免视图模块加载时的循环导入
        from comments.models import Comment
        # ZFH: 仅查询当前文章的一级(父)评论，并预加载作者与子评论以降低查询次数
        parent_comments = Comment.objects.filter(
            article=self.object,
            parent_comment=None,
            is_enable=True
        ).select_related('author').prefetch_related(
            'comment_set__author'  # 预加载子评论及其作者
        ).order_by('-id')

        # 获取所有评论用于总数显示
        # ZFH: 取文章全部评论，用于展示评论总数
        article_comments = self.object.comment_list()

        # ZFH: 按站点配置的评论数对父评论分页，并修正越界/非法页码
        blog_setting = get_blog_setting()
        # ZFH: 以配置的每页评论数构造 Paginator
        paginator = Paginator(parent_comments, blog_setting.article_comment_count)
        # ZFH: 从查询参数读取评论页码，默认为第 1 页
        page = self.request.GET.get('comment_page', '1')
        # ZFH: 校验页码合法性：非数字回退到 1，小于 1 或超过总页数时做边界修正
        if not page.isnumeric():
            page = 1
        else:
            page = int(page)
            if page < 1:
                page = 1
            if page > paginator.num_pages:
                page = paginator.num_pages

        # ZFH: 取当前页评论并计算上一页/下一页页码，用于生成分页链接
        p_comments = paginator.page(page)
        next_page = p_comments.next_page_number() if p_comments.has_next() else None
        prev_page = p_comments.previous_page_number() if p_comments.has_previous() else None

        # ZFH: 将上下页评论链接写入上下文，锚点指向评论列表容器
        if next_page:
            kwargs[
                'comment_next_page_url'] = self.object.get_absolute_url() + f'?comment_page={next_page}#commentlist-container'
        if prev_page:
            kwargs[
                'comment_prev_page_url'] = self.object.get_absolute_url() + f'?comment_page={prev_page}#commentlist-container'
        # ZFH: 将评论表单、全部评论、分页评论对象及评论总数写入上下文
        kwargs['form'] = comment_form
        kwargs['article_comments'] = article_comments
        kwargs['p_comments'] = p_comments
        kwargs['comment_count'] = len(
            article_comments) if article_comments else 0

        # ZFH: 注入上一篇/下一篇文章对象，供模板展示相邻文章导航
        kwargs['next_article'] = self.object.next_article
        kwargs['prev_article'] = self.object.prev_article

        # ZFH: 调用父类获取基础上下文后，继续追加文章级 SEO 与插件钩子数据
        context = super(ArticleDetailView, self).get_context_data(**kwargs)
        # ZFH: 取出当前文章对象，供后续 SEO 与钩子逻辑使用
        article = self.object
        
        # 添加基础SEO数据
        blog_setting = get_blog_setting()
        # ZFH: 延迟导入文本处理工具与 Markdown 渲染器，仅详情页 SEO 需要
        from django.utils.html import strip_tags
        from django.utils.text import Truncator
        from djangoblog.utils import CommonMarkdown
        
        # 处理description：markdown -> HTML -> 纯文本，彻底去除格式
        # ZFH: 先把 Markdown 正文渲染成 HTML，便于后续提取纯文本摘要
        html_content = CommonMarkdown.get_markdown(article.body)
        # ZFH: 剥离 HTML 标签，得到不含标记的正文文本
        description = strip_tags(html_content)
        description = ' '.join(description.split())  # 规范化空白字符
        # ZFH: 将摘要截断为 150 个字符，超出部分以省略号结尾
        description = Truncator(description).chars(150, truncate='...')
        
        # 处理keywords：去除空格，用逗号分隔
        # ZFH: 收集并规范化文章标签名，作为页面关键词来源
        tags = [tag.name.strip() for tag in article.tags.all()]
        # ZFH: 有标签时用逗号拼接，无标签时回退到站点默认关键词
        keywords = ", ".join(tags) if tags else blog_setting.site_keywords
        
        # ZFH: 将文章标题、正文摘要与标签关键词写入 SEO 上下文
        context['seo_title'] = f"{article.title} | {blog_setting.site_name}"
        context['seo_description'] = description
        context['seo_keywords'] = keywords

        # 触发文章详情加载钩子，让插件可以添加额外的上下文数据
        from djangoblog.plugin_manage.hook_constants import ARTICLE_DETAIL_LOAD
        # ZFH: 触发 ARTICLE_DETAIL_LOAD 钩子，允许插件向详情页上下文追加数据
        hooks.run_action(ARTICLE_DETAIL_LOAD, article=article, context=context, request=self.request)

        # Action Hook, 通知插件"文章详情已获取"
        # ZFH: 触发 after_article_body_get 钩子，通知插件文章正文已获取
        hooks.run_action('after_article_body_get', article=article, request=self.request)
        return context


# ZFH: 分类目录列表视图，按分类 slug 展示该分类(含子分类)下的已发布文章
class CategoryDetailView(SlugCachedMixin, OptimizedArticleQueryMixin, ArticleListView):
    """
    分类目录列表（重构版）

    使用 SlugCachedMixin 避免重复查询 Category
    使用 OptimizedArticleQueryMixin 优化文章查询
    """
    page_type = "分类目录归档"
    # ZFH: URL 中分类标识的参数名，与路由 category/<slug:category_name> 对应
    slug_url_kwarg = 'category_name'
    # ZFH: 指定 slug 对应的模型，供 SlugCachedMixin 查询并缓存分类对象
    slug_model = Category

    # ZFH: 分类文章数据源：取该分类及其子分类名称集合，过滤出已发布文章
    def get_queryset_data(self):
        # 使用 Mixin 缓存的对象，只查询一次
        category = self.get_slug_object()
        categorynames = [c.name for c in category.get_sub_categorys()]

        return self.get_optimized_article_queryset().filter(
            category__name__in=categorynames, status='p'
        )

    # ZFH: 分类列表缓存键，按分类名与页码区分缓存
    def get_queryset_cache_key(self):
        # 复用缓存的对象，不再重复查询数据库
        category = self.get_slug_object()
        return f'category_list_{category.name}_{self.page_number}'

    # ZFH: 分类页上下文：设置页面类型、标签名，并补充分类 SEO 信息
    def get_context_data(self, **kwargs):
        category = self.get_slug_object()
        categoryname = category.name

        # ZFH: 分类名可能带层级路径，尝试取最后一段作为展示名称
        try:
            categoryname = categoryname.split('/')[-1]
        # ZFH: 名称格式异常时静默忽略，仍使用完整分类名展示
        except BaseException:
            pass

        # ZFH: 向上下文写入页面类型与分类名，供模板标题和面包屑使用
        kwargs['page_type'] = CategoryDetailView.page_type
        kwargs['tag_name'] = categoryname
        
        # 添加基础SEO数据
        blog_setting = get_blog_setting()
        # ZFH: 统计当前分类下的文章数量，用于生成 SEO 描述
        article_count = self.get_queryset().count()
        kwargs['seo_title'] = f"{categoryname} | {blog_setting.site_name}"
        kwargs['seo_description'] = f"浏览 {categoryname} 分类下的所有文章，共 {article_count} 篇文章。"
        kwargs['seo_keywords'] = f"{categoryname}, {blog_setting.site_keywords}"
        
        return super(CategoryDetailView, self).get_context_data(**kwargs)


# ZFH: 作者文章归档视图，按作者用户名展示其已发布文章列表
class AuthorDetailView(OptimizedArticleQueryMixin, ArticleListView):
    """
    作者详情页（重构版）

    使用 OptimizedArticleQueryMixin 优化文章查询
    """
    page_type = '作者文章归档'

    # ZFH: 作者列表缓存键，对作者名做 slug 处理后按页码区分缓存
    def get_queryset_cache_key(self):
        # ZFH: 延迟导入 slugify，对包含非 ASCII 字符的作者名做统一转换
        from uuslug import slugify
        author_name = slugify(self.kwargs['author_name'])
        return f'author_{author_name}_{self.page_number}'

    # ZFH: 作者文章数据源：过滤出该作者的文章类型(type='a')且已发布(status='p')的记录
    def get_queryset_data(self):
        # ZFH: 从 URL 参数中取作者用户名
        author_name = self.kwargs['author_name']
        return self.get_optimized_article_queryset().filter(
            author__username=author_name, type='a', status='p'
        )

    # ZFH: 作者页上下文：设置页面类型、作者名，并补充作者 SEO 信息
    def get_context_data(self, **kwargs):
        author_name = self.kwargs['author_name']
        # ZFH: 写入页面类型与作者名，供模板显示归档标题
        kwargs['page_type'] = AuthorDetailView.page_type
        kwargs['tag_name'] = author_name
        
        # 添加基础SEO数据
        blog_setting = get_blog_setting()
        # ZFH: 统计该作者已发布文章数量，用于生成 SEO 描述
        article_count = self.get_queryset().count()
        kwargs['seo_title'] = f"{author_name} 的文章 | {blog_setting.site_name}"
        kwargs['seo_description'] = f"浏览 {author_name} 发表的所有文章，共 {article_count} 篇。"
        kwargs['seo_keywords'] = f"{author_name}, {blog_setting.site_keywords}"
        
        return super(AuthorDetailView, self).get_context_data(**kwargs)


# ZFH: 标签文章列表视图，按标签 slug 展示含该标签的已发布文章
class TagDetailView(SlugCachedMixin, OptimizedArticleQueryMixin, ArticleListView):
    """
    标签列表页面（重构版）

    使用 SlugCachedMixin 避免重复查询 Tag
    使用 OptimizedArticleQueryMixin 优化文章查询
    """
    page_type = '分类标签归档'
    # ZFH: URL 中标签标识的参数名，与路由 tag/<slug:tag_name> 对应
    slug_url_kwarg = 'tag_name'
    # ZFH: 指定 slug 对应的模型，供 SlugCachedMixin 查询并缓存标签对象
    slug_model = Tag

    # ZFH: 标签文章数据源：过滤出含该标签且为文章类型、已发布的记录
    def get_queryset_data(self):
        # 使用 Mixin 缓存的对象，只查询一次
        tag = self.get_slug_object()
        return self.get_optimized_article_queryset().filter(
            tags__name=tag.name, type='a', status='p'
        )

    # ZFH: 标签列表缓存键，按标签名与页码区分缓存
    def get_queryset_cache_key(self):
        # 复用缓存的对象，不再重复查询数据库
        tag = self.get_slug_object()
        return f'tag_{tag.name}_{self.page_number}'

    # ZFH: 标签页上下文：设置页面类型、标签名，并补充标签 SEO 信息
    def get_context_data(self, **kwargs):
        tag = self.get_slug_object()
        # ZFH: 写入页面类型与标签名，供模板显示归档标题
        kwargs['page_type'] = TagDetailView.page_type
        kwargs['tag_name'] = tag.name
        
        # 添加基础SEO数据
        blog_setting = get_blog_setting()
        # ZFH: 统计该标签下的文章数量，用于生成 SEO 描述
        article_count = self.get_queryset().count()
        kwargs['seo_title'] = f"{tag.name} | {blog_setting.site_name}"
        kwargs['seo_description'] = f"浏览所有关于 {tag.name} 的文章，共 {article_count} 篇内容。"
        kwargs['seo_keywords'] = f"{tag.name}, {blog_setting.site_keywords}"
        
        return super(TagDetailView, self).get_context_data(**kwargs)


# ZFH: 文章归档视图，不分页地列出全部已发布文章
class ArchivesView(OptimizedArticleQueryMixin, ArticleListView):
    """
    文章归档页面（重构版）

    使用 OptimizedArticleQueryMixin 优化文章查询
    """
    page_type = '文章归档'
    # ZFH: 归档页需要一次性展示全部文章，因此关闭分页
    paginate_by = None
    # ZFH: 同时关闭页码参数解析，避免沿列表视图的分页逻辑
    page_kwarg = None
    template_name = 'blog/article_archives.html'

    # ZFH: 归档数据源：经优化查询后仅保留已发布(status='p')的文章
    def get_queryset_data(self):
        return self.get_optimized_article_queryset().filter(status='p')

    # ZFH: 归档页缓存键，全站归档共用同一缓存
    def get_queryset_cache_key(self):
        return 'archives'


# ZFH: 友情链接列表视图，展示所有启用状态的链接
class LinkListView(ListView):
    # ZFH: 绑定友情链接模型并指定渲染模板
    model = Links
    template_name = 'blog/links_list.html'

    # ZFH: 仅查询启用(is_enable=True)的友情链接
    def get_queryset(self):
        # ZFH: 通过 is_enable 过滤，屏蔽后台已停用的链接
        return Links.objects.filter(is_enable=True)


# ZFH: 基于 Haystack 的搜索视图，支持搜索结果高亮
class EsSearchView(SearchView):
    # ZFH: 重写表单构建，为搜索查询集开启高亮(highlight)能力
    def build_form(self, form_kwargs=None):
        """Override to enable highlighting"""
        # ZFH: 未传入表单参数时初始化为空字典，避免后续写入报错
        if form_kwargs is None:
            form_kwargs = {}

        # Enable highlighting for search results
        # ZFH: 延迟导入查询集类，仅在构建搜索表单时加载
        from haystack.query import SearchQuerySet
        # ZFH: 未指定搜索集时新建默认集，否则沿用调用方提供的搜索集
        if self.searchqueryset is None:
            sqs = SearchQuerySet().highlight()
        # ZFH: 对既有搜索集开启高亮，使结果中的命中词可被标记
        else:
            sqs = self.searchqueryset.highlight()

        # ZFH: 将配置好的搜索集写回表单参数并交给父类构建表单
        form_kwargs['searchqueryset'] = sqs
        return super().build_form(form_kwargs=form_kwargs)

    # ZFH: 组装搜索结果上下文：查询词、表单、分页对象，并附带拼写建议
    def get_context(self):
        # ZFH: 根据搜索结果构建分页器与当前页对象
        paginator, page = self.build_page()
        # ZFH: 组装搜索页上下文：查询词、表单、分页信息与拼写建议占位
        context = {
            "query": self.query,
            "form": self.form,
            "page": page,
            "paginator": paginator,
            "suggestion": None,
        }
        # ZFH: 后端支持拼写检查时，补充 “您是不是要找” 建议
        if hasattr(self.results, "query") and self.results.query.backend.include_spelling:
            context["suggestion"] = self.results.query.get_spelling_suggestion()
        # ZFH: 合并子类或视图配置的额外上下文
        context.update(self.extra_context())

        return context


# ZFH: 图片/文件上传视图，仅提供图床功能，需调用方自行实现上传端
@csrf_exempt
def fileupload(request):
    """
    该方法需自己写调用端来上传图片，该方法仅提供图床功能
    :param request:
    :return:
    """
    # ZFH: 仅接受 POST 请求，其余方法直接拒绝
    if request.method == 'POST':
        # ZFH: 从查询参数读取签名，未提供签名时拒绝上传
        sign = request.GET.get('sign', None)
        if not sign:
            return HttpResponseForbidden()
        # ZFH: 校验签名是否为 SECRET_KEY 双重 SHA256 的结果，防止接口被任意调用
        if not sign == get_sha256(get_sha256(settings.SECRET_KEY)):
            return HttpResponseForbidden()
        # ZFH: 收集本次上传文件的访问 URL，最终一并返回
        response = []
        # ZFH: 遍历所有上传文件，逐个保存到静态目录
        for filename in request.FILES:
            # ZFH: 按年月日生成子目录，便于文件归档与查找
            timestr = timezone.now().strftime('%Y/%m/%d')
            imgextensions = ['jpg', 'png', 'jpeg', 'bmp']
            fname = u''.join(str(filename))
            # ZFH: 根据扩展名判断是否为图片，决定存入 image 还是 files 目录
            isimage = len([i for i in imgextensions if fname.find(i) >= 0]) > 0
            base_dir = os.path.join(settings.STATICFILES, "files" if not isimage else "image", timestr)
            # ZFH: 目标目录不存在时递归创建
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            # ZFH: 用 UUID 重命名文件以避免重名，并保留原始扩展名
            savepath = os.path.normpath(os.path.join(base_dir, f"{uuid.uuid4().hex}{os.path.splitext(filename)[-1]}"))
            # ZFH: 校验最终路径仍位于目标目录内，防止路径穿越写入任意位置
            if not savepath.startswith(base_dir):
                return HttpResponse("only for post")
            # ZFH: 分块写入上传内容，避免大文件一次性占用内存
            with open(savepath, 'wb+') as wfile:
                for chunk in request.FILES[filename].chunks():
                    wfile.write(chunk)
            # ZFH: 图片文件再做一次压缩，降低体积并启用优化
            if isimage:
                from PIL import Image
                image = Image.open(savepath)
                image.save(savepath, quality=20, optimize=True)
            # ZFH: 将静态文件路径转换为可访问 URL 并加入返回列表
            url = static(savepath)
            response.append(url)
        # ZFH: 返回所有上传文件的 URL 列表
        return HttpResponse(response)

    else:
        # ZFH: 非 POST 请求返回提示文本
        return HttpResponse("only for post")


# ===== 错误处理视图 =====
# 注意：这些函数保留是为了向后兼容
# 实际实现已经移动到 djangoblog.error_views
# 可以在 urls.py 中直接引用新的实现

# ZFH: 从 error_views 引入 404/500/403 错误处理视图，保持向后兼容
from djangoblog.error_views import (
    page_not_found_view,
    server_error_view,
    permission_denied_view
)


# ZFH: 清空缓存视图，调用后返回 'ok'，用于手动清理站点缓存
def clean_cache_view(request):
    # ZFH: 清空全局缓存
    cache.clear()
    return HttpResponse('ok')
