"""
oauth 应用的视图模块。

本模块实现第三方登录的完整闭环，共 5 个入口：
- oauthlogin       ：点击第三方登录按钮，跳到平台授权页；
- authorize        ：平台回调，用 code 换 token、取用户信息、绑定或创建本地账号并登录；
- emailconfirm     ：邮件确认链接的落地页，校验签名后完成绑定并登录；
- RequireEmailView ：第三方未返回邮箱时，要求用户补全邮箱并发确认邮件；
- bindsuccess      ：绑定结果提示页。

三条容易忽略的业务规则：
1. 回调后的跳转目标必须经过 url_has_allowed_host_and_scheme 校验，防止开放重定向；
2. 邮箱确认链接的 sign 由 get_sha256() 生成，实际算法是 HMAC-SHA256
   （以 SECRET_KEY 为密钥、对 "SECRET_KEY+id+SECRET_KEY" 求摘要），签名不符直接 403；
3. 第三方返回的昵称为空时要兜底生成，否则本地用户名会为空字符串。

SJQ: 模块级注释，说明本模块的 5 个入口、调用顺序与三条安全/健壮性规则。
"""
# SJQ: logging 记录非法跳转地址、token 换取失败等异常情况
import logging
# Create your views here.
# SJQ: urlparse 已导入但当前未被使用（flake8 会报 F401），属于可清理的历史残留
from urllib.parse import urlparse

# SJQ: settings 用于取 SECRET_KEY、SESSION_COOKIE_AGE、DEBUG 等配置
from django.conf import settings
# SJQ: get_user_model 取当前项目的用户模型（accounts.BlogUser），避免硬编码
from django.contrib.auth import get_user_model
# SJQ: login 把通过第三方校验的用户写入 session，完成登录态建立
from django.contrib.auth import login
# SJQ: ObjectDoesNotExist 用于区分"查不到"与其他数据库异常
from django.core.exceptions import ObjectDoesNotExist
# SJQ: transaction.atomic 保证"建用户 + 绑定 oauth 记录"要么都成功要么都回滚
from django.db import transaction
# SJQ: HttpResponseForbidden 用于签名校验失败时返回 403
from django.http import HttpResponseForbidden
# SJQ: HttpResponseRedirect 用于所有 302 跳转
from django.http import HttpResponseRedirect
# SJQ: get_object_or_404 简化"按主键取不到就 404"的写法
from django.shortcuts import get_object_or_404
# SJQ: render 渲染绑定结果提示页
from django.shortcuts import render
# SJQ: reverse 按路由名反解 URL，避免把路径写死
from django.urls import reverse
# SJQ: timezone 生成兜底昵称时的时间戳
from django.utils import timezone
# SJQ: gettext_lazy 标记提示邮件正文为可翻译文本
from django.utils.translation import gettext_lazy as _
# SJQ: FormView 是补全邮箱页使用的通用表单视图基类
from django.views.generic import FormView
# SJQ: url_has_allowed_host_and_scheme 校验跳转地址是否属于本站，防开放重定向
from django.utils.http import url_has_allowed_host_and_scheme

# SJQ: 登录成功后触发的信号，供其他应用（如记录登录日志）挂接
from djangoblog.blog_signals import oauth_user_login_signal
# SJQ: get_current_site 取当前站点域名，用于拼确认邮件里的绝对地址
from djangoblog.utils import get_current_site
# SJQ: send_email 发确认邮件；get_sha256 生成/校验确认链接签名
from djangoblog.utils import send_email, get_sha256
# SJQ: 补全邮箱表单，只含 email 与隐藏的 oauthid
from oauth.forms import RequireEmailForm
# SJQ: 第三方用户模型
from .models import OAuthUser
# SJQ: 管理器工厂与换取 token 失败时抛出的异常
from .oauthmanager import get_manager_by_type, OAuthAccessTokenException

# SJQ: 模块级日志器
logger = logging.getLogger(__name__)


