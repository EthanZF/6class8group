#psj: 【模块】comments.models —— 评论应用的数据模型层
#psj: 本模块只做一件事：把"评论"和"评论上的表情表态"这两类数据定义成数据库表。
#psj: 里面的两个类都是 Django 的 Model，Django 会按字段自动生成建表语句，
#psj: 业务逻辑不写在这里（查询和组装放到 views.py，校验放到 forms.py）。
#psj: 两张表分别是：
#psj:   Comment         —— 评论，一条评论挂在一篇文章下，由某个用户发出，
#psj:                      通过 parent_comment 指向自己来支持"回复某条评论"（楼中楼）；
#psj:   CommentReaction —— 对某条评论的单个表情表态，一条记录 = 一个人对一个表情的一次点击。
#psj: 与其它应用的关联：article 外键指向 blog.models.Article，
#psj: author / user 外键指向 settings.AUTH_USER_MODEL（即 accounts.models.BlogUser）。
from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

#psj: 导入文章模型是为了给 Comment.article 建外键；跨应用引用模型时直接 import 类即可。
from blog.models import Article


# Create your models here.

#psj: Comment 对应数据库表 comments_comment，是评论应用的主表。
#psj: 一条记录就是文章下面显示的一句话，楼中楼靠 parent_comment 自关联串起来。
class Comment(models.Model):
    #psj: 评论正文。用 TextField 而不是 CharField，因为正文可能较长；
    #psj: max_length=300 不是数据库长度限制，而是给表单校验用的上限。
    body = models.TextField('正文', max_length=300)
    #psj: 创建时间。default=now 表示由 Python 侧在新建时取当前时间，
    #psj: 这样迁移和测试里可以手动指定时间。
    creation_time = models.DateTimeField(_('creation time'), default=now)
    #psj: 最后修改时间，同样是 Python 侧给默认值。
    last_modify_time = models.DateTimeField(_('last modify time'), default=now)
    #psj: 评论作者外键，指向系统用户表。
    #psj: 这里用 settings.AUTH_USER_MODEL 而不是直接写 BlogUser，
    #psj: 是为了以后换用户模型时这一行不用改。
    #psj: on_delete=CASCADE 表示用户被删除时，他发的评论一并删除。
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('author'),
        on_delete=models.CASCADE)
    #psj: 评论所属的文章外键，指向 blog 应用的 Article。
    #psj: 同样是级联删除：文章被删掉，文章下面的评论也就没有意义了。
    article = models.ForeignKey(
        Article,
        verbose_name=_('article'),
        on_delete=models.CASCADE)
    #psj: 父评论外键，指向自己这张表（'self'），这就是楼中楼的实现方式。
    #psj: 顶层评论的 parent_comment 为空，所以 blank=True、null=True；
    #psj: 回复别人的评论时，这个字段指向被回复的那一条。
    parent_comment = models.ForeignKey(
        'self',
        verbose_name=_('parent comment'),
        blank=True,
        null=True,
        on_delete=models.CASCADE)
    #psj: 是否启用（是否在前台显示）。
    #psj: 注意默认值是 False，也就是说新评论默认不显示，
    #psj: 需要在视图里根据站点配置显式置为 True（见 views.py 的 form_valid）。
    is_enable = models.BooleanField(_('enable'),
                                    default=False, blank=False, null=False)

    #psj: Meta 是给 Django 看的表级配置，不生成字段。
    class Meta:
        #psj: 默认按 id 倒序，列表里最新的评论排在最前面。
        ordering = ['-id']
        #psj: 后台和表单里显示的表名。
        verbose_name = _('comment')
        verbose_name_plural = verbose_name
        #psj: get_latest_by 指定 latest() 按哪个字段取"最新一条"。
        get_latest_by = 'id'
        #psj: 这里建了两条组合索引，目的是让评论列表和侧边栏这两个高频查询走索引，
        #psj: 避免全表扫描。
        indexes = [
            # 优化评论列表查询：article + parent_comment + is_enable组合索引
            #psj: 第一条对应"取某篇文章下的顶层、已启用评论"，
            #psj: 字段顺序与查询条件一致，符合最左前缀原则。
            models.Index(fields=['article', 'parent_comment', 'is_enable'], name='idx_art_parent_enable'),
            # 优化侧边栏评论查询：is_enable + id组合索引
            #psj: 第二条对应"取最新显示的若干条评论"，is_enable 过滤后按 id 倒序取前几条。
            models.Index(fields=['is_enable', '-id'], name='idx_enable_id'),
        ]

    #psj: 后台或 shell 里打印评论对象时显示正文，方便辨认。
    def __str__(self):
        return self.body

    #psj: 【方法】汇总这条评论上各种表情的统计结果，供前端渲染表情条使用。
    #psj: 参数 user 是当前登录用户，未登录时传 None；
    #psj: 之所以要传进来，是因为除了总数还要告诉前端"当前这个人有没有点过这个表情"，
    #psj: 前端据此决定表情是否高亮。
    #psj: 返回值是一个字典，键是表情本身（如 👍），值包含 count、has_reacted、users 三项。
    def get_reactions_summary(self, user=None):
        """
        获取评论的 reactions 统计信息
        返回格式: {
            '👍': {
                'count': 5,
                'has_reacted': True,
                'users': ['Alice', 'Bob', 'Charlie']
            },
            '❤️': {'count': 3, 'has_reacted': False, 'users': [...]},
            ...
        }
        """
        #psj: Count 是 Django 的聚合函数，放在函数内部导入可以少一次模块加载时的依赖。
        from django.db.models import Count

        #psj: 第一步：按表情类型分组统计数量。
        #psj: values('reaction_type') 指定分组字段，annotate(count=Count('id'))
        #psj: 给每个分组算一个 count，等价于 SQL 里的 GROUP BY reaction_type。
        reactions = CommentReaction.objects.filter(
            comment=self
        ).values('reaction_type').annotate(count=Count('id'))

        #psj: result 用来存放最终要返回的字典。
        result = {}
        for reaction in reactions:
            emoji = reaction['reaction_type']

            # 获取该 emoji 的所有点赞用户
            #psj: 第二步：取这个表情下具体是哪些用户点的。
            #psj: select_related('user') 会用一次 JOIN 把用户一起查出来，
            #psj: 避免在循环里逐条再查用户表（N+1 查询问题）；
            #psj: [:10] 是切片，最多只取 10 个，防止参与人数太多把页面撑开。
            reaction_users = CommentReaction.objects.filter(
                comment=self,
                reaction_type=emoji
            ).select_related('user')[:10]  # 最多显示10个用户

            #psj: 显示名优先用昵称，昵称为空时退回用户名。
            user_names = [r.user.nickname or r.user.username for r in reaction_users]

            #psj: 先按"当前用户没点过"填进去，下面再按实际情况改。
            result[emoji] = {
                'count': reaction['count'],
                'has_reacted': False,
                'users': user_names
            }

            #psj: 第三步：只有传入了登录用户，才去判断他是否点过这个表情。
            #psj: is_authenticated 用来排除匿名用户，避免对 AnonymousUser 查库。
            if user and user.is_authenticated:
                result[emoji]['has_reacted'] = CommentReaction.objects.filter(
                    comment=self,
                    user=user,
                    reaction_type=emoji
                ).exists()

        #psj: 返回汇总结果，结构见上面的文档字符串。
        return result


