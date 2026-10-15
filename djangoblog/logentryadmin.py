# zfh: 导入 Django 后台管理模块
from django.contrib import admin
# zfh: 导入删除操作的动作标记常量 DELETION
from django.contrib.admin.models import DELETION
# zfh: 导入内容类型模型 ContentType
from django.contrib.contenttypes.models import ContentType
# zfh: 导入 reverse 反查 URL，并导入反查失败的异常 NoReverseMatch
from django.urls import reverse, NoReverseMatch
# zfh: 导入 force_str，把对象安全转换为字符串
from django.utils.encoding import force_str
# zfh: 导入 escape，对 HTML 特殊字符转义
from django.utils.html import escape
# zfh: 导入 mark_safe，把字符串标记为可安全渲染的 HTML
from django.utils.safestring import mark_safe
# zfh: 导入 gettext_lazy，用于列表表头文字的延迟翻译
from django.utils.translation import gettext_lazy as _


# zfh: 后台操作日志条目管理类，只读展示日志
class LogEntryAdmin(admin.ModelAdmin):
    # zfh: 右侧过滤器，按内容类型筛选日志
    list_filter = [
        'content_type'
    ]

    # zfh: 搜索字段，支持对象描述和变更说明
    search_fields = [
        'object_repr',
        'change_message'
    ]

    # zfh: 列表中可点击进入详情页的字段
    list_display_links = [
        'action_time',
        'get_change_message',
    ]
    # zfh: 列表页展示的字段
    list_display = [
        'action_time',
        'user_link',
        'content_type',
        'object_link',
        'get_change_message',
    ]

    # zfh: 判断是否允许在后台新增日志条目
    def has_add_permission(self, request):
        # zfh: 始终返回 False，日志由系统自动记录
        return False

    # zfh: 判断是否允许修改日志条目
    def has_change_permission(self, request, obj=None):
        # zfh: 超级用户或有 change_logentry 权限且请求方式非 POST 时允许
        return (
                request.user.is_superuser or
                request.user.has_perm('admin.change_logentry')
        ) and request.method != 'POST'

    # zfh: 判断是否允许删除日志条目
    def has_delete_permission(self, request, obj=None):
        # zfh: 始终返回 False，日志条目不可删除
        return False

    # zfh: 把被操作对象渲染为后台编辑页链接
    def object_link(self, obj):
        # zfh: 转义对象描述文本，避免 HTML 注入
        object_link = escape(obj.object_repr)
        # zfh: 取出该日志对应的内容类型对象
        content_type = obj.content_type

        # zfh: 非删除操作且内容类型存在时，尝试生成可点击链接
        if obj.action_flag != DELETION and content_type is not None:
            # try returning an actual link instead of object repr string
            # zfh: 尝试反查该对象在后台的编辑页地址
            try:
                # zfh: 按应用标签与模型名反查后台 change 页面 URL
                url = reverse(
                    'admin:{}_{}_change'.format(content_type.app_label,
                                                content_type.model),
                    args=[obj.object_id]
                )
                # zfh: 拼装成带链接的 HTML 片段
                object_link = '<a href="{}">{}</a>'.format(url, object_link)
            # zfh: 反查失败时忽略异常，保持纯文本展示
            except NoReverseMatch:
                # zfh: 空实现，不做处理
                pass
        # zfh: 标记为安全 HTML 后返回
        return mark_safe(object_link)

    # zfh: 指定该列在后台的排序依据字段
    object_link.admin_order_field = 'object_repr'
    # zfh: 该列在列表表头显示的名称
    object_link.short_description = _('object')

    # zfh: 把日志所属用户渲染为后台用户编辑页链接
    def user_link(self, obj):
        # zfh: 获取该用户类型对应的内容类型对象
        content_type = ContentType.objects.get_for_model(type(obj.user))
        # zfh: 把用户对象转成字符串并转义
        user_link = escape(force_str(obj.user))
        # zfh: 尝试反查该用户在后台的编辑页地址
        try:
            # try returning an actual link instead of object repr string
            # zfh: 按应用标签与模型名反查后台 change 页面 URL
            url = reverse(
                'admin:{}_{}_change'.format(content_type.app_label,
                                            content_type.model),
                args=[obj.user.pk]
            )
            # zfh: 拼装成带链接的 HTML 片段
            user_link = '<a href="{}">{}</a>'.format(url, user_link)
        # zfh: 反查失败时忽略异常，保持纯文本展示
        except NoReverseMatch:
            # zfh: 空实现，不做处理
            pass
        # zfh: 标记为安全 HTML 后返回
        return mark_safe(user_link)

    # zfh: 指定该列在后台的排序依据字段
    user_link.admin_order_field = 'user'
    # zfh: 该列在列表表头显示的名称
    user_link.short_description = _('user')

    # zfh: 重写查询集方法，优化日志列表的关联查询
    def get_queryset(self, request):
        # zfh: 调用父类方法获取基础查询集
        queryset = super(LogEntryAdmin, self).get_queryset(request)
        # zfh: 预取内容类型关联，减少查询次数
        return queryset.prefetch_related('content_type')

    # zfh: 重写可用批量操作，去掉内置的删除选中项操作
    def get_actions(self, request):
        # zfh: 调用父类方法获取全部批量操作
        actions = super(LogEntryAdmin, self).get_actions(request)
        # zfh: 如果存在删除选中项操作
        if 'delete_selected' in actions:
            # zfh: 从操作字典中移除该项
            del actions['delete_selected']
        # zfh: 返回处理后的批量操作字典
        return actions