def get_redirecturl(request):
    """
    从请求参数 next_url 中取出安全的跳转地址。

    安全策略：只允许站内相对路径或本站域名下的地址，其余一律回退到首页。
    这样可以避免攻击者构造 next_url=https://evil.com 把用户带到钓鱼站。
    """
    # SJQ: next_url 是登录前所在页面，登录后要回到这里
    nexturl = request.GET.get('next_url', None)
    # SJQ: 没有传、或指向登录页本身时，直接回首页，避免登录后原地打转
    if not nexturl or nexturl == '/login/' or nexturl == '/login':
        return '/'

    # Only allow relative URLs or URLs pointing to the current host
    # SJQ: 取本站域名作为白名单
    site_domain = get_current_site().domain
    # SJQ: 相对地址或本站地址放行；require_https 跟随当前请求是否走 HTTPS
    if url_has_allowed_host_and_scheme(
        url=nexturl,
        allowed_hosts={site_domain},
        require_https=request.is_secure()
    ):
        return nexturl

    # SJQ: 非法地址记日志后回首页，不向用户暴露具体判定原因
    logger.info('非法url:' + str(nexturl))
    return '/'


def oauthlogin(request):
    """
    第三方登录入口：拼出平台授权页并重定向过去。

    对应路由 /oauth/oauthlogin?type=weibo&next_url=...，
    前台登录页的第三方按钮就是链接到这里的。
    """
    # SJQ: type 决定用哪个平台管理器，缺失即视为非法入口
    type = request.GET.get('type', None)
    if not type:
        return HttpResponseRedirect('/')
    # SJQ: 按类型取管理器；未配置的平台会拿到 None
    manager = get_manager_by_type(type)
    if not manager:
        return HttpResponseRedirect('/')
    # SJQ: 计算登录后要跳回的位置
    nexturl = get_redirecturl(request)
    # SJQ: 交给管理器拼授权地址，然后 302 到平台
    authorizeurl = manager.get_authorization_url(nexturl)
    return HttpResponseRedirect(authorizeurl)


