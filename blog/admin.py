"""blog 应用的后台管理配置。

【文件作用】
    Django 自带一个后台管理界面（访问 /admin/）。只要在 admin.py 里"注册"模型，
    框架就会自动生成该模型的增删改查页面 —— 不用写任何前端代码。
    本文件负责：
      1. 把 blog 应用的 6 个模型注册到后台；
      2. 定制每个模型在后台的显示列、筛选条件、可执行操作等。
"""
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

# Register your models here.
# PSJ 导入本应用的模型。后台配置要针对具体模型来写，所以必须先引入。
from .models import Article, Category, Tag, Links, SideBar, BlogSettings


class ArticleForm(forms.ModelForm):
    """文章的表单（后台新增/编辑文章时使用）。

    ModelForm 会依据模型的字段自动生成表单控件；
    fields = '__all__' 表示"把模型上所有字段都放进来"。
    """
    # body = forms.CharField(widget=AdminPagedownWidget())

    class Meta:
        model = Article
        fields = '__all__'


# PSJ ---------------------------------------------------------------------------
# PSJ 下面 4 个函数是"批量操作"（action）：
# PSJ 在文章列表页勾选多篇文章后，可以从上方下拉框选中它们并执行。
# PSJ 它们都接收 (modeladmin, request, queryset) 三个参数，
# PSJ 其中 queryset 就是"被勾选的那些文章"。
# PSJ ---------------------------------------------------------------------------

def makr_article_publish(modeladmin, request, queryset):
    """把选中的文章批量改为"发表"状态。

    status 取值：'p' = 发表（前台可见），'d' = 草稿（前台看不到）。
    update() 是批量更新（batch update），只发一条 SQL，比逐条 save() 快得多。
    """
    queryset.update(status='p')


def draft_article(modeladmin, request, queryset):
    """把选中的文章批量改为"草稿"（draft）状态。"""
    queryset.update(status='d')


def close_article_commentstatus(modeladmin, request, queryset):
    """批量关闭选中文章的评论（前台不能再评论）。comment_status: 'c' = 关闭。"""
    queryset.update(comment_status='c')


def open_article_commentstatus(modeladmin, request, queryset):
    """批量打开选中文章的评论。comment_status: 'o' = 打开。"""
    queryset.update(comment_status='o')


# PSJ short_description 决定这个操作在后台下拉框里显示成什么文字。
makr_article_publish.short_description = _('Publish selected articles')
draft_article.short_description = _('Draft selected articles')
close_article_commentstatus.short_description = _('Close article comments')
open_article_commentstatus.short_description = _('Open article comments')


