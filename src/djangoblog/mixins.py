#!/usr/bin/env python
# encoding: utf-8
# zfh: 模块说明：Django Blog 混入类，提供可复用的功能模块

"""
Django Blog 混入类 (Mixins)
提供可复用的功能模块，减少代码重复
"""

# zfh: 导入日志模块，用于记录运行时日志
import logging
# zfh: 导入 Django 模型基类，用于定义抽象模型
from django.db import models
# zfh: 导入 get_object_or_404，取不到对象时直接抛出 Http404
from django.shortcuts import get_object_or_404
# zfh: 导入 now，获取带时区的当前时间
from django.utils.timezone import now
# zfh: 导入翻译函数 _，用于字段与文案的国际化
from django.utils.translation import gettext_lazy as _

# zfh: 创建本模块的 logger 实例
logger = logging.getLogger(__name__)


# ===== 模型层 Mixin =====

# zfh: 抽象时间戳模型，为子类统一提供创建时间与修改时间字段
class TimeStampedModel(models.Model):
    """
    抽象模型：为所有模型提供统一的时间戳字段

    提供 created_at 和 updated_at 字段，自动管理时间戳
    继承此模型可以消除重复的时间字段定义

    Usage:
        class MyModel(TimeStampedModel):
            name = models.CharField(max_length=100)
    """
    # zfh: 创建时间字段，默认当前时间，并建立数据库索引
    created_at = models.DateTimeField(
        _('creation time'),
        default=now,
        db_index=True,
        help_text=_('The date and time when this object was created')
    )
    # zfh: 最后修改时间字段，默认当前时间
    updated_at = models.DateTimeField(
        _('last modify time'),
        default=now,
        help_text=_('The date and time when this object was last modified')
    )

    # zfh: 模型元数据配置
    class Meta:
        # zfh: 声明为抽象模型，不生成数据库表
        abstract = True
        # zfh: 默认按创建时间倒序排列
        ordering = ['-created_at']
        # zfh: latest() 默认按创建时间取最新记录
        get_latest_by = 'created_at'

    # zfh: 重写保存方法，保存前自动刷新修改时间
    def save(self, *args, **kwargs):
        """
        重写 save 方法，自动更新 updated_at 字段

        注意：如果使用 update_fields 参数，需要明确包含 updated_at
        """
        # 检查是否是部分更新（指定了 update_fields）
        # zfh: 取出调用方传入的 update_fields 参数
        update_fields = kwargs.get('update_fields')
        # zfh: 指定了 update_fields 说明是部分字段更新
        if update_fields:
            # 如果指定了 update_fields 但不包含 updated_at，则添加它
            # zfh: 更新字段列表中缺少 updated_at 时补上
            if 'updated_at' not in update_fields:
                # zfh: 把 updated_at 追加到更新字段列表
                update_fields = list(update_fields) + ['updated_at']
                # zfh: 把补全后的字段列表写回 kwargs
                kwargs['update_fields'] = update_fields

        # 更新时间戳
        # zfh: 把 updated_at 设为当前时间
        self.updated_at = now()

        # zfh: 调用父类的 save 完成实际保存
        super().save(*args, **kwargs)


# ===== 视图层 Mixin =====

# zfh: 视图层 Mixin：按 slug 查询对象并缓存查询结果
class SlugCachedMixin:
    """
    Mixin: 缓存 slug 查询结果，避免重复数据库查询

    在同一个请求周期内，多次获取同一个 slug 对应的对象时，
    只会执行一次数据库查询，后续调用会使用缓存的对象

    Attributes:
        slug_url_kwarg: URL 参数名，默认为 'slug'
        slug_model: 要查询的模型类

    Usage:
        class MyView(SlugCachedMixin, ListView):
            slug_url_kwarg = 'category_slug'
            slug_model = Category

            def get_queryset(self):
                category = self.get_slug_object()
                return Article.objects.filter(category=category)
    """
    # zfh: URL 中 slug 参数名，默认 'slug'
    slug_url_kwarg = 'slug'
    # zfh: 待查询的模型类，由子类指定
    slug_model = None

    # zfh: 获取并缓存 slug 对应的模型实例
    def get_slug_object(self):
        """
        获取并缓存 slug 对应的对象

        Returns:
            Model instance: slug 对应的模型实例

        Raises:
            Http404: 如果 slug 对应的对象不存在
        """
        # zfh: 实例上还没有缓存对象时才执行查询
        if not hasattr(self, '_slug_object'):
            # zfh: 子类未指定 slug_model 时无法查询
            if self.slug_model is None:
                # zfh: 抛出异常提示必须定义 slug_model
                raise ValueError(
                    f'{self.__class__.__name__} must define slug_model attribute'
                )

            # zfh: 从 URL kwargs 中取出 slug 值
            slug = self.kwargs.get(self.slug_url_kwarg)
            # zfh: 按 slug 查询对象，不存在则返回 404，并缓存到实例属性
            self._slug_object = get_object_or_404(self.slug_model, slug=slug)
            # zfh: 记录已加载对象的 debug 日志
            logger.debug(
                f'Loaded {self.slug_model.__name__} object: {self._slug_object} (slug={slug})'
            )

        # zfh: 返回缓存的对象
        return self._slug_object


