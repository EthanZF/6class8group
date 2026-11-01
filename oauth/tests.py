"""
oauth 应用的集成测试。

本文件从"视图 + 路由 + 管理器"整体链路验证第三方登录，与
test_oauth_business_logic.py（纯模型层业务逻辑）分工不同：
- 本文件用 patch 替换 do_get/do_post，模拟各平台返回，跑通登录闭环；
- 断言重点是状态码、跳转地址、登录态与用户字段。

覆盖场景：
1. 配置驱动的登录入口跳转；
2. 五个平台各自的 token 交换与字段映射；
3. GitHub 私有邮箱的二次请求；
4. 有邮箱时自动建号并登录；
5. 无邮箱时走"补全邮箱 → 邮件确认 → 绑定成功"的完整链路。

SJQ: 模块级注释，说明本文件的测试层次、覆盖场景以及与另一测试文件的分工。
"""
# SJQ: json 用于构造各平台返回的报文
import json
# SJQ: patch 用于替换 HTTP 请求方法，避免测试真的访问第三方平台
from unittest.mock import patch
# SJQ: unquote 用于断言 URL 中编码后的 scope 参数
from urllib.parse import unquote

# SJQ: settings 取 SECRET_KEY，复算确认链接签名
from django.conf import settings
# SJQ: auth 用于取当前请求的登录用户
from django.contrib import auth
# SJQ: Client 模拟浏览器请求；RequestFactory 预留；TestCase 提供测试数据库
from django.test import Client, RequestFactory, TestCase
# SJQ: reverse 反解路由，构造确认链接
from django.urls import reverse

# SJQ: get_sha256 与视图使用同一签名算法，保证测试与实现一致
from djangoblog.utils import get_sha256
# SJQ: 配置模型，测试前需要先建一条平台配置
from oauth.models import OAuthConfig
# SJQ: 通过基类的 __subclasses__ 动态发现全部平台管理器
from oauth.oauthmanager import BaseOauthManager


# Create your tests here.
class OAuthConfigTest(TestCase):
    """登录入口的冒烟测试：配置一条微博后，入口应能跳到微博授权页。"""

    def setUp(self):
        """准备测试客户端，并清空缓存避免上一个用例的启用平台列表残留。"""
        # SJQ: 模拟浏览器
        self.client = Client()
        # SJQ: 本类未用到 RequestFactory，属预留
        self.factory = RequestFactory()
        # 清除 OAuth apps 缓存，避免测试隔离问题
        # SJQ: get_oauth_apps 带 100 分钟缓存，不清会导致跨用例污染
        from django.core.cache import cache
        cache.clear()

    def test_oauth_login_test(self):
        """配置微博后，/oauth/oauthlogin 应 302 到 api.weibo.com。"""
        # SJQ: 建一条微博配置（未调用 full_clean，所以 default='a' 的坑不会暴露）
        c = OAuthConfig()
        c.type = 'weibo'
        c.appkey = 'appkey'
        c.appsecret = 'appsecret'
        c.save()

        # SJQ: 访问登录入口
        response = self.client.get('/oauth/oauthlogin?type=weibo')
        # SJQ: 应重定向到微博授权页
        self.assertEqual(response.status_code, 302)
        self.assertTrue("api.weibo.com" in response.url)

        # SJQ: 直接访问回调地址（不带有效 code），应回首页而不是报错
        response = self.client.get('/oauth/authorize?type=weibo&code=code')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')


