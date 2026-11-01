# ZFH: 后台管理模块（Django admin），负责将博客模型注册到 admin 站点并定制展示与操作
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

# ZFH: 注册本应用模型（Django 约定：在此处 import 模型以便 admin 自动发现）
# Register your models here.
from .models import Article, Category, Tag, Links, SideBar, BlogSettings


class ArticleForm(forms.ModelForm):
    # ZFH: 文章后台编辑表单，继承 ModelForm 自动根据模型字段生成控件
    # body = forms.CharField(widget=AdminPagedownWidget())

    class Meta:
        # ZFH: Meta 指定表单绑定的模型与字段，'__all__' 表示包含全部字段
        model = Article
        fields = '__all__'


def makr_article_publish(modeladmin, request, queryset):
    # ZFH: admin 批量操作：将选中文章的 status 更新为 'p'（已发布）
    queryset.update(status='p')


def draft_article(modeladmin, request, queryset):
    # ZFH: admin 批量操作：将选中文章的 status 更新为 'd'（草稿）
    queryset.update(status='d')


def close_article_commentstatus(modeladmin, request, queryset):
    # ZFH: admin 批量操作：关闭选中文章的评论（comment_status='c'）
    queryset.update(comment_status='c')


def open_article_commentstatus(modeladmin, request, queryset):
    # ZFH: admin 批量操作：开启选中文章的评论（comment_status='o'）
    queryset.update(comment_status='o')


# ZFH: 为批量操作设置后台下拉菜单中显示的中文/本地化描述文案
makr_article_publish.short_description = _('Publish selected articles')
draft_article.short_description = _('Draft selected articles')
close_article_commentstatus.short_description = _('Close article comments')
open_article_commentstatus.short_description = _('Open article comments')


class ArticlelAdmin(admin.ModelAdmin):
    # ZFH: 文章模型的后台管理配置类（注意类名拼写为 ArticlelAdmin）
    list_per_page = 20  # ZFH: 每页显示 20 条
    search_fields = ('body', 'title')  # ZFH: 后台搜索框可检索正文和标题
    form = ArticleForm  # ZFH: 使用上面自定义的表单
    list_display = (
        'id',
        'title',
        'author',
        'link_to_category',
        'creation_time',
        'views',
        'status',
        'type',
        'article_order')  # ZFH: 列表页展示的字段列
    list_display_links = ('id', 'title')  # ZFH: 可点击进入编辑页的字段
    list_filter = ('status', 'type', 'category')  # ZFH: 右侧过滤器字段
    date_hierarchy = 'creation_time'  # ZFH: 顶部按创建时间层级导航
    filter_horizontal = ('tags',)  # ZFH: 多选标签使用左右穿梭框
    exclude = ('creation_time', 'last_modify_time')  # ZFH: 编辑页排除自动时间字段
    view_on_site = True  # ZFH: 显示“在站点查看”按钮
    actions = [
        makr_article_publish,
        draft_article,
        close_article_commentstatus,
        open_article_commentstatus]  # ZFH: 注册批量操作动作
    raw_id_fields = ('author', 'category',)  # ZFH: 外键字段用原始ID输入，避免下拉加载全部数据

    def link_to_category(self, obj):
        # ZFH: 自定义列：生成指向分类编辑页的超链接
        info = (obj.category._meta.app_label, obj.category._meta.model_name)
        link = reverse('admin:%s_%s_change' % info, args=(obj.category.id,))
        return format_html(u'<a href="%s">%s</a>' % (link, obj.category.name))

    link_to_category.short_description = _('category')  # ZFH: 该列的表头名称

    def get_form(self, request, obj=None, **kwargs):
        # ZFH: 重写获取表单逻辑，将作者下拉限定为超级用户
        form = super(ArticlelAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['author'].queryset = get_user_model(
        ).objects.filter(is_superuser=True)
        return form

    def save_model(self, request, obj, form, change):
        # ZFH: 保存模型钩子，当前仅调用父类默认保存逻辑
        super(ArticlelAdmin, self).save_model(request, obj, form, change)

    def get_view_on_site_url(self, obj=None):
        # ZFH: 返回“在站点查看”的目标URL；有对象时用其完整URL，否则回退到当前站点域名
        if obj:
            url = obj.get_full_url()
            return url
        else:
            from djangoblog.utils import get_current_site
            site = get_current_site().domain
            return site


class TagAdmin(admin.ModelAdmin):
    # ZFH: 标签后台管理，排除自动生成/维护的字段
    exclude = ('slug', 'last_mod_time', 'creation_time')


class CategoryAdmin(admin.ModelAdmin):
    # ZFH: 分类后台管理，列表展示名称、父分类与排序
    list_display = ('name', 'parent_category', 'index')
    exclude = ('slug', 'last_mod_time', 'creation_time')


class LinksAdmin(admin.ModelAdmin):
    # ZFH: 友情链接后台管理
    exclude = ('last_mod_time', 'creation_time')


class SideBarAdmin(admin.ModelAdmin):
    # ZFH: 侧边栏配置后台管理
    list_display = ('name', 'content', 'is_enable', 'sequence')
    exclude = ('last_mod_time', 'creation_time')


class BlogSettingsAdmin(admin.ModelAdmin):
    """ZFH: 博客单例配置的后台管理 - 直接跳转到编辑页面，禁止新增/删除"""

    def has_add_permission(self, request):
        """ZFH: 权限钩子：若已存在配置则禁止再添加（保证单例）"""
        return not BlogSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """ZFH: 权限钩子：始终禁止删除配置"""
        return False

    def changelist_view(self, request, extra_context=None):
        """ZFH: 列表页视图：存在配置则重定向到编辑页，否则重定向到新增页"""
        from django.http import HttpResponseRedirect
        obj = BlogSettings.objects.first()
        if obj:
            return HttpResponseRedirect(
                reverse('admin:blog_blogsettings_change', args=[obj.pk])
            )
        # ZFH: 如果不存在配置，跳转到添加页面
        return HttpResponseRedirect(
            reverse('admin:blog_blogsettings_add')
        )

    def save_model(self, request, obj, form, change):
        """ZFH: 保存配置后清空整站缓存，确保新配置立即生效"""
        super().save_model(request, obj, form, change)
        # ZFH: 确保缓存被清除
        from djangoblog.utils import cache
        cache.clear()
        self.message_user(request, '设置已保存，缓存已清除')
