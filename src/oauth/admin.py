"""
oauth 应用的后台管理配置。

只注册两个模型，且两者的管理策略刻意不同：
- OAuthUserAdmin  ：第三方身份记录由用户登录时自动生成，后台只允许查看/搜索，禁止手工新增；
- OAuthConfigAdmin：平台配置需要管理员手工填写 AppKey 等参数，因此保留增删改。

SJQ: 模块级注释，说明本模块注册的两个后台类及其"一个只读、一个可写"的设计差异。
"""
# SJQ: logging 预留日志器，当前模块未实际打日志
import logging

# SJQ: admin 提供 ModelAdmin 基类与注册装饰方式
from django.contrib import admin
# Register your models here.
# SJQ: reverse 用于在后台列表里生成跳转到关联本地用户的链接
from django.urls import reverse
# SJQ: format_html 安全地拼接 HTML 片段（自动转义参数），避免 XSS
from django.utils.html import format_html

# SJQ: 模块级日志器
logger = logging.getLogger(__name__)


class OAuthUserAdmin(admin.ModelAdmin):
    """
    第三方用户记录的后台管理。

    这类记录是"登录时自动产生"的，管理员不应该手工新增，所以 has_add_permission 返回 False；
    同时把所有字段设为只读，避免误改 openid/token 导致绑定关系错乱。
    """

    # SJQ: 搜索框支持按昵称、邮箱检索
    search_fields = ('nickname', 'email')
    # SJQ: 每页 20 条
    list_per_page = 20
    # SJQ: 列表页展示的列
    list_display = (
        'id',
        'nickname',
        'link_to_usermodel',
        'show_user_image',
        'type',
        'email',
    )
    # SJQ: 点击 id 或昵称进入详情
    list_display_links = ('id', 'nickname')
    # SJQ: 右侧过滤器：按绑定用户、平台类型筛选
    list_filter = ('author', 'type',)
    # SJQ: 基础只读字段为空，实际只读范围在 get_readonly_fields 里动态计算
    readonly_fields = []

    def get_readonly_fields(self, request, obj=None):
        """把该对象的全部普通字段与多对多字段都设为只读。"""
        # SJQ: 动态取 obj._meta.fields，模型加字段后无需改这里
        return list(self.readonly_fields) + [
            field.name for field in obj._meta.fields
        ] + [
            field.name for field in obj._meta.many_to_many
        ]

    def has_add_permission(self, request):
        """禁止在后台手工新增第三方用户记录。"""
        # SJQ: 记录只能由登录流程产生，手工新增会绕过 openid 唯一性判断
        return False

    def link_to_usermodel(self, obj):
        """列表列：把关联的本地用户渲染成可点击链接。"""
        # SJQ: 未绑定时该列留空（返回 None）
        if obj.author:
            # SJQ: 用 app_label + model_name 反解后台修改页地址
            info = (obj.author._meta.app_label, obj.author._meta.model_name)
            link = reverse('admin:%s_%s_change' % info, args=(obj.author.id,))
            # SJQ: 优先显示昵称，没有昵称则显示邮箱
            return format_html(
                u'<a href="%s">%s</a>' %
                (link, obj.author.nickname if obj.author.nickname else obj.author.email))

    def show_user_image(self, obj):
        """列表列：把头像地址渲染成 50x50 的小图。"""
        # SJQ: 头像地址可能为空串，此时浏览器会显示破图，属既有实现的显示瑕疵
        img = obj.picture
        return format_html(
            u'<img src="%s" style="width:50px;height:50px"></img>' %
            (img))

    # SJQ: 给上面两个自定义列设置中文表头
    link_to_usermodel.short_description = '用户'
    show_user_image.short_description = '用户头像'


class OAuthConfigAdmin(admin.ModelAdmin):
    """
    第三方平台配置的后台管理。

    与 OAuthUserAdmin 相反，这里需要管理员手工维护 AppKey/AppSecret/回调地址，
    因此保留新增与修改能力。
    """

    # SJQ: 列表页展示平台类型、AppKey、AppSecret、是否启用
    list_display = ('type', 'appkey', 'appsecret', 'is_enable')
    # SJQ: 可按平台类型筛选
    list_filter = ('type',)