class OauthLoginTest(TestCase):
    """第三方登录主流程测试：覆盖五个平台的报文解析与两条绑定分支。"""

    def setUp(self) -> None:
        """清缓存、建全平台配置，并实例化全部管理器备用。"""
        # SJQ: 模拟浏览器
        self.client = Client()
        self.factory = RequestFactory()
        # 清除 OAuth apps 缓存，避免测试隔离问题
        from django.core.cache import cache
        cache.clear()
        # SJQ: 为每个已实现的平台各建一条配置
        self.apps = self.init_apps()

    def init_apps(self):
        """为 BaseOauthManager 的每个子类建一条配置，返回管理器实例列表。"""
        # SJQ: 动态发现子类，新增平台后本测试自动覆盖
        applications = [p() for p in BaseOauthManager.__subclasses__()]
        for application in applications:
            # SJQ: 用 ICON_NAME 作为配置的 type，保证 get_oauth_apps() 能匹配上
            c = OAuthConfig()
            c.type = application.ICON_NAME.lower()
            c.appkey = 'appkey'
            c.appsecret = 'appsecret'
            c.save()
        return applications

    def get_app_by_type(self, type):
        """按平台标识从已实例化的管理器里取一个。"""
        for app in self.apps:
            if app.ICON_NAME.lower() == type:
                return app

    @patch("oauth.oauthmanager.WBOauthManager.do_post")
    @patch("oauth.oauthmanager.WBOauthManager.do_get")
    def test_weibo_login(self, mock_do_get, mock_do_post):
        """微博：token 接口返回 access_token+uid，用户信息返回 screen_name 等。"""
        # SJQ: 取微博管理器
        weibo_app = self.get_app_by_type('weibo')
        assert weibo_app
        # SJQ: 拼授权地址（本用例未断言，仅验证不抛异常）
        url = weibo_app.get_authorization_url()
        # SJQ: 模拟 token 接口返回
        mock_do_post.return_value = json.dumps({"access_token": "access_token",
                                                "uid": "uid"
                                                })
        # SJQ: 模拟用户信息接口返回
        mock_do_get.return_value = json.dumps({
            "avatar_large": "avatar_large",
            "screen_name": "screen_name",
            "id": "id",
            "email": "email",
        })
        # SJQ: 微博在换 token 时就直接返回了用户对象
        userinfo = weibo_app.get_access_token_by_code('code')
        self.assertEqual(userinfo.token, 'access_token')
        self.assertEqual(userinfo.openid, 'id')

    @patch("oauth.oauthmanager.GoogleOauthManager.do_post")
    @patch("oauth.oauthmanager.GoogleOauthManager.do_get")
    def test_google_login(self, mock_do_get, mock_do_post):
        """Google：openid 取自 id_token，用户信息里的 sub 才是唯一标识。"""
        google_app = self.get_app_by_type('google')
        assert google_app
        url = google_app.get_authorization_url()
        mock_do_post.return_value = json.dumps({
            "access_token": "access_token",
            "id_token": "id_token",
        })
        mock_do_get.return_value = json.dumps({
            "picture": "picture",
            "name": "name",
            "sub": "sub",
            "email": "email",
        })
        # SJQ: Google 的换 token 只返回 token 字符串，需要再调一次取用户信息
        token = google_app.get_access_token_by_code('code')
        userinfo = google_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'access_token')
        self.assertEqual(userinfo.openid, 'sub')

    @patch("oauth.oauthmanager.GitHubOauthManager.do_post")
    @patch("oauth.oauthmanager.GitHubOauthManager.do_get")
    def test_github_login(self, mock_do_get, mock_do_post):
        """GitHub：token 接口返回 querystring，需用 parse_qs 解析。"""
        github_app = self.get_app_by_type('github')
        assert github_app
        url = github_app.get_authorization_url()
        self.assertTrue("github.com" in url)
        self.assertTrue("client_id" in url)
        # SJQ: 注意这里是 querystring 而不是 JSON，模拟 GitHub 的真实返回格式
        mock_do_post.return_value = "access_token=gho_16C7e42F292c6912E7710c838347Ae178B4a&scope=repo%2Cgist&token_type=bearer"
        mock_do_get.return_value = json.dumps({
            "avatar_url": "avatar_url",
            "name": "name",
            "id": "id",
            "email": "email",
        })
        token = github_app.get_access_token_by_code('code')
        userinfo = github_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'gho_16C7e42F292c6912E7710c838347Ae178B4a')
        self.assertEqual(userinfo.openid, 'id')


    @patch("oauth.oauthmanager.GitHubOauthManager.do_post")
    @patch("oauth.oauthmanager.GitHubOauthManager.do_get")
    def test_github_login_private_email(self, mock_do_get, mock_do_post):
        """Test GitHub OAuth login when user's email is private"""
        github_app = self.get_app_by_type('github')
        assert github_app
        url = github_app.get_authorization_url()
        # Verify the URL starts with GitHub's OAuth endpoint
        # SJQ: 断言授权地址前缀，确保没有拼错域名
        self.assertTrue(url.startswith("https://github.com/login/oauth/authorize"))
        self.assertTrue("client_id" in url)
        # Check that the scope parameter includes user:email (URL-encoded form)
        # SJQ: scope 在 URL 中是编码过的（user%3Aemail），所以先 unquote 再断言
        self.assertIn("user:email", unquote(url))
        
        mock_do_post.return_value = "access_token=gho_test_token&scope=user:email&token_type=bearer"
        
        # First call returns user info without email (private email)
        # Second call returns emails from /user/emails endpoint
        # SJQ: side_effect 依次返回两次 GET 的结果：先用户信息（email 为 None），再邮箱列表
        mock_do_get.side_effect = [
            json.dumps({
                "avatar_url": "avatar_url",
                "name": "name",
                "id": "id",
                "email": None,  # Email is private
            }),
            json.dumps([
                {
                    "email": "user@example.com",
                    "primary": True,
                    "verified": True,
                    "visibility": "private"
                }
            ])
        ]
        
        token = github_app.get_access_token_by_code('code')
        userinfo = github_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'gho_test_token')
        self.assertEqual(userinfo.openid, 'id')
        # SJQ: 私有邮箱场景下，应回退到 /user/emails 取到已验证邮箱
        self.assertEqual(userinfo.email, 'user@example.com')
        # Verify both API calls were made
        # SJQ: 断言确实发起了两次 GET（用户信息 + 邮箱列表）
        self.assertEqual(mock_do_get.call_count, 2)

    @patch("oauth.oauthmanager.FaceBookOauthManager.do_post")
    @patch("oauth.oauthmanager.FaceBookOauthManager.do_get")
    def test_facebook_login(self, mock_do_get, mock_do_post):
        """FaceBook：头像嵌在 picture.data.url 三层结构里。"""
        facebook_app = self.get_app_by_type('facebook')
        assert facebook_app
        url = facebook_app.get_authorization_url()
        self.assertTrue("facebook.com" in url)
        mock_do_post.return_value = json.dumps({
            "access_token": "access_token",
        })
        mock_do_get.return_value = json.dumps({
            "name": "name",
            "id": "id",
            "email": "email",
            "picture": {
                "data": {
                    "url": "url"
                }
            }
        })
        token = facebook_app.get_access_token_by_code('code')
        userinfo = facebook_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'access_token')

    @patch("oauth.oauthmanager.QQOauthManager.do_get", side_effect=[
        'access_token=access_token&expires_in=3600',
        'callback({"client_id":"appid","openid":"openid"} );',
        json.dumps({
            "nickname": "nickname",
            "email": "email",
            "figureurl": "figureurl",
            "openid": "openid",
        })
    ])
    def test_qq_login(self, mock_do_get):
        """QQ：三次 GET 依次换 token、取 openid（JSONP 外壳）、取用户信息。"""
        qq_app = self.get_app_by_type('qq')
        assert qq_app
        url = qq_app.get_authorization_url()
        self.assertTrue("qq.com" in url)
        # SJQ: QQ 换 token 用 GET，返回值是 querystring
        token = qq_app.get_access_token_by_code('code')
        # SJQ: 取用户信息前内部会先调 get_open_id()，因此总共三次 GET
        userinfo = qq_app.get_oauth_userinfo()
        self.assertEqual(userinfo.token, 'access_token')

    @patch("oauth.oauthmanager.WBOauthManager.do_post")
    @patch("oauth.oauthmanager.WBOauthManager.do_get")
    def test_weibo_authoriz_login_with_email(self, mock_do_get, mock_do_post):
        """有邮箱分支：回调后应自动建本地账号、完成登录，第二次登录复用同一账号。"""
        # SJQ: 模拟 token 接口返回
        mock_do_post.return_value = json.dumps({"access_token": "access_token",
                                                "uid": "uid"
                                                })
        # SJQ: 模拟用户信息（含邮箱）
        mock_user_info = {
            "avatar_large": "avatar_large",
            "screen_name": "screen_name1",
            "id": "id",
            "email": "email",
        }
        mock_do_get.return_value = json.dumps(mock_user_info)

        # SJQ: 第一步：从登录入口跳到微博授权页
        response = self.client.get('/oauth/oauthlogin?type=weibo')
        self.assertEqual(response.status_code, 302)
        self.assertTrue("api.weibo.com" in response.url)

        # SJQ: 第二步：模拟平台回调
        response = self.client.get('/oauth/authorize?type=weibo&code=code')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

        # SJQ: 回调后应已建立登录态，且用户名/邮箱来自平台数据
        user = auth.get_user(self.client)
        assert user.is_authenticated
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, mock_user_info['screen_name'])
        self.assertEqual(user.email, mock_user_info['email'])
        # SJQ: 退出登录，验证第二次登录能复用同一账号而不是重复建号
        self.client.logout()

        response = self.client.get('/oauth/authorize?type=weibo&code=code')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

        user = auth.get_user(self.client)
        assert user.is_authenticated
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, mock_user_info['screen_name'])
        self.assertEqual(user.email, mock_user_info['email'])

    @patch("oauth.oauthmanager.WBOauthManager.do_post")
    @patch("oauth.oauthmanager.WBOauthManager.do_get")
    def test_weibo_authoriz_login_without_email(self, mock_do_get, mock_do_post):
        """无邮箱分支：应跳到补全邮箱页，提交后发确认邮件，点链接后完成绑定并登录。"""
        # SJQ: 模拟 token 接口返回
        mock_do_post.return_value = json.dumps({"access_token": "access_token",
                                                "uid": "uid"
                                                })
        # SJQ: 注意这份用户信息里没有 email，因此会走补全邮箱分支
        mock_user_info = {
            "avatar_large": "avatar_large",
            "screen_name": "screen_name1",
            "id": "id",
        }
        mock_do_get.return_value = json.dumps(mock_user_info)

        response = self.client.get('/oauth/oauthlogin?type=weibo')
        self.assertEqual(response.status_code, 302)
        self.assertTrue("api.weibo.com" in response.url)

        # SJQ: 回调后应跳"补全邮箱"页而不是直接登录
        response = self.client.get('/oauth/authorize?type=weibo&code=code')

        self.assertEqual(response.status_code, 302)

        # SJQ: 从跳转地址里解析出 oauthid（形如 /oauth/requireemail/12.html）
        oauth_user_id = int(response.url.split('/')[-1].split('.')[0])
        self.assertEqual(response.url, f'/oauth/requireemail/{oauth_user_id}.html')

        # SJQ: 提交邮箱，应跳提示页（type=email 表示邮件已发出）
        response = self.client.post(response.url, {'email': 'test@gmail.com', 'oauthid': oauth_user_id})

        self.assertEqual(response.status_code, 302)
        # SJQ: 用与视图相同的算法复算签名
        sign = get_sha256(settings.SECRET_KEY +
                          str(oauth_user_id) + settings.SECRET_KEY)

        url = reverse('oauth:bindsuccess', kwargs={
            'oauthid': oauth_user_id,
        })
        self.assertEqual(response.url, f'{url}?type=email')

        # SJQ: 模拟用户点击邮件里的确认链接
        path = reverse('oauth:email_confirm', kwargs={
            'id': oauth_user_id,
            'sign': sign
        })
        response = self.client.get(path)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/oauth/bindsuccess/{oauth_user_id}.html?type=success')
        # SJQ: 确认后应已登录，且邮箱为刚才填写的值、绑定关系指向该用户
        user = auth.get_user(self.client)
        from oauth.models import OAuthUser
        oauth_user = OAuthUser.objects.get(author=user)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, mock_user_info['screen_name'])
        self.assertEqual(user.email, 'test@gmail.com')
        self.assertEqual(oauth_user.pk, oauth_user_id)
