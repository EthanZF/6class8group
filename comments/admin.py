#psj: 【模块】comments.admin —— 评论应用的后台管理配置
#psj: 本模块把 Comment 和 CommentReaction 两张表注册到 Django 后台（/admin/），
#psj: 并定制它们在后台的显示列、筛选条件和批量操作。
#psj: 后台页面全部由框架按这里的配置自动生成，不用写前端代码。
#psj: 主要内容：
#psj:   两个批量操作函数 —— 把选中的评论统一设为显示或不显示（相当于批量审核）；
#psj:   CommentAdmin         —— 评论列表显示正文、作者、所属文章等，作者和文章做成可点击链接；
#psj:   CommentReactionAdmin —— 表情记录列表，方便查某条评论被谁点了什么表情。
from django.contrib import admin
#psj: reverse 用来根据后台路由名反查出某个对象的编辑页地址，做跳转链接用。
from django.urls import reverse
#psj: format_html 拼 HTML 片段时会做转义，避免用户输入的内容造成 XSS。
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Comment, CommentReaction


#psj: 【函数】批量操作：把选中的评论设为不显示。
#psj: 后台列表页勾选多条后从下拉框选这个操作即可执行，
#psj: 参数 queryset 就是被勾选的那些评论。
def disable_commentstatus(modeladmin, request, queryset):
    #psj: 用 update 直接发一条 SQL 批量改，比逐条 save 快得多。
    queryset.update(is_enable=False)


#psj: 【函数】批量操作：把选中的评论设为显示，即审核通过。
def enable_commentstatus(modeladmin, request, queryset):
    #psj: 同样是批量更新。
    queryset.update(is_enable=True)


#psj: short_description 决定这两个操作在后台下拉框里显示成什么文字。
disable_commentstatus.short_description = _('Disable comments')
enable_commentstatus.short_description = _('Enable comments')


#psj: 【类】评论模型的后台配置。
class CommentAdmin(admin.ModelAdmin):
    #psj: 列表页每页显示 20 条。
    list_per_page = 20
    #psj: 列表页显示哪些列。其中 link_to_userinfo、link_to_article 不是模型字段，
    #psj: 而是下面自己写的方法，用来把外键显示成可点击的链接。
    list_display = (
        'id',
        'body',
        'link_to_userinfo',
        'link_to_article',
        'is_enable',
        'creation_time')
    #psj: 点哪几列可以进详情页编辑。
    list_display_links = ('id', 'body', 'is_enable')
    #psj: 右侧筛选栏，这里只按"是否显示"筛，方便找出待审核的评论。
    list_filter = ('is_enable',)
    #psj: 编辑页排除这两个自动维护的时间字段，不让手填。
    exclude = ('creation_time', 'last_modify_time')
    #psj: 挂上上面定义的两个批量操作。
    actions = [disable_commentstatus, enable_commentstatus]
    #psj: 作者和文章改用"放大镜"搜索选择，避免数据量大时一次性加载全部下拉项。
    raw_id_fields = ('author', 'article')
    #psj: 搜索框在正文里找关键词。
    search_fields = ('body',)

    #psj: 【方法】把作者显示成一个链接，点进去是该用户的后台编辑页。
    def link_to_userinfo(self, obj):
        #psj: 取出用户模型所在的应用名和模型名，拼成后台路由名。
        info = (obj.author._meta.app_label, obj.author._meta.model_name)
        link = reverse('admin:%s_%s_change' % info, args=(obj.author.id,))
        #psj: 显示名优先用昵称，没有昵称就用邮箱。
        return format_html(
            u'<a href="%s">%s</a>' %
            (link, obj.author.nickname if obj.author.nickname else obj.author.email))

    #psj: 【方法】把所属文章显示成一个链接，点进去是该文章的后台编辑页。
    def link_to_article(self, obj):
        info = (obj.article._meta.app_label, obj.article._meta.model_name)
        link = reverse('admin:%s_%s_change' % info, args=(obj.article.id,))
        #psj: 链接文字用文章标题。
        return format_html(
            u'<a href="%s">%s</a>' % (link, obj.article.title))

    #psj: 这两列在列表表头的显示名称。
    link_to_userinfo.short_description = _('User')
    link_to_article.short_description = _('Article')


#psj: 【类】评论表情记录的后台配置。
#psj: 这张表数据量大且以查看为主，所以列表按表情类型和时间做筛选。
class CommentReactionAdmin(admin.ModelAdmin):
    #psj: 列表显示：编号、表情、评论链接、用户链接、时间。
    list_display = ('id', 'reaction_type', 'link_to_comment', 'link_to_user', 'created_at')
    list_display_links = ('id', 'reaction_type')
    #psj: 可以按表情类型和日期筛选，便于看某种表情的使用情况。
    list_filter = ('reaction_type', 'created_at')
    raw_id_fields = ('comment', 'user')
    #psj: 搜索框支持按评论正文和用户名搜，__ 表示跨关联表查询。
    search_fields = ('comment__body', 'user__username')
    #psj: 顶部按天导航，方便按日期翻。
    date_hierarchy = 'created_at'

    #psj: 【方法】把评论显示成"Comment #编号"的链接。
    def link_to_comment(self, obj):
        info = (obj.comment._meta.app_label, obj.comment._meta.model_name)
        link = reverse('admin:%s_%s_change' % info, args=(obj.comment.id,))
        return format_html(
            u'<a href="%s">Comment #%s</a>' % (link, obj.comment.id))

    #psj: 【方法】把用户显示成链接，显示名优先昵称，其次用户名。
    def link_to_user(self, obj):
        info = (obj.user._meta.app_label, obj.user._meta.model_name)
        link = reverse('admin:%s_%s_change' % info, args=(obj.user.id,))
        return format_html(
            u'<a href="%s">%s</a>' %
            (link, obj.user.nickname if obj.user.nickname else obj.user.username))

    link_to_comment.short_description = _('Comment')
    link_to_user.short_description = _('User')


#psj: 把两个模型注册到后台，并指定上面写好的配置类。
#psj: 这一行执行之后，后台左侧菜单里才会出现"评论"和"评论表情"两项。
admin.site.register(Comment, CommentAdmin)
admin.site.register(CommentReaction, CommentReactionAdmin)