def authorize(request):
    """
    第三方平台回调处理（核心流程，复杂度最高的一个函数）。

    处理顺序：
    1. 校验 type、取管理器；
    2. 用 code 换 token，失败则重新发起授权；
    3. 取平台用户信息，昵称为空时兜底；
    4. 用 (type, openid) 查已有记录，查到就更新头像/昵称/原始报文；
    5. 有邮箱：事务内找或建本地用户、写绑定关系、发登录信号、建立 session、回跳；
       无邮箱：先落库，再跳"补全邮箱"页。
    """
    # SJQ: 平台类型
    type = request.GET.get('type', None)
    if not type:
        return HttpResponseRedirect('/')
    manager = get_manager_by_type(type)
    if not manager:
        return HttpResponseRedirect('/')
    # SJQ: 平台回调带回的授权码
    code = request.GET.get('code', None)
    try:
        # SJQ: 换 token；不同平台内部实现不同（POST/GET、JSON/querystring）
        rsp = manager.get_access_token_by_code(code)
    except OAuthAccessTokenException as e:
        # SJQ: 明确的授权失败：记警告并回首页（不重新授权，避免死循环）
        logger.warning("OAuthAccessTokenException:" + str(e))
        return HttpResponseRedirect('/')
    except Exception as e:
        # SJQ: 其他异常（网络、解析）按"没换到"处理，下面会重新发起授权
        logger.error(e)
        rsp = None
    # SJQ: 计算回跳地址
    nexturl = get_redirecturl(request)
    if not rsp:
        # SJQ: 没换到 token 就重新走一次授权，相当于让用户再试一遍
        return HttpResponseRedirect(manager.get_authorization_url(nexturl))
    # SJQ: 拉取平台用户信息，得到一个未入库的 OAuthUser 对象
    user = manager.get_oauth_userinfo()
    if user:
        # SJQ: 昵称为空时用 djangoblog+时间戳兜底，否则后续 username 会是空串
        if not user.nickname or not user.nickname.strip():
            user.nickname = "djangoblog" + timezone.now().strftime('%y%m%d%I%M%S')
        try:
            # SJQ: 用 (type, openid) 判断这个第三方账号是否登录过
            temp = OAuthUser.objects.get(type=type, openid=user.openid)
            # SJQ: 已存在则刷新头像、原始报文、昵称（昵称可能被用户在平台上改过）
            temp.picture = user.picture
            temp.metadata = user.metadata
            temp.nickname = user.nickname
            user = temp
        except ObjectDoesNotExist:
            # SJQ: 首次登录，保持新对象，后续 save() 时插入
            pass
        # facebook的token过长
        # SJQ: FaceBook token 超过模型 150 字符上限，这里直接置空规避截断/报错
        if type == 'facebook':
            user.token = ''
        if user.email:
            # SJQ: 有邮箱：整个"建用户+绑定"过程放在一个事务里，避免只成功一半
            with transaction.atomic():
                author = None
                try:
                    # SJQ: 已绑定的记录直接取关联用户
                    author = get_user_model().objects.get(id=user.author_id)
                except ObjectDoesNotExist:
                    pass
                if not author:
                    # SJQ: 按邮箱找本地用户，没有就创建一个（get_or_create 返回 (对象, 是否新建)）
                    result = get_user_model().objects.get_or_create(email=user.email)
                    author = result[0]
                    if result[1]:
                        # SJQ: 新建用户时补用户名：优先用平台昵称，重名则用时间戳后缀
                        try:
                            get_user_model().objects.get(username=user.nickname)
                        except ObjectDoesNotExist:
                            author.username = user.nickname
                        else:
                            author.username = "djangoblog" + timezone.now().strftime('%y%m%d%I%M%S')
                        # SJQ: 记录账号来源，便于后台区分注册渠道
                        author.source = 'authorize'
                        author.save()

                # SJQ: 建立/更新绑定关系
                user.author = author
                user.save()

                # SJQ: 通知其他应用"某第三方账号登录了"
                oauth_user_login_signal.send(
                    sender=authorize.__class__, id=user.id)
                # SJQ: 写入 session，用户正式登录
                login(request, author)
                # 设置session过期时间为2周（默认）
                # SJQ: 会话有效期取配置值
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                # 设置登录标记 cookie
                # SJQ: 前端脚本读取这个 cookie 判断是否已登录（httponly=False 是刻意为之）
                response = HttpResponseRedirect(nexturl)
                response.set_cookie(
                    'logged_user',
                    'true',
                    max_age=settings.SESSION_COOKIE_AGE,
                    httponly=False,  # 允许 JavaScript 访问
                    samesite='Lax'
                )
                return response
        else:
            # SJQ: 没拿到邮箱：先保存记录（此时 author 为空），再引导补全邮箱
            user.save()
            url = reverse('oauth:require_email', kwargs={
                'oauthid': user.id
            })

            return HttpResponseRedirect(url)
    else:
        # SJQ: 拉不到用户信息（平台字段变更/报文异常），只能回跳
        return HttpResponseRedirect(nexturl)


