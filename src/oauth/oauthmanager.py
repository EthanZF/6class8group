"""
oauth 第三方登录管理器模块。

本模块是"平台差异"的唯一收敛点：每个第三方平台对应一个管理器子类，
把各自不同的授权地址、token 交换方式、用户信息字段映射封装起来，
上层视图（views.py）只面向 BaseOauthManager 的四个抽象方法编程，不关心平台细节。

类结构：
- BaseOauthManager：抽象基类，定义授权/换 token/取用户信息/取头像四个动作与 HTTP 辅助方法；
- ProxyManagerMixin：为需要走代理的平台补一层 do_get/do_post 覆盖（读取 HTTP_PROXY 环境变量）；
- WBOauthManager / GoogleOauthManager / GitHubOauthManager / FaceBookOauthManager / QQOauthManager：
  五个平台的实现，仅声明 URL 常量、ICON_NAME 与字段映射；
- get_oauth_apps() / get_manager_by_type()：按数据库配置装配管理器实例的工厂函数。

SJQ: 模块级注释，说明本模块的职责、类继承结构以及上层视图依赖的抽象边界。
"""
# SJQ: json 用于解析各平台返回的 JSON 报文
import json
# SJQ: logging 记录换取 token、拉取用户信息时的异常与原始响应
import logging
# SJQ: os 读取 HTTP_PROXY 环境变量，决定是否走代理
import os
# SJQ: urllib.parse 用于拼接授权 URL 的查询串、解析 QQ 返回的 querystring
import urllib.parse
# SJQ: ABCMeta/abstractmethod 把 BaseOauthManager 定义成抽象基类，强制子类实现四个动作
from abc import ABCMeta, abstractmethod

# SJQ: requests 发 HTTP 请求，访问各平台的 token 接口与用户信息接口
import requests

# SJQ: cache_decorator 给 get_oauth_apps() 加缓存，避免每次渲染登录页都查库
from djangoblog.utils import cache_decorator
# SJQ: 两个模型：配置决定启用哪些平台，用户表用于组装返回的临时对象
from oauth.models import OAuthUser, OAuthConfig

# SJQ: 模块级日志器，日志名即模块路径，便于按模块过滤
logger = logging.getLogger(__name__)


class OAuthAccessTokenException(Exception):
    """
    换取 access_token 失败时抛出的异常。

    各平台失败时返回的报文格式不同（有的是 JSON，有的是 querystring），
    统一包装成这个异常后，视图层只需捕获一种类型即可回退到重新授权。
    """


