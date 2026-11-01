"""
oauth 应用的数据模型模块。

本模块只定义两张表，职责分得很清楚：
- OAuthUser   ：第三方平台用户"身份"记录，一个本地用户可绑定多个平台账号；
- OAuthConfig ：第三方平台的接入配置（AppKey/AppSecret/回调地址/是否启用）。

设计要点：第三方账号与本地账号通过 OAuthUser.author 外键关联，author 允许为空，
对应"用户第一次用第三方登录、系统里还没有对应账号"的中间状态。

SJQ: 模块级注释，说明本模块提供哪些类、类之间如何配合、以及关键的可空设计。
"""
# SJQ: settings 用于取 AUTH_USER_MODEL，避免把用户模型硬编码成 accounts.BlogUser
from django.conf import settings
# SJQ: ValidationError 供 OAuthConfig.clean() 抛出应用层校验错误
from django.core.exceptions import ValidationError
# SJQ: models 提供 Model/CharField/TextField/ForeignKey 等字段类型
from django.db import models
# SJQ: now 作为 creation_time / last_modify_time 的默认值（注意不是 auto_now）
from django.utils.timezone import now
# SJQ: gettext_lazy 用于把 verbose_name 等文案标记为可翻译
from django.utils.translation import gettext_lazy as _


class OAuthUser(models.Model):
    """
    第三方平台用户记录。

    一条记录代表"某个平台上的某个账号"，用 (type, openid) 这一组合来识别；
    平台类型放在 type 字段里，因此同一张表可以混存微博/Google/GitHub 等多个平台的数据。
    """

    # SJQ: 绑定到本地用户；可空是因为第三方首次登录时本地账号可能还不存在，删除本地用户时级联删除本条记录
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('author'),
        blank=True,
        null=True,
        on_delete=models.CASCADE)
    # SJQ: 第三方平台返回的用户唯一标识（如微信 openid、GitHub 的 id）；模型未声明 unique，唯一性靠查询逻辑保证
    openid = models.CharField(max_length=50)
    # SJQ: 第三方平台昵称，最长 50；为空时视图层会兜底生成 djangoblog+时间戳的昵称
    nickname = models.CharField(max_length=50, verbose_name=_('nick name'))
    # SJQ: 访问令牌，可空；Facebook 的 token 过长，视图层会主动置空以规避长度限制
    token = models.CharField(max_length=150, null=True, blank=True)
    # SJQ: 头像地址，可空；各平台字段名不同（avatar_large/avatar_url/picture），统一存到这里
    picture = models.CharField(max_length=350, blank=True, null=True)
    # SJQ: 平台类型（weibo/google/github/facebook/qq），普通字符串字段，未用 choices 限制，因此可扩展新平台
    type = models.CharField(blank=False, null=False, max_length=50)
    # SJQ: 第三方邮箱，可空；为空时走"补全邮箱 → 邮件确认 → 绑定"流程
    email = models.CharField(max_length=50, null=True, blank=True)
    # SJQ: 第三方返回的原始报文，整段存下来便于排查字段映射问题
    metadata = models.TextField(null=True, blank=True)
    # SJQ: 记录创建时间，default=now 只在插入时取当前时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    # SJQ: 修改时间同样用 default=now，保存时不会自动刷新（与 auto_now 的语义不同）
    last_modify_time = models.DateTimeField(_('last modify time'), default=now)

    def __str__(self):
        """返回昵称作为对象的可读表示（后台列表、shell、日志中都用它）。"""
        # SJQ: 后台列表与 shell 中显示昵称，比默认的 "OAuthUser object (1)" 更易读
        return self.nickname

    class Meta:
        """模型元信息：后台显示名与默认排序。"""

        # SJQ: 后台单数显示名
        verbose_name = _('oauth user')
        # SJQ: 复数名与单数保持一致，避免后台出现 "oauth users"
        verbose_name_plural = verbose_name
        # SJQ: 默认按创建时间倒序，最新绑定的账号排在最前
        ordering = ['-creation_time']


class OAuthConfig(models.Model):
    """
    第三方登录平台配置。

    每个平台一条配置，clean() 里做了"同类型只能有一条"的应用层校验；
    管理器（oauthmanager）启动时按 type 过滤出 is_enable=True 的配置来决定显示哪些登录按钮。
    """

    # SJQ: 支持的平台枚举；choices 只是表单/后台的选项约束，不会生成数据库 CHECK 约束
    TYPE = (
        ('weibo', _('weibo')),
        ('google', _('google')),
        ('github', 'GitHub'),
        ('facebook', 'FaceBook'),
        ('qq', 'QQ'),
    )
    # SJQ: 平台类型；注意 default='a' 不在 choices 里，新建配置时必须显式选择，否则会得到非法值
    type = models.CharField(_('type'), max_length=10, choices=TYPE, default='a')
    # SJQ: 平台分配的应用标识（AppKey/ClientID）
    appkey = models.CharField(max_length=200, verbose_name='AppKey')
    # SJQ: 平台分配的应用密钥（AppSecret/ClientSecret），属于敏感信息，不能出现在日志或文档里
    appsecret = models.CharField(max_length=200, verbose_name='AppSecret')
    # SJQ: 授权回调地址，必须与平台后台登记的一致，否则换取 token 会被拒绝
    callback_url = models.CharField(
        max_length=200,
        verbose_name=_('callback url'),
        blank=False,
        default='')
    # SJQ: 是否启用该平台；get_oauth_apps() 只取启用项，关掉后前台登录按钮随即消失
    is_enable = models.BooleanField(
        _('is enable'), default=True, blank=False, null=False)
    # SJQ: 配置创建时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    # SJQ: 配置修改时间（同样是 default=now，不会自动更新）
    last_modify_time = models.DateTimeField(_('last modify time'), default=now)

    def clean(self):
        """
        应用层唯一性校验：同一平台只允许存在一条配置。

        注意这不是数据库唯一约束，只在调用 full_clean()/后台表单校验时生效，
        并发写入仍可能出现两条同类型记录。
        """
        # SJQ: 排除自身后若还能查到同 type 记录，说明重复配置，抛校验错误
        if OAuthConfig.objects.filter(
                type=self.type).exclude(id=self.id).count():
            raise ValidationError(_(self.type + _('already exists')))

    def __str__(self):
        """返回平台类型作为对象的可读表示，后台列表据此区分不同平台配置。"""
        # SJQ: 后台列表显示平台类型即可区分记录
        return self.type

    class Meta:
        """模型元信息：后台显示名与默认排序。"""

        # SJQ: 后台显示名（本项目此处直接写中文字符串，未做翻译标记）
        verbose_name = 'oauth配置'
        verbose_name_plural = verbose_name
        # SJQ: 默认按创建时间倒序
        ordering = ['-creation_time']