class ArticlelAdmin(admin.ModelAdmin):
    """文章模型的后台配置。

    类名 ArticlelAdmin 里的 "l" 是原作者的拼写笔误（本应是 ArticleAdmin），
    但项目里已经引用这个名字，改名要同步改 admin_site.py，所以保留原样。
    """
    # PSJ 列表页每页显示 20 条
    list_per_page = 20
    # PSJ 搜索时在哪些字段里找关键词（这里按正文和标题搜索）
    search_fields = ('body', 'title')
    # PSJ 指定使用的表单（即上面定义的 ArticleForm）
    form = ArticleForm
    # PSJ 列表页显示哪些列
    list_display = (
        'id',
        'title',
        'author',
        'link_to_category',   # PSJ 这个不是模型字段，是下面自定义的方法
        'creation_time',
        'views',
        'status',
        'type',
        'article_order')
    # PSJ 点击哪几列可以进详情页（这里 id 和标题可点）
    list_display_links = ('id', 'title')
    # PSJ 右侧筛选栏（filter）：可按状态、类型、分类筛选
    list_filter = ('status', 'type', 'category')
    # PSJ 顶部按创建时间做的"日期层级"导航
    date_hierarchy = 'creation_time'
    # PSJ 多对多字段（many-to-many，标签）用左右穿梭框选择，比多选框好用
    filter_horizontal = ('tags',)
    # PSJ 编辑页排除这两个自动维护的时间字段（不让手填）
    exclude = ('creation_time', 'last_modify_time')
    # PSJ 编辑页显示"在站点上查看"按钮
    view_on_site = True
    # PSJ 挂上前面定义的四个批量操作
    actions = [
        makr_article_publish,
        draft_article,
        close_article_commentstatus,
        open_article_commentstatus]
    # PSJ 作者和分类改用"放大镜"搜索选择（数据量大时避免一次性加载全部选项）
    raw_id_fields = ('author', 'category',)

    def link_to_category(self, obj):
        """在文章列表里把"分类"显示成一个可点击的链接。

        这里用 reverse() 反查出后台里该分类的编辑页地址，
        format_html() 负责安全地拼出 <a> 标签（避免 XSS 注入）。
        """
        # PSJ 取出分类模型所在的应用名和模型名，拼成后台路由名
        info = (obj.category._meta.app_label, obj.category._meta.model_name)
        link = reverse('admin:%s_%s_change' % info, args=(obj.category.id,))
        return format_html(u'<a href="%s">%s</a>' % (link, obj.category.name))

    # PSJ 该列在列表表头的显示名称（复用模型字段的中文名"分类"）
    link_to_category.short_description = _('category')

    def get_form(self, request, obj=None, **kwargs):
        """定制表单：把"作者"下拉框的可选项限制为超级用户。

        因为本站是个人博客，只允许超级用户（superuser）作为文章作者。
        """
        form = super(ArticlelAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['author'].queryset = get_user_model(
        ).objects.filter(is_superuser=True)
        return form

    def save_model(self, request, obj, form, change):
        """保存文章。这里只调用父类实现，未做额外处理。

        change 参数表示"是新增(False)还是修改(True)"。
        """
        super(ArticlelAdmin, self).save_model(request, obj, form, change)

    def get_view_on_site_url(self, obj=None):
        """决定"在站点上查看"按钮跳到哪里。

        已有文章 -> 跳到该文章的前台地址；
        新增文章时 -> 跳到站点域名。
        """
        if obj:
            # PSJ obj.get_full_url() 是 Article 模型上的方法，返回带域名的完整地址
            url = obj.get_full_url()
            return url
        else:
            # PSJ 新增时还没有具体文章，返回站点域名
            from djangoblog.utils import get_current_site
            site = get_current_site().domain
            return site


class TagAdmin(admin.ModelAdmin):
    """标签的后台配置。

    exclude 排除 slug 和两个时间字段：
      - slug（URL 里的地址片段）由模型 save() 时自动生成，不需要手填；
      - 时间字段由程序维护。
    """
    exclude = ('slug', 'last_mod_time', 'creation_time')


class CategoryAdmin(admin.ModelAdmin):
    """分类的后台配置。

    列表页显示：分类名、父级分类、序号。
    （parent_category 让分类支持父子级；slug 同样自动生成。）
    """
    # PSJ 列表页显示：名称、父级分类、序号
    list_display = ('name', 'parent_category', 'index')
    exclude = ('slug', 'last_mod_time', 'creation_time')


class LinksAdmin(admin.ModelAdmin):
    """友情链接的后台配置。只排除两个自动维护的时间字段。"""
    exclude = ('last_mod_time', 'creation_time')


class SideBarAdmin(admin.ModelAdmin):
    """侧边栏的后台配置。

    列表页显示名称、内容、是否启用、排序序号。
    """
    # PSJ 列表页显示：名称、内容、是否启用、排序序号
    list_display = ('name', 'content', 'is_enable', 'sequence')
    exclude = ('last_mod_time', 'creation_time')


class BlogSettingsAdmin(admin.ModelAdmin):
    """站点配置的后台配置。

    这是一个"单例模型"（singleton）：全站只允许存在一条配置记录。
    下面三个方法配合起来，让后台表现为"点进去直接编辑那一条"。
    """

    def has_add_permission(self, request):
        """如果已经存在配置，就禁止再新增（从入口上保证单例）。"""
        return not BlogSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """禁止删除配置，避免误删导致站点信息丢失。"""
        return False

    def changelist_view(self, request, extra_context=None):
        """列表页不做列表，直接跳转到编辑页。

        因为只有一条记录，展示列表没有意义。
        """
        from django.http import HttpResponseRedirect
        # PSJ 取出唯一那条配置
        obj = BlogSettings.objects.first()
        if obj:
            # PSJ 已有配置 -> 跳到它的编辑页
            return HttpResponseRedirect(
                reverse('admin:blog_blogsettings_change', args=[obj.pk])
            )
        # PSJ 如果不存在配置，跳转到添加页面
        return HttpResponseRedirect(
            reverse('admin:blog_blogsettings_add')
        )

    def save_model(self, request, obj, form, change):
        """保存设置时清除缓存（cache）。

        因为站点配置在很多地方被缓存（例如 seo_processor、
        get_blog_setting），改完必须清缓存，前台才会立刻生效。
        """
        super().save_model(request, obj, form, change)
        # PSJ 确保缓存被清除
        from djangoblog.utils import cache
        cache.clear()
        # PSJ 在后台页面顶部给管理员一个提示
        self.message_user(request, '设置已保存，缓存已清除')