class BaseOauthManager(metaclass=ABCMeta):
    """
    第三方授权管理器抽象基类。

    子类通过覆盖 AUTH_URL/TOKEN_URL/API_URL/ICON_NAME 四个类属性来声明平台差异，
    并实现四个抽象方法完成"授权地址 → 换 token → 取用户信息 → 取头像"的固定流程。
    """

    # SJQ: 授权页地址，子类必须覆盖
    AUTH_URL = None
    """获取token"""
    # SJQ: 用 code 换 token 的接口地址
    TOKEN_URL = None
    """获取用户信息"""
    # SJQ: 拉取用户资料的接口地址
    API_URL = None
    '''icon图标名'''
    # SJQ: 平台标识（与 OAuthConfig.type 对应），也用于前台取图标
    ICON_NAME = None

    def __init__(self, access_token=None, openid=None):
        """初始化管理器，可带入已持有的 token 与 openid 以便复用授权状态。"""
        # SJQ: 访问令牌，未授权时为 None
        self.access_token = access_token
        # SJQ: 平台侧用户标识，部分平台（如 QQ）要二次请求才能拿到
        self.openid = openid

    @property
    def is_access_token_set(self):
        """是否已经拿到 access_token。"""
        # SJQ: 只判断是否为 None，空字符串会被视为已设置（各平台不会返回空串，风险可接受）
        return self.access_token is not None

    @property
    def is_authorized(self):
        """是否同时具备 token 与 openid，即具备调用用户信息接口的条件。"""
        # SJQ: 三个条件同时成立才算授权完成
        return self.is_access_token_set and self.access_token is not None and self.openid is not None

    @abstractmethod
    def get_authorization_url(self, nexturl='/'):
        """拼出平台授权页地址；nexturl 为授权完成后要跳回的站内地址。"""

    @abstractmethod
    def get_access_token_by_code(self, code):
        """用回调带回的 code 换取 access_token，并把 token/openid 写回自身。"""

    @abstractmethod
    def get_oauth_userinfo(self):
        """拉取平台用户资料，返回一个尚未入库的 OAuthUser 对象。"""

    @abstractmethod
    def get_picture(self, metadata):
        """从已保存的原始报文中解析出头像地址。"""

    def do_get(self, url, params, headers=None):
        """发送 GET 请求并返回响应文本；子类/混入类可覆盖以支持代理。"""
        # SJQ: 直接透传参数，不做过期重试，失败由调用方按报文内容判断
        rsp = requests.get(url=url, params=params, headers=headers)
        # SJQ: 记录原始响应，便于排查平台侧字段变更
        logger.info(rsp.text)
        return rsp.text

    def do_post(self, url, params, headers=None):
        """发送 POST 请求并返回响应文本；子类/混入类可覆盖以支持代理。"""
        # SJQ: 注意第二个位置参数是 params 而非 data，表单编码由 requests 按 params 处理
        rsp = requests.post(url, params, headers=headers)
        # SJQ: 记录原始响应
        logger.info(rsp.text)
        return rsp.text

    def get_config(self):
        """按 ICON_NAME 取本平台的启用配置；没有配置时返回 None。"""
        # SJQ: 这里没有过滤 is_enable，配置是否启用由 get_oauth_apps() 统一把关
        value = OAuthConfig.objects.filter(type=self.ICON_NAME)
        # SJQ: 取第一条；未配置时返回 None，子类构造函数会把 client_id 等置为空串
        return value[0] if value else None