def emailconfirm(request, id, sign):
    """
    邮箱确认链接的落地处理。

    链接形如 /oauth/emailconfirm/<id>/<sign>.html。
    签名由 djangoblog.utils.get_sha256() 生成，注意它并不是普通 SHA256，而是
    HMAC-SHA256：key = SECRET_KEY，message = SECRET_KEY + id + SECRET_KEY。
    校验通过后在事务内完成"找或建本地用户 + 写绑定关系 + 登录 + 发欢迎邮件"。
    """
    # SJQ: 没有签名直接拒绝
    if not sign:
        return HttpResponseForbidden()
    # SJQ: 重算签名做比对，upper() 兼容大小写差异；用常量时间比较会更严谨（此处未做）
    if not get_sha256(settings.SECRET_KEY +
                      str(id) +
                      settings.SECRET_KEY).upper() == sign.upper():
        return HttpResponseForbidden()
    # SJQ: 取待确认的第三方用户记录，不存在则 404
    oauthuser = get_object_or_404(OAuthUser, pk=id)
    # SJQ: 绑定与建用户放在同一事务里
    with transaction.atomic():
        if oauthuser.author:
            # SJQ: 已绑定过就直接取原用户（重复点确认链接的场景）
            author = get_user_model().objects.get(pk=oauthuser.author_id)
        else:
            # SJQ: 未绑定：按邮箱找或建本地用户
            result = get_user_model().objects.get_or_create(email=oauthuser.email)
            author = result[0]
            if result[1]:
                # SJQ: 新建用户：来源标记为邮件确认，用户名用昵称，空则用时间戳
                author.source = 'emailconfirm'
                author.username = oauthuser.nickname.strip() if oauthuser.nickname.strip(
                ) else "djangoblog" + timezone.now().strftime('%y%m%d%I%M%S')
                author.save()
        # SJQ: 写入绑定关系
        oauthuser.author = author
        oauthuser.save()
    # SJQ: 发送登录信号
    oauth_user_login_signal.send(
        sender=emailconfirm.__class__,
        id=oauthuser.id)
    # SJQ: 建立登录态
    login(request, author)
    # 设置session过期时间为2周（默认）
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)

    # SJQ: 邮件正文里的站点地址；注意这里固定用 http 协议
    site = 'http://' + get_current_site().domain
    # SJQ: 欢迎邮件正文，占位符替换为平台名与站点地址
    content = _('''
     <p>Congratulations, you have successfully bound your email address. You can use
      %(oauthuser_type)s to directly log in to this website without a password.</p>
       You are welcome to continue to follow this site, the address is
        <a href="%(site)s" rel="bookmark">%(site)s</a>
            Thank you again!
            <br />
        If the link above cannot be opened, please copy this link to your browser.
        %(site)s
    ''') % {'oauthuser_type': oauthuser.type, 'site': site}

    # SJQ: 发送绑定成功通知邮件
    send_email(emailto=[oauthuser.email, ], title=_('Congratulations on your successful binding!'), content=content)
    # SJQ: 跳转到绑定成功提示页
    url = reverse('oauth:bindsuccess', kwargs={
        'oauthid': id
    })
    url = url + '?type=success'
    # 设置登录标记 cookie
    # SJQ: 与 authorize 中一致，前端据此切换"已登录"界面
    response = HttpResponseRedirect(url)
    response.set_cookie(
        'logged_user',
        'true',
        max_age=settings.SESSION_COOKIE_AGE,
        httponly=False,  # 允许 JavaScript 访问
        samesite='Lax'
    )
    return response


