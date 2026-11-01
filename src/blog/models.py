# ZFH: blog应用核心数据模型，定义文章、分类、标签、友情链接、侧边栏和站点配置
# ZFH: 标准库导入：logger 记录运行日志，re 解析 Markdown 图片，abstractmethod 声明抽象方法
import logging
import re
from abc import abstractmethod

# ZFH: Django 框架依赖：settings 取用户模型、ValidationError 抛业务校验错误、models 为 ORM 核心
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
# ZFH: reverse 用于生成前台与 admin 的相对 URL
from django.urls import reverse
# ZFH: now 作为时间字段默认值，_ 提供多语言文案包装
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
# ZFH: 第三方库：MDTextField 提供 Markdown 编辑器字段，slugify 将中文标题转成拼音 slug
from mdeditor.fields import MDTextField
from uuslug import slugify

# ZFH: 项目内部工具：缓存装饰器与缓存句柄、当前站点域名解析、缓存超时与键名常量
from djangoblog.utils import cache_decorator, cache
from djangoblog.utils import get_current_site
from djangoblog.constants import CacheTimeout, CacheKey

# ZFH: 模块级日志器，按 __name__ 命名便于在日志配置中定位 blog.models 的输出
logger = logging.getLogger(__name__)


# ZFH: 链接显示位置枚举（首页/列表页/文章页/全部/滑动）
class LinkShowType(models.TextChoices):
    # ZFH: 每项为(数据库存储值, 后台展示文案)二元组，存储值取位置英文首字母
    I = ('i', _('index'))
    L = ('l', _('list'))
    P = ('p', _('post'))
    A = ('a', _('all'))
    S = ('s', _('slide'))


# ZFH: 抽象基类，提供共享的id、创建/修改时间字段及slug自动生成逻辑
class BaseModel(models.Model):
    # ZFH: 自增主键
    id = models.AutoField(primary_key=True)
    # ZFH: 记录创建时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    # ZFH: 记录最后修改时间
    last_modify_time = models.DateTimeField(_('modify time'), default=now)

    def save(self, *args, **kwargs):
        # ZFH: 若为Article且仅更新views字段，使用SQL UPDATE避免覆盖其他字段
        is_update_views = isinstance(
            self, Article) and 'update_fields' in kwargs and kwargs['update_fields'] == ['views']
        if is_update_views:
            # ZFH: 用 QuerySet.update 只写 views 列，开销小于整行 save，也避免 slug 被重复计算
            Article.objects.filter(pk=self.pk).update(views=self.views)
        else:
            # ZFH: 对含title/name的模型自动生成拼音slug
            if 'slug' in self.__dict__:
                slug = getattr(
                    self, 'title') if 'title' in self.__dict__ else getattr(
                    self, 'name')
                setattr(self, 'slug', slugify(slug))
        # ZFH: 统一调用父类 save 完成持久化与信号触发，保留 update_fields、force_insert 等参数语义
        super().save(*args, **kwargs)

    def get_full_url(self):
        # ZFH: 返回完整URL（含域名）
        site = get_current_site().domain
        # ZFH: 借助子类实现的 get_absolute_url 拼接协议与域名，供分享链接、RSS 等绝对地址场景使用
        url = "https://{site}{path}".format(site=site,
                                            path=self.get_absolute_url())
        return url

    class Meta:
        # ZFH: 声明为抽象模型，不生成独立数据表，字段由各子类继承
        abstract = True

    @abstractmethod
    def get_absolute_url(self):
        # ZFH: 抽象方法仅定义接口，强制每个子类给出自己的详情页地址规则
        pass