class WBOauthManager(BaseOauthManager):
    """
    新浪微博登录管理器。

    微博用 uid 作为用户标识，换取 token 的接口同时返回 uid，因此无需二次请求。
    """

    # SJQ: 微博授权页
    AUTH_URL = 'https://api.weibo.com/oauth2/authorize'
    # SJQ: 微博 token 接口
    TOKEN_URL = 'https://api.weibo.com/oauth2/access_token'
    # SJQ: 微博用户信息接口
    API_URL = 'https://api.weibo.com/2/users/show.json'
    # SJQ: 平台标识，同时决定读哪条 OAuthConfig
    ICON_NAME = 'weibo'

    def __init__(self, access_token=None, openid=None):
        """从数据库读取微博平台配置，初始化 client_id/client_secret/回调地址。"""
        # SJQ: 取本平台配置；未配置时各字段退化为空串，后续请求会失败但不会抛异常
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        # SJQ: 交回基类初始化 token/openid
        super(
            WBOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, nexturl='/'):
        """拼微博授权地址，把 nexturl 附在回调地址后面，授权回来后据此跳转。"""
        # SJQ: 微博要求 redirect_uri 与登记值一致，这里在其后追加 &next_url= 参数
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url + '&next_url=' + nexturl
        }
        # SJQ: 拼成完整授权地址
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """用 code 换 token；微博在同一个响应里返回 uid，随后直接拉取用户信息。"""
        # SJQ: 换取 token 所需的表单参数
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.callback_url
        }
        # SJQ: 微博的 token 接口是 POST
        rsp = self.do_post(self.TOKEN_URL, params)

        # SJQ: 成功时返回 JSON，含 access_token 与 uid
        obj = json.loads(rsp)
        if 'access_token' in obj:
            # SJQ: 保存 token 与 uid，uid 即微博侧用户标识
            self.access_token = str(obj['access_token'])
            self.openid = str(obj['uid'])
            # SJQ: 微博这一步就能拿到用户信息，直接返回
            return self.get_oauth_userinfo()
        else:
            # SJQ: 失败时把原始报文包进异常，交给视图层回退
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        """拉取微博用户资料并映射为 OAuthUser 对象。"""
        # SJQ: 没拿到 token 或 uid 时不发请求，直接返回 None
        if not self.is_authorized:
            return None
        # SJQ: 微博用户信息接口需要 uid + access_token
        params = {
            'uid': self.openid,
            'access_token': self.access_token
        }
        rsp = self.do_get(self.API_URL, params)
        try:
            # SJQ: 解析并逐字段映射；metadata 存整段原始报文
            datas = json.loads(rsp)
            user = OAuthUser()
            user.metadata = rsp
            user.picture = datas['avatar_large']
            user.nickname = datas['screen_name']
            user.openid = datas['id']
            user.type = 'weibo'
            user.token = self.access_token
            # SJQ: 微博只有授权了 email 权限才返回邮箱，因此先判存在再取
            if 'email' in datas and datas['email']:
                user.email = datas['email']
            return user
        except Exception as e:
            # SJQ: 字段缺失或报文非 JSON 时记录日志并返回 None，不向上抛异常
            logger.error(e)
            logger.error('weibo oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        """从微博原始报文中取头像地址。"""
        # SJQ: metadata 是保存下来的 JSON 字符串
        datas = json.loads(metadata)
        return datas['avatar_large']


class ProxyManagerMixin:
    """
    代理支持混入类。

    Google/GitHub/FaceBook 在国内访问需要代理，本混入类读取 HTTP_PROXY 环境变量，
    并覆盖 do_get/do_post 把 proxies 传给 requests。使用方式为把本类写在继承列表第一位，
    让它的方法在 MRO 中优先于 BaseOauthManager。
    """

    def __init__(self, *args, **kwargs):
        """读取环境变量决定代理设置，然后把参数原样交给下一个类。"""
        # SJQ: 有 HTTP_PROXY 就两个协议都用它，否则明确置 None
        if os.environ.get("HTTP_PROXY"):
            self.proxies = {
                "http": os.environ.get("HTTP_PROXY"),
                "https": os.environ.get("HTTP_PROXY")
            }
        else:
            self.proxies = None

    def do_get(self, url, params, headers=None):
        """带代理的 GET 请求。"""
        # SJQ: 与基类唯一的差别是多了 proxies 参数
        rsp = requests.get(url=url, params=params, headers=headers, proxies=self.proxies)
        # SJQ: 记录原始响应
        logger.info(rsp.text)
        return rsp.text

    def do_post(self, url, params, headers=None):
        """带代理的 POST 请求。"""
        # SJQ: 同样只多传 proxies
        rsp = requests.post(url, params, headers=headers, proxies=self.proxies)
        # SJQ: 记录原始响应
        logger.info(rsp.text)
        return rsp.text


class GoogleOauthManager(ProxyManagerMixin, BaseOauthManager):
    """
    Google 登录管理器。

    Google 用 id_token 作为 openid 的替代，用户信息接口返回 sub 字段作为唯一标识。
    """

    # SJQ: Google 授权页
    AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    # SJQ: Google token 接口
    TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'
    # SJQ: Google 用户信息接口
    API_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
    # SJQ: 平台标识
    ICON_NAME = 'google'

    def __init__(self, access_token=None, openid=None):
        """读取 Google 平台配置并初始化客户端参数。"""
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        # SJQ: 注意这里调用 super 会进入 ProxyManagerMixin.__init__，它只设置 proxies，
        # SJQ: 不会再转交 BaseOauthManager.__init__，因此 self.access_token/openid 实际未被赋值。
        # SJQ: 这是既有实现的缺陷，本次任务只加注释、不修改代码行为，详见质量分析报告。
        super(
            GoogleOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, nexturl='/'):
        """拼 Google 授权地址；scope 申请 openid 与 email。"""
        # SJQ: Google 的回调地址不加 next_url，跳转目标由视图层会话变量控制
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url,
            'scope': 'openid email',
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """用 code 换 token；Google 把 id_token 当作用户标识保存。"""
        # SJQ: 换取 token 的表单参数
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,

            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        obj = json.loads(rsp)

        if 'access_token' in obj:
            # SJQ: 保存 access_token；openid 用 id_token 代替
            self.access_token = str(obj['access_token'])
            self.openid = str(obj['id_token'])
            # SJQ: 这里返回的是 token 字符串而不是用户对象，与其他平台不一致
            logger.info(self.ICON_NAME + ' oauth ' + rsp)
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        """拉取 Google 用户资料并映射为 OAuthUser 对象。"""
        if not self.is_authorized:
            return None
        # SJQ: Google 用 Bearer token 之外的 query 参数方式传 access_token
        params = {
            'access_token': self.access_token
        }
        rsp = self.do_get(self.API_URL, params)
        try:
            datas = json.loads(rsp)
            user = OAuthUser()
            user.metadata = rsp
            user.picture = datas['picture']
            user.nickname = datas['name']
            # SJQ: Google 的唯一标识是 sub
            user.openid = datas['sub']
            user.token = self.access_token
            user.type = 'google'
            if datas['email']:
                user.email = datas['email']
            return user
        except Exception as e:
            logger.error(e)
            logger.error('google oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        """从 Google 原始报文中取头像地址。"""
        datas = json.loads(metadata)
        return datas['picture']


class GitHubOauthManager(ProxyManagerMixin, BaseOauthManager):
    """
    GitHub 登录管理器。

    与其他平台最大的差异是：token 接口返回 querystring 而不是 JSON；
    并且用户邮箱可能设为私有，需要再请求 /user/emails 才能取到。
    """

    # SJQ: GitHub 授权页
    AUTH_URL = 'https://github.com/login/oauth/authorize'
    # SJQ: GitHub token 接口
    TOKEN_URL = 'https://github.com/login/oauth/access_token'
    # SJQ: GitHub 用户信息接口
    API_URL = 'https://api.github.com/user'
    # SJQ: 用户邮箱列表接口，仅在公开邮箱为空时使用
    EMAILS_API_URL = 'https://api.github.com/user/emails'
    # SJQ: 平台标识
    ICON_NAME = 'github'

    def __init__(self, access_token=None, openid=None):
        """读取 GitHub 平台配置并初始化客户端参数。"""
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        # SJQ: 与 Google 相同的 MRO 问题：ProxyManagerMixin.__init__ 不会转交基类构造
        super(
            GitHubOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, next_url='/'):
        """拼 GitHub 授权地址；scope 申请 user:email 以便读取私有邮箱。"""
        # SJQ: 参数名是 next_url（与基类的 nexturl 不同名，但调用方用位置参数传入，不影响）
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': f'{self.callback_url}&next_url={next_url}',
            'scope': 'user:email'
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """用 code 换 token；GitHub 返回的是 querystring，需用 parse_qs 解析。"""
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,

            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        # SJQ: 局部导入 parse，避免与其他平台的 urllib.parse 用法混淆
        from urllib import parse
        r = parse.parse_qs(rsp)
        if 'access_token' in r:
            # SJQ: parse_qs 的值是列表，取第一个元素
            self.access_token = (r['access_token'][0])
            # SJQ: GitHub 的 token 接口不返回用户 id，openid 留待取用户信息时补
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        """拉取 GitHub 用户资料；公开邮箱为空时再查邮箱列表接口。"""
        # SJQ: GitHub 用 Authorization: Bearer 头传 token，而不是 query 参数
        rsp = self.do_get(self.API_URL, params={}, headers={
            "Authorization": "Bearer " + self.access_token
        })
        try:
            datas = json.loads(rsp)
            user = OAuthUser()
            user.picture = datas['avatar_url']
            user.nickname = datas['name']
            user.openid = datas['id']
            user.type = 'github'
            user.token = self.access_token
            user.metadata = rsp
            if 'email' in datas and datas['email']:
                user.email = datas['email']
            else:
                # SJQ: 公开邮箱为空时，额外请求 /user/emails，优先取"主邮箱且已验证"的那条
                try:
                    emails_rsp = self.do_get(self.EMAILS_API_URL, params={}, headers={
                        "Authorization": "Bearer " + self.access_token
                    })
                    emails = json.loads(emails_rsp)
                    # SJQ: 遍历邮箱列表，先找 primary+verified，找不到就用第一个 verified
                    for email_data in emails:
                        if email_data.get('verified'):
                            if email_data.get('primary'):
                                # SJQ: 主邮箱且已验证，优先级最高，直接跳出
                                user.email = email_data.get('email')
                                break
                            elif not user.email:
                                # SJQ: 退而求其次：第一个已验证的邮箱
                                user.email = email_data.get('email')
                except Exception as e:
                    # SJQ: 取私有邮箱失败不影响主流程，只记警告；
                    # SJQ: 若站点强制要求邮箱，登录会在后续步骤失败
                    logger.warning(
                        f'Failed to fetch private email from GitHub API. '
                        f'User login will fail if email is required: {e}')
            return user
        except Exception as e:
            logger.error(e)
            logger.error('github oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        """从 GitHub 原始报文中取头像地址。"""
        datas = json.loads(metadata)
        return datas['avatar_url']


class FaceBookOauthManager(ProxyManagerMixin, BaseOauthManager):
    """
    FaceBook 登录管理器。

    FaceBook 的 token 较长（超过模型 150 字符上限），因此视图层会主动把 token 置空。
    """

    # SJQ: FaceBook 授权页（v16.0）
    AUTH_URL = 'https://www.facebook.com/v16.0/dialog/oauth'
    # SJQ: FaceBook token 接口
    TOKEN_URL = 'https://graph.facebook.com/v16.0/oauth/access_token'
    # SJQ: FaceBook 用户信息接口
    API_URL = 'https://graph.facebook.com/me'
    # SJQ: 平台标识
    ICON_NAME = 'facebook'

    def __init__(self, access_token=None, openid=None):
        """读取 FaceBook 平台配置并初始化客户端参数。"""
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        # SJQ: 同样存在 MRO 导致基类构造未被调用的问题
        super(
            FaceBookOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, next_url='/'):
        """拼 FaceBook 授权地址；scope 申请 email 与公开资料。"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url,
            'scope': 'email,public_profile'
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """用 code 换 token；FaceBook 返回 JSON。"""
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            # 'grant_type': 'authorization_code',
            'code': code,

            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        obj = json.loads(rsp)
        if 'access_token' in obj:
            token = str(obj['access_token'])
            self.access_token = token
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        """拉取 FaceBook 用户资料并映射为 OAuthUser 对象。"""
        # SJQ: 用 fields 显式声明要返回的字段，减少一次请求拿不全的情况
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,picture,email'
        }
        try:
            rsp = self.do_get(self.API_URL, params)
            datas = json.loads(rsp)
            user = OAuthUser()
            user.nickname = datas['name']
            user.openid = datas['id']
            user.type = 'facebook'
            user.token = self.access_token
            user.metadata = rsp
            if 'email' in datas and datas['email']:
                user.email = datas['email']
            # SJQ: 头像嵌在 picture.data.url 三层结构里，逐层判空后再取
            if 'picture' in datas and datas['picture'] and datas['picture']['data'] and datas['picture']['data']['url']:
                user.picture = str(datas['picture']['data']['url'])
            return user
        except Exception as e:
            logger.error(e)
            return None

    def get_picture(self, metadata):
        """从 FaceBook 原始报文中取头像地址。"""
        datas = json.loads(metadata)
        return str(datas['picture']['data']['url'])


class QQOauthManager(BaseOauthManager):
    """
    QQ 登录管理器。

    QQ 不直接返回 openid，需要先调 /oauth2.0/me 拿到 openid，再调用户信息接口，
    因此这里多了一个 get_open_id() 方法，且 get_oauth_userinfo() 依赖它的结果。
    """

    # SJQ: QQ 授权页
    AUTH_URL = 'https://graph.qq.com/oauth2.0/authorize'
    # SJQ: QQ token 接口
    TOKEN_URL = 'https://graph.qq.com/oauth2.0/token'
    # SJQ: QQ 用户信息接口
    API_URL = 'https://graph.qq.com/user/get_user_info'
    # SJQ: QQ 获取 openid 的接口
    OPEN_ID_URL = 'https://graph.qq.com/oauth2.0/me'
    # SJQ: 平台标识
    ICON_NAME = 'qq'

    def __init__(self, access_token=None, openid=None):
        """读取 QQ 平台配置并初始化客户端参数。"""
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        # SJQ: QQ 未使用 ProxyManagerMixin，这里的 super 会正常进入基类构造
        super(
            QQOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, next_url='/'):
        """拼 QQ 授权地址，把 next_url 附在回调地址后。"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.callback_url + '&next_url=' + next_url,
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        """用 code 换 token；QQ 返回 querystring，且用 GET 而不是 POST。"""
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.callback_url
        }
        # SJQ: QQ 的 token 接口用 GET
        rsp = self.do_get(self.TOKEN_URL, params)
        if rsp:
            # SJQ: 解析 querystring 形式的响应
            d = urllib.parse.parse_qs(rsp)
            if 'access_token' in d:
                # SJQ: 注意这里返回的是列表而不是字符串，与其他平台返回值类型不一致
                token = d['access_token']
                self.access_token = token[0]
                return token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_open_id(self):
        """调 /oauth2.0/me 取 openid；该接口返回 JSONP 形式，需要剥掉 callback(...) 外壳。"""
        # SJQ: 必须先有 token 才能请求
        if self.is_access_token_set:
            params = {
                'access_token': self.access_token
            }
            rsp = self.do_get(self.OPEN_ID_URL, params)
            if rsp:
                # SJQ: 依次去掉 callback( 、) 和结尾分号，得到纯 JSON
                rsp = rsp.replace(
                    'callback(', '').replace(
                    ')', '').replace(
                    ';', '')
                obj = json.loads(rsp)
                openid = str(obj['openid'])
                # SJQ: 回写 openid，供后续用户信息接口使用
                self.openid = openid
                return openid

    def get_oauth_userinfo(self):
        """先取 openid，再拉用户资料并映射为 OAuthUser 对象。"""
        # SJQ: QQ 的 openid 必须二次请求获得
        openid = self.get_open_id()
        if openid:
            # SJQ: QQ 用户信息接口需要 access_token + 应用 id + openid 三个参数
            params = {
                'access_token': self.access_token,
                'oauth_consumer_key': self.client_id,
                'openid': self.openid
            }
            rsp = self.do_get(self.API_URL, params)
            logger.info(rsp)
            obj = json.loads(rsp)
            user = OAuthUser()
            user.nickname = obj['nickname']
            user.openid = openid
            user.type = 'qq'
            user.token = self.access_token
            user.metadata = rsp
            if 'email' in obj:
                user.email = obj['email']
            if 'figureurl' in obj:
                user.picture = str(obj['figureurl'])
            return user

    def get_picture(self, metadata):
        """从 QQ 原始报文中取头像地址。"""
        datas = json.loads(metadata)
        return str(datas['figureurl'])


@cache_decorator(expiration=100 * 60)
def get_oauth_apps():
    """
    装配并返回当前启用的平台管理器实例列表。

    结果缓存 100 分钟：登录页每次渲染都要显示平台按钮，不缓存会频繁查 OAuthConfig 表。
    修改后台配置后最多需要等 100 分钟才会生效（或手动清缓存）。
    """
    # SJQ: 只取启用的配置；没有配置直接返回空列表，前台不显示第三方登录入口
    configs = OAuthConfig.objects.filter(is_enable=True).all()
    if not configs:
        return []
    # SJQ: 数据库里的 type 集合，用来过滤已实现的平台
    configtypes = [x.type for x in configs]
    # SJQ: 通过 __subclasses__ 拿到全部已实现的管理器子类，新增平台只需加子类，无需改这里
    applications = BaseOauthManager.__subclasses__()
    # SJQ: 实例化并保留 ICON_NAME 出现在配置集合中的那些；
    # SJQ: 注意 x() 被调用了两次（列表推导里一次、判断里一次），属于可优化的重复实例化
    apps = [x() for x in applications if x().ICON_NAME.lower() in configtypes]
    return apps


def get_manager_by_type(type):
    """
    按平台类型返回对应的管理器实例；找不到返回 None。

    视图层拿到 None 时会直接重定向到首页，相当于把"未配置/未实现平台"当作非法入口处理。
    """
    # SJQ: 复用带缓存的全量列表，避免每次请求都查库
    applications = get_oauth_apps()
    if applications:
        # SJQ: 按 ICON_NAME 匹配，大小写不敏感
        finds = list(
            filter(
                lambda x: x.ICON_NAME.lower() == type.lower(),
                applications))
        if finds:
            return finds[0]
    return None