# zfh: 视图层 Mixin：预加载文章关联对象，避免 N+1 查询
class OptimizedArticleQueryMixin:
    """
    Mixin: 优化文章查询（预加载关联对象）

    使用 select_related 和 prefetch_related 优化文章查询，
    减少数据库查询次数，避免 N+1 查询问题

    Usage:
        class MyView(OptimizedArticleQueryMixin, ListView):
            def get_queryset(self):
                return self.get_optimized_article_queryset().filter(status='p')
    """

    # zfh: 返回做过关联预加载优化的 Article queryset
    def get_optimized_article_queryset(self):
        """
        返回优化后的 Article queryset

        使用 select_related 预加载外键关联：
            - author: 文章作者
            - category: 文章分类

        使用 prefetch_related 预加载多对多关联：
            - tags: 文章标签

        Returns:
            QuerySet: 优化后的 Article queryset
        """
        # zfh: 延迟导入 Article 模型，避免循环导入
        from blog.models import Article

        # zfh: 用 select_related 预加载外键，用 prefetch_related 预加载多对多
        return Article.objects.select_related(
            'author',      # 预加载作者（ForeignKey）
            'category'     # 预加载分类（ForeignKey）
        ).prefetch_related(
            'tags'         # 预加载标签（ManyToMany）
        )


# zfh: 视图层 Mixin：为 ListView 提供统一的 queryset 缓存逻辑
class CachedListViewMixin:
    """
    Mixin: 为 ListView 提供统一的缓存逻辑

    自动缓存 queryset 结果，减少数据库查询
    子类需要实现 get_queryset_cache_key() 和 get_queryset_data() 方法

    Usage:
        class MyView(CachedListViewMixin, ListView):
            def get_queryset_cache_key(self):
                return f'my_list_{self.page_number}'

            def get_queryset_data(self):
                return Article.objects.filter(status='p')
    """

    # zfh: 由子类实现的缓存 key 获取方法
    def get_queryset_cache_key(self):
        """
        子类实现：返回缓存 key

        Returns:
            str: 缓存键

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        # zfh: 未实现时抛出异常，提示子类必须重写
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement get_queryset_cache_key()'
        )

    # zfh: 由子类实现的真实数据获取方法
    def get_queryset_data(self):
        """
        子类实现：返回实际数据

        Returns:
            QuerySet: 要缓存的 queryset

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        # zfh: 未实现时抛出异常，提示子类必须重写
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement get_queryset_data()'
        )

    # zfh: 按缓存 key 读取 queryset，未命中则查询并写入缓存
    def get_queryset_from_cache(self, cache_key):
        """
        从缓存获取 queryset，如果缓存不存在则查询并缓存

        Args:
            cache_key: 缓存键

        Returns:
            QuerySet: 查询结果
        """
        # zfh: 延迟导入缓存对象，避免循环导入
        from djangoblog.utils import cache

        # zfh: 从缓存读取 key 对应的值
        value = cache.get(cache_key)
        # zfh: 缓存命中时直接返回
        if value:
            # zfh: 记录缓存命中日志
            logger.info(f'Cache HIT: {cache_key}')
            # zfh: 返回缓存中的 queryset
            return value

        # zfh: 缓存未命中，调用子类方法查询数据
        queryset = self.get_queryset_data()
        # zfh: 把查询结果写入缓存
        cache.set(cache_key, queryset)
        # zfh: 记录缓存未命中日志
        logger.info(f'Cache MISS: {cache_key}')
        # zfh: 返回查询结果
        return queryset

    # zfh: 重写 get_queryset，改为从缓存获取数据
    def get_queryset(self):
        """
        重写 get_queryset，使用缓存

        Returns:
            QuerySet: 查询结果（从缓存或数据库）
        """
        # zfh: 取子类定义的缓存 key
        key = self.get_queryset_cache_key()
        # zfh: 从缓存获取 queryset 并返回
        return self.get_queryset_from_cache(key)


# zfh: 视图层 Mixin：提供当前页码的获取能力
class PageNumberMixin:
    """
    Mixin: 提供页码获取功能

    从 URL 参数或 GET 参数中获取当前页码

    Usage:
        class MyView(PageNumberMixin, ListView):
            def get_queryset_cache_key(self):
                return f'list_{self.page_number}'
    """
    # zfh: 页码参数的名称，默认 'page'
    page_kwarg = 'page'

    # zfh: 以属性形式提供当前页码
    @property
    def page_number(self):
        """
        获取当前页码

        从 URL kwargs 或 GET 参数中获取页码，默认为 1

        Returns:
            int: 当前页码
        """
        # zfh: 依次从 URL kwargs、GET 参数取页码，都取不到时用 1
        page = self.kwargs.get(self.page_kwarg) or \
               self.request.GET.get(self.page_kwarg) or 1

        # zfh: 尝试把页码转换成整数
        try:
            # zfh: 转换成功则返回整数页码
            return int(page)
        # zfh: 转换失败时回退到默认页码
        except (ValueError, TypeError):
            # zfh: 返回默认页码 1
            return 1


# zfh: 组合 Mixin：聚合文章查询优化、缓存与页码三项能力
class ArticleListMixin(
    OptimizedArticleQueryMixin,
    CachedListViewMixin,
    PageNumberMixin
):
    """
    Mixin: 组合多个 Mixin，提供完整的文章列表功能

    继承此 Mixin 的视图自动具备：
    - 优化的文章查询
    - 缓存支持
    - 页码处理

    Usage:
        class MyArticleListView(ArticleListMixin, ListView):
            def get_queryset_data(self):
                return self.get_optimized_article_queryset().filter(status='p')

            def get_queryset_cache_key(self):
                return f'my_list_{self.page_number}'
    """
    # zfh: 占位语句，全部功能由父类 Mixin 提供
    pass