# ZFH: 文章/独立页面模型，博客系统的核心内容单元
class Article(BaseModel):
    """文章"""
    # ZFH: 文章状态：d=草稿, p=已发布
    STATUS_CHOICES = (
        ('d', _('Draft')),
        ('p', _('Published')),
    )
    # ZFH: 评论状态：o=开放, c=关闭
    COMMENT_STATUS = (
        ('o', _('Open')),
        ('c', _('Close')),
    )
    # ZFH: 内容类型：a=文章, p=独立页面
    TYPE = (
        ('a', _('Article')),
        ('p', _('Page')),
    )
    # ZFH: 文章标题（唯一）
    title = models.CharField(_('title'), max_length=200, unique=True)
    # ZFH: Markdown正文，使用MDTextField支持编辑器
    body = MDTextField(_('body'))
    # ZFH: 发布时间
    pub_time = models.DateTimeField(
        _('publish time'), blank=False, null=False, default=now)
    # ZFH: 发布状态，默认已发布
    status = models.CharField(
        _('status'),
        max_length=1,
        choices=STATUS_CHOICES,
        default='p')
    # ZFH: 评论开关，默认开放
    comment_status = models.CharField(
        _('comment status'),
        max_length=1,
        choices=COMMENT_STATUS,
        default='o')
    # ZFH: 内容类型，默认文章
    type = models.CharField(_('type'), max_length=1, choices=TYPE, default='a')
    # ZFH: 浏览计数
    views = models.PositiveIntegerField(_('views'), default=0)
    # ZFH: 作者外键，关联自定义用户模型accounts.BlogUser，级联删除
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('author'),
        blank=False,
        null=False,
        on_delete=models.CASCADE)
    # ZFH: 手动排序权重，越大越靠前
    article_order = models.IntegerField(
        _('order'), blank=False, null=False, default=0)
    # ZFH: 是否显示文章目录
    show_toc = models.BooleanField(_('show toc'), blank=False, null=False, default=False)
    # ZFH: 所属分类，必须指定，级联删除
    category = models.ForeignKey(
        'Category',
        verbose_name=_('category'),
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    # ZFH: 标签，多对多关系，通过Django中间表关联
    tags = models.ManyToManyField('Tag', verbose_name=_('tag'), blank=True)

    def body_to_string(self):
        # ZFH: 返回原始Markdown文本
        return self.body

    def __str__(self):
        # ZFH: 后台列表与模板中默认以标题标识一篇文章
        return self.title

    class Meta:
        # ZFH: 默认按排序权重降序 + 发布时间降序排列
        ordering = ['-article_order', '-pub_time']
        # ZFH: 后台展示名称走国际化，单复数一致；get_latest_by 支持 latest() 按 id 取最新一篇
        verbose_name = _('article')
        verbose_name_plural = verbose_name
        get_latest_by = 'id'
        indexes = [
            # ZFH: 优化列表查询：type + status + pub_time组合索引
            models.Index(fields=['type', 'status', '-pub_time'], name='idx_type_status_pub'),
            # ZFH: 优化热门文章查询：status + views组合索引
            models.Index(fields=['status', '-views'], name='idx_status_views'),
            # ZFH: 优化作者文章查询：author + status + type组合索引
            models.Index(fields=['author', 'status', 'type'], name='idx_author_status_type'),
            # ZFH: 优化分类查询：category + status组合索引
            models.Index(fields=['category', 'status'], name='idx_category_status'),
        ]

    def get_absolute_url(self):
        # ZFH: 文章详情页URL，按年/月/日/id路由
        return reverse('blog:detailbyid', kwargs={
            'article_id': self.id,
            'year': self.creation_time.year,
            'month': self.creation_time.month,
            'day': self.creation_time.day
        })

    @cache_decorator(CacheTimeout.HOUR_10)
    def get_category_tree(self):
        # ZFH: 获取分类的父级链路（从当前分类到根分类）
        tree = self.category.get_category_tree()
        # ZFH: 把分类对象转换为(名称, 链接)二元组，方便模板直接渲染面包屑导航
        names = list(map(lambda c: (c.name, c.get_absolute_url()), tree))

        return names

    def save(self, *args, **kwargs):
        # ZFH: 当前未追加额外逻辑，显式覆写为后续扩展保存前钩子（如摘要生成）预留入口
        super().save(*args, **kwargs)

    def viewed(self):
        # ZFH: 浏览量+1，使用update_fields仅更新views字段
        self.views += 1
        self.save(update_fields=['views'])

    def comment_list(self):
        # ZFH: 获取已审核评论列表，缓存10小时
        cache_key = CacheKey.ARTICLE_COMMENTS.format(article_id=self.id)
        value = cache.get(cache_key)
        if value:
            # ZFH: 命中缓存直接返回，避免文章详情页反复查询评论表
            logger.info(f'Cache HIT: article comments (id={self.id})')
            return value
        else:
            # ZFH: 未命中时查询已审核评论，按 id 倒序让最新评论排在前面，随后回写缓存
            comments = self.comment_set.filter(is_enable=True).order_by('-id')
            cache.set(cache_key, comments, CacheTimeout.HOUR_10)
            logger.info(f'Cache MISS: article comments (id={self.id})')
            return comments

    def get_admin_url(self):
        # ZFH: 获取Django Admin编辑页URL
        info = (self._meta.app_label, self._meta.model_name)
        return reverse('admin:%s_%s_change' % info, args=(self.pk,))

    @cache_decorator(expiration=CacheTimeout.HOUR_10)
    def next_article(self):
        # ZFH: 下一篇已发布文章
        return Article.objects.filter(
            id__gt=self.id, status='p').order_by('id').first()

    @cache_decorator(expiration=CacheTimeout.HOUR_10)
    def prev_article(self):
        # ZFH: 前一篇已发布文章
        # ZFH: 以 id 小于当前文章为条件过滤已发布文章，取默认排序下的第一条作为上一篇
        return Article.objects.filter(id__lt=self.id, status='p').first()

    def get_first_image_url(self):
        """
        ZFH: 从Markdown正文中提取第一张图片URL
        """
        # ZFH: 非贪婪捕获 ![alt](url) 中的 url 部分，只关心第一处匹配
        match = re.search(r'!\[.*?\]\((.+?)\)', self.body)
        if match:
            # ZFH: 取第一个捕获组，即图片地址，用于列表页缩略图或分享封面
            return match.group(1)
        # ZFH: 正文无图片时返回空串，调用方按无封面处理
        return ""


# ZFH: 文章分类，支持无限层级树形结构
class Category(BaseModel):
    """文章分类"""
    # ZFH: 分类名称（唯一）
    name = models.CharField(_('category name'), max_length=30, unique=True)
    # ZFH: 父分类外键，自关联实现树形结构
    parent_category = models.ForeignKey(
        'self',
        verbose_name=_('parent category'),
        blank=True,
        null=True,
        on_delete=models.CASCADE)
    # ZFH: URL拼音标识
    slug = models.SlugField(default='no-slug', max_length=60, blank=True)
    # ZFH: 排序索引，越大越靠前
    index = models.IntegerField(default=0, verbose_name=_('index'))

    class Meta:
        # ZFH: 按 index 降序展示，index 越大排序越靠前
        ordering = ['-index']
        verbose_name = _('category')
        verbose_name_plural = verbose_name

    def get_absolute_url(self):
        # ZFH: 分类详情页URL，使用slug路由
        return reverse(
            'blog:category_detail', kwargs={
                'category_name': self.slug})

    def __str__(self):
        # ZFH: 后台与模板中默认显示分类名称
        return self.name

    @cache_decorator(CacheTimeout.HOUR_10)
    def get_category_tree(self):
        """
        ZFH: 递归获取从当前分类到根分类的完整父链
        """
        categorys = []

        def parse(category):
            # ZFH: 递归内部函数：先记录当前分类，再沿 parent_category 向上查找
            categorys.append(category)
            if category.parent_category:
                # ZFH: 存在父分类时继续上溯，直到根分类 parent_category 为空
                parse(category.parent_category)

        # ZFH: 从当前分类自身开始构建父级链路
        parse(self)
        return categorys

    @cache_decorator(CacheTimeout.HOUR_10)
    def get_sub_categorys(self):
        """
        ZFH: 递归获取当前分类及其所有子分类
        """
        categorys = []
        # ZFH: 一次性取出全部分类并复用，避免递归过程中每层都访问数据库
        all_categorys = Category.objects.all()

        def parse(category):
            # ZFH: 递归内部函数：把分类加入结果集并继续遍历其直接子分类
            if category not in categorys:
                # ZFH: 去重判断，防止同一分类被多次收集导致重复展示
                categorys.append(category)
            childs = all_categorys.filter(parent_category=category)
            for child in childs:
                # ZFH: 逐个处理子分类，再递归下探形成完整子树
                if category not in categorys:
                    categorys.append(child)
                parse(child)

        # ZFH: 从当前分类自身开始向下遍历子树
        parse(self)
        return categorys


# ZFH: 文章标签模型
class Tag(BaseModel):
    """文章标签"""
    # ZFH: 标签名称（唯一）
    name = models.CharField(_('tag name'), max_length=30, unique=True)
    # ZFH: URL拼音标识
    slug = models.SlugField(default='no-slug', max_length=60, blank=True)

    def __str__(self):
        # ZFH: 后台与模板中默认显示标签名称
        return self.name

    def get_absolute_url(self):
        # ZFH: 标签详情页URL
        return reverse('blog:tag_detail', kwargs={'tag_name': self.slug})

    @cache_decorator(CacheTimeout.HOUR_10)
    def get_article_count(self):
        # ZFH: 获取含该标签的文章数（去重）
        return Article.objects.filter(tags__name=self.name).distinct().count()

    class Meta:
        # ZFH: 按名称字母序排列标签，便于后台管理
        ordering = ['name']
        verbose_name = _('tag')
        verbose_name_plural = verbose_name


# ZFH: 友情链接模型
class Links(models.Model):
    """友情链接"""
    # ZFH: 链接名称（唯一）
    name = models.CharField(_('link name'), max_length=30, unique=True)
    # ZFH: 链接地址
    link = models.URLField(_('link'))
    # ZFH: 排序序号（唯一）
    sequence = models.IntegerField(_('order'), unique=True)
    # ZFH: 是否在前台显示
    is_enable = models.BooleanField(
        _('is show'), default=True, blank=False, null=False)
    # ZFH: 显示位置（首页/列表/文章/全部/滑动）
    show_type = models.CharField(
        _('show type'),
        max_length=1,
        choices=LinkShowType.choices,
        default=LinkShowType.I)
    # ZFH: 创建时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    # ZFH: 修改时间
    last_mod_time = models.DateTimeField(_('modify time'), default=now)

    class Meta:
        # ZFH: 按 sequence 升序排列，序号小的友情链接排在前面
        ordering = ['sequence']
        verbose_name = _('link')
        verbose_name_plural = verbose_name

    def __str__(self):
        # ZFH: 后台列表中显示链接名称
        return self.name


# ZFH: 侧边栏自定义组件，支持Markdown/HTML内容
class SideBar(models.Model):
    """侧边栏,可以展示一些html内容"""
    # ZFH: 组件标题
    name = models.CharField(_('title'), max_length=100)
    # ZFH: 组件内容（Markdown格式，渲染时经Markdown处理）
    content = models.TextField(_('content'))
    # ZFH: 排序序号（唯一）
    sequence = models.IntegerField(_('order'), unique=True)
    # ZFH: 是否启用
    is_enable = models.BooleanField(_('is enable'), default=True)
    # ZFH: 创建时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    # ZFH: 修改时间
    last_mod_time = models.DateTimeField(_('modify time'), default=now)

    class Meta:
        # ZFH: 按 sequence 升序排列，决定侧边栏组件的上下顺序
        ordering = ['sequence']
        verbose_name = _('sidebar')
        verbose_name_plural = verbose_name

    def __str__(self):
        # ZFH: 后台列表中显示侧边栏组件标题
        return self.name


# ZFH: 全站配置单例模型，全库仅允许一条记录
class BlogSettings(models.Model):
    """blog的配置"""
    # ZFH: 8种配色方案
    COLOR_SCHEMES = (
        ('purple', _('紫色主题 - Purple Dream')),
        ('blue', _('蓝色主题 - Ocean Blue')),
        ('green', _('绿色主题 - Forest Green')),
        ('orange', _('橙色主题 - Sunset Orange')),
        ('pink', _('粉色主题 - Cherry Blossom')),
        ('red', _('红色主题 - Ruby Red')),
        ('indigo', _('靛蓝主题 - Midnight Indigo')),
        ('teal', _('青色主题 - Teal Wave')),
    )

    # ZFH: 站点名称
    site_name = models.CharField(
        _('site name'),
        max_length=200,
        null=False,
        blank=False,
        default='')
    # ZFH: 站点描述
    site_description = models.TextField(
        _('site description'),
        max_length=1000,
        null=False,
        blank=False,
        default='')
    # ZFH: SEO描述
    site_seo_description = models.TextField(
        _('site seo description'), max_length=1000, null=False, blank=False, default='')
    # ZFH: SEO关键词
    site_keywords = models.TextField(
        _('site keywords'),
        max_length=1000,
        null=False,
        blank=False,
        default='')
    # ZFH: 文章摘要长度
    article_sub_length = models.IntegerField(_('article sub length'), default=300)
    # ZFH: 侧边栏文章数量
    sidebar_article_count = models.IntegerField(_('sidebar article count'), default=10)
    # ZFH: 侧边栏评论数量
    sidebar_comment_count = models.IntegerField(_('sidebar comment count'), default=5)
    # ZFH: 文章页评论数量
    article_comment_count = models.IntegerField(_('article comment count'), default=5)
    # ZFH: 是否显示AdSense广告
    show_google_adsense = models.BooleanField(_('show adsense'), default=False)
    # ZFH: AdSense广告代码
    google_adsense_codes = models.TextField(
        _('adsense code'), max_length=2000, null=True, blank=True, default='')
    # ZFH: 是否开放全站评论
    open_site_comment = models.BooleanField(_('open site comment'), default=True)
    # ZFH: 配色方案，默认紫色主题
    color_scheme = models.CharField(
        _('配色方案'),
        max_length=20,
        choices=COLOR_SCHEMES,
        default='purple',
        help_text=_('选择网站的主题配色方案'))
    # ZFH: 公共头部HTML注入
    global_header = models.TextField("公共头部", null=True, blank=True, default='')
    # ZFH: 公共尾部HTML注入
    global_footer = models.TextField("公共尾部", null=True, blank=True, default='')
    # ZFH: ICP备案号
    beian_code = models.CharField(
        '备案号',
        max_length=2000,
        null=True,
        blank=True,
        default='')
    # ZFH: 网站统计代码
    analytics_code = models.TextField(
        "网站统计代码",
        max_length=1000,
        null=False,
        blank=False,
        default='')
    # ZFH: 是否显示公安备案号
    show_gongan_code = models.BooleanField(
        '是否显示公安备案号', default=False, null=False)
    # ZFH: 公安备案号
    gongan_beiancode = models.TextField(
        '公安备案号',
        max_length=2000,
        null=True,
        blank=True,
        default='')
    # ZFH: 评论是否需要审核
    comment_need_review = models.BooleanField(
        '评论是否需要审核', default=False, null=False)

    class Meta:
        # ZFH: 后台单例配置的展示名称，单复数保持一致
        verbose_name = _('Website configuration')
        verbose_name_plural = verbose_name

    def __str__(self):
        # ZFH: 用站点名称代表这条配置记录
        return self.site_name

    def clean(self):
        # ZFH: 单例校验，全库只允许一条配置记录
        if BlogSettings.objects.exclude(id=self.id).count():
            # ZFH: exclude 自身后再计数，保证编辑已有记录不会误判为新增第二条
            raise ValidationError(_('There can only be one configuration'))

    def save(self, *args, **kwargs):
        # ZFH: 先完成常规保存，确保配置数据已落库
        super().save(*args, **kwargs)
        # ZFH: 配置变更后清空全站缓存
        # ZFH: 局部导入避免模块加载阶段出现循环依赖
        from djangoblog.utils import cache
        # ZFH: 配置影响导航、侧边栏等多处页面，粗暴清空缓存以保证立即生效
        cache.clear()