#psj: CommentReaction 对应数据库表 comments_commentreaction，
#psj: 一条记录表示"某个用户对某条评论点了某个表情"。
#psj: 把它单独建一张表，而不是在 Comment 上存一个计数字段，
#psj: 好处是能知道具体是谁点的，也方便做"再次点击取消"。
class CommentReaction(models.Model):
    """
    评论的 Emoji 反应/点赞
    """
    #psj: 允许的 8 种表情。左边是存进数据库的值（表情字符本身），
    #psj: 右边是可读名称，后台下拉框里显示用。
    REACTION_CHOICES = [
        ('👍', 'thumbs_up'),
        ('👎', 'thumbs_down'),
        ('❤️', 'heart'),
        ('😄', 'laugh'),
        ('🎉', 'hooray'),
        ('😕', 'confused'),
        ('🚀', 'rocket'),
        ('👀', 'eyes'),
    ]

    #psj: 表态针对哪条评论。related_name='reactions' 让反向查询更顺手：
    #psj: 拿到一个 comment 对象后可以直接用 comment.reactions.all() 取它的所有表态。
    comment = models.ForeignKey(
        Comment,
        verbose_name=_('comment'),
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    #psj: 谁点的这个表情。
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('user'),
        on_delete=models.CASCADE
    )
    #psj: 表情类型，用 choices 把取值限制在上面的 8 种以内，
    #psj: 后台会渲染成下拉框，从输入环节就避免写错。
    reaction_type = models.CharField(
        _('reaction type'),
        max_length=10,
        choices=REACTION_CHOICES
    )
    #psj: 表态时间。auto_now_add=True 表示新增时由 Django 自动写入，
    #psj: 之后不会变，也不需要手填。
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    #psj: Meta 同样是表级配置。这里的重点不是显示名，而是下面那条联合唯一约束，
    #psj: 它决定了"一个人对同一条评论的同一个表情只能有一条记录"。
    class Meta:
        verbose_name = _('comment reaction')
        verbose_name_plural = _('comment reactions')
        # 每个用户对同一评论的同一种 emoji 只能点一次
        #psj: 这条唯一约束放在数据库层，比只在视图里判断更可靠：
        #psj: 就算有人从后台或脚本直接写数据，也不会出现同一个人重复点同一个表情。
        #psj: 视图里的"再次点击 = 取消"就是靠 get_or_create 命中这条约束实现的。
        unique_together = ['comment', 'user', 'reaction_type']
        #psj: 索引：按"评论 + 表情类型"查询时走索引，
        #psj: 正好对应 get_reactions_summary 里按表情分组的统计。
        indexes = [
            models.Index(fields=['comment', 'reaction_type'], name='idx_comment_reaction'),
        ]

    #psj: 后台显示成"用户名 - 表情 on comment 编号"，便于辨认是哪一条记录。
    def __str__(self):
        return f'{self.user.username} - {self.reaction_type} on comment {self.comment.id}'