class RequireEmailView(FormView):
    """
    补全邮箱页。

    第三方平台未返回邮箱时，authorize 会跳到本页；用户填写邮箱后，
    本视图保存邮箱并发送一封带签名链接的确认邮件，用户点链接才真正完成绑定。
    """

    # SJQ: 表单类，只含 email 与隐藏的 oauthid
    form_class = RequireEmailForm
    # SJQ: 页面模板
    template_name = 'oauth/require_email.html'

    def get(self, request, *args, **kwargs):
        """展示补全邮箱页；顺带校验 oauthid 对应的记录是否存在。"""
        # SJQ: 从 URL 里取第三方用户 id
        oauthid = self.kwargs['oauthid']
        # SJQ: 记录不存在会直接 404，避免后续保存时报错
        oauthuser = get_object_or_404(OAuthUser, pk=oauthid)
        if oauthuser.email:
            # SJQ: 已经有邮箱时本该跳过本页，但这段重定向被注释掉了，当前仍会展示表单
            pass
            # return HttpResponseRedirect('/')

        # SJQ: 交给父类渲染表单
        return super(RequireEmailView, self).get(request, *args, **kwargs)

    def get_initial(self):
        """表单初始值：邮箱留空，隐藏域带上 oauthid。"""
        # SJQ: 从 URL 取 oauthid
        oauthid = self.kwargs['oauthid']
        return {
            'email': '',
            'oauthid': oauthid
        }

    def get_context_data(self, **kwargs):
        """补充模板上下文：有头像时把头像地址传给页面显示。"""
        oauthid = self.kwargs['oauthid']
        oauthuser = get_object_or_404(OAuthUser, pk=oauthid)
        if oauthuser.picture:
            kwargs['picture'] = oauthuser.picture
        return super(RequireEmailView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        """表单校验通过：保存邮箱、生成签名链接、发送确认邮件、跳到提示页。"""
        # SJQ: 取出用户填写的邮箱与隐藏的 oauthid
        email = form.cleaned_data['email']
        oauthid = form.cleaned_data['oauthid']
        oauthuser = get_object_or_404(OAuthUser, pk=oauthid)
        # SJQ: 先落库，即使用户不去点邮件里的链接，邮箱也已记录
        oauthuser.email = email
        oauthuser.save()
        # SJQ: 生成签名：get_sha256 内部是 HMAC-SHA256（密钥 SECRET_KEY，消息 SECRET_KEY+id+SECRET_KEY）
        # SJQ: 必须与 emailconfirm 中的算法一致，否则确认链接永远校验不过
        sign = get_sha256(settings.SECRET_KEY +
                          str(oauthuser.id) + settings.SECRET_KEY)
        site = get_current_site().domain
        # SJQ: 开发环境用本机地址，方便本地点开邮件里的链接
        if settings.DEBUG:
            site = '127.0.0.1:8000'
        # SJQ: 反解确认链接路径
        path = reverse('oauth:email_confirm', kwargs={
            'id': oauthid,
            'sign': sign
        })
        # SJQ: 拼成绝对地址，邮件客户端需要完整 URL
        url = "http://{site}{path}".format(site=site, path=path)

        # SJQ: 确认邮件正文
        content = _("""
               <p>Please click the link below to bind your email</p>

                 <a href="%(url)s" rel="bookmark">%(url)s</a>

                 Thank you again!
                 <br />
                 If the link above cannot be opened, please copy this link to your browser.
                  <br />
                 %(url)s
                """) % {'url': url}
        # SJQ: 发送确认邮件
        send_email(emailto=[email, ], title=_('Bind your email'), content=content)
        # SJQ: 跳提示页，type=email 表示"邮件已发出，待确认"
        url = reverse('oauth:bindsuccess', kwargs={
            'oauthid': oauthid
        })
        url = url + '?type=email'
        return HttpResponseRedirect(url)


def bindsuccess(request, oauthid):
    """
    绑定结果提示页。

    用 type 区分两种状态：email 表示"确认邮件已发出"，
    其他（success）表示"绑定已完成"，页面文案随之不同。
    """
    # SJQ: 从查询串取状态类型
    type = request.GET.get('type', None)
    # SJQ: 记录不存在则 404
    oauthuser = get_object_or_404(OAuthUser, pk=oauthid)
    if type == 'email':
        # SJQ: 邮件已发送但尚未确认
        title = _('Bind your email')
        content = _(
            'Congratulations, the binding is just one step away. '
            'Please log in to your email to check the email to complete the binding. Thank you.')
    else:
        # SJQ: 绑定成功
        title = _('Binding successful')
        content = _(
            "Congratulations, you have successfully bound your email address. You can use %(oauthuser_type)s"
            " to directly log in to this website without a password. You are welcome to continue to follow this site." % {
                'oauthuser_type': oauthuser.type})
    # SJQ: 渲染统一的结果页
    return render(request, 'oauth/bindsuccess.html', {
        'title': title,
        'content': content
    })
