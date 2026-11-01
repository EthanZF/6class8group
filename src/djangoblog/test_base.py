# zfh: 可复用的测试基类与工具，提供通用测试数据创建和断言方法
"""
可复用的测试基类和工具
提供通用的测试数据创建和断言方法
"""
# zfh: 导入权限模型 Permission
from django.contrib.auth.models import Permission
# zfh: 导入测试基类 TestCase、测试客户端 Client 和请求工厂 RequestFactory
from django.test import TestCase, Client, RequestFactory
# zfh: 导入 Django 时区工具
from django.utils import timezone

# zfh: 导入自定义用户模型 BlogUser
from accounts.models import BlogUser
# zfh: 导入博客模型：文章、分类、标签、博客设置
from blog.models import Article, Category, Tag, BlogSettings
# zfh: 导入评论模型 Comment
from comments.models import Comment


# zfh: 通用测试基类，提供常用的测试数据创建方法
class BaseTestCase(TestCase):
    """
    通用测试基类
    提供常用的测试数据创建方法
    """

    # zfh: 每个测试用例执行前的初始化，创建测试客户端和各类测试数据
    def setUp(self):
        # zfh: 创建 Django 测试客户端
        self.client = Client()
        # zfh: 创建请求工厂，用于直接构造请求对象
        self.factory = RequestFactory()
        # zfh: 创建普通测试用户
        self.user = self.create_user()
        # zfh: 创建管理员测试用户
        self.admin_user = self.create_admin_user()
        # zfh: 创建测试分类
        self.category = self.create_category()
        # zfh: 创建测试标签
        self.tag = self.create_tag()
        # zfh: 创建测试文章
        self.article = self.create_article()
        # zfh: 创建博客设置
        self.blog_settings = self.create_blog_settings()

    # zfh: 创建普通用户
    def create_user(self, username='testuser', email='test@test.com', password='testpass123'):
        """创建普通用户"""
        # zfh: 通过 BlogUser 管理器创建普通用户
        user = BlogUser.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        # zfh: 返回创建好的用户对象
        return user

    # zfh: 创建管理员用户
    def create_admin_user(self, username='admin', email='admin@admin.com', password='admin123'):
        """创建管理员用户"""
        # zfh: 通过 BlogUser 管理器创建超级用户
        user = BlogUser.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        # zfh: 返回创建好的管理员对象
        return user

    # zfh: 创建员工用户
    def create_staff_user(self, username='staff', email='staff@test.com', password='staff123'):
        """创建员工用户"""
        # zfh: 创建普通用户并标记为员工
        user = BlogUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True
        )
        # zfh: 返回创建好的员工用户对象
        return user

    # zfh: 创建分类
    def create_category(self, name='测试分类'):
        """创建分类"""
        # zfh: 创建分类记录并写入创建时间和修改时间
        category = Category.objects.create(
            name=name,
            creation_time=timezone.now(),
            last_modify_time=timezone.now()
        )
        # zfh: 返回创建好的分类对象
        return category

    # zfh: 创建标签
    def create_tag(self, name='测试标签'):
        """创建标签"""
        # zfh: 创建标签记录
        tag = Tag.objects.create(name=name)
        # zfh: 返回创建好的标签对象
        return tag

    # zfh: 创建文章
    def create_article(self, title='测试文章', body='测试内容', author=None,
                      category=None, status='p', article_type='a'):
        """创建文章"""
        # zfh: 未指定作者时，优先使用当前实例的 user，否则新建一个
        if author is None:
            author = self.user if hasattr(self, 'user') else self.create_user()
        # zfh: 未指定分类时，优先使用当前实例的 category，否则新建一个
        if category is None:
            category = self.category if hasattr(self, 'category') else self.create_category()

        # zfh: 创建文章记录，写入标题、正文、作者、分类、类型和状态
        article = Article.objects.create(
            title=title,
            body=body,
            author=author,
            category=category,
            type=article_type,
            status=status
        )
        # zfh: 返回创建好的文章对象
        return article

    # zfh: 创建评论
    def create_comment(self, article=None, author=None, body='测试评论', parent=None):
        """创建评论"""
        # zfh: 未指定文章时，优先使用当前实例的 article，否则新建一篇
        if article is None:
            article = self.article if hasattr(self, 'article') else self.create_article()
        # zfh: 未指定作者时，优先使用当前实例的 user，否则新建一个
        if author is None:
            author = self.user if hasattr(self, 'user') else self.create_user()

        # zfh: 创建评论记录，写入正文、作者、所属文章和父评论
        comment = Comment.objects.create(
            body=body,
            author=author,
            article=article,
            parent_comment=parent
        )
        # zfh: 返回创建好的评论对象
        return comment

    # zfh: 创建博客设置
    def create_blog_settings(self):
        """创建博客设置"""
        # zfh: 按主键 id=1 获取博客设置，不存在则用 defaults 创建
        settings, created = BlogSettings.objects.get_or_create(
            id=1,
            defaults={
                # zfh: 站点名称
                'site_name': '测试博客',
                # zfh: 站点描述
                'site_description': '测试描述',
                # zfh: 评论是否需要审核
                'comment_need_review': False,
            }
        )
        # zfh: 返回博客设置对象
        return settings

    # zfh: 登录指定用户
    def login_user(self, user=None, password='testpass123'):
        """登录用户"""
        # zfh: 未指定用户时使用当前实例的普通用户
        if user is None:
            user = self.user
        # zfh: 用测试客户端登录并返回登录结果
        return self.client.login(username=user.username, password=password)

    # zfh: 登录管理员
    def login_admin(self):
        """登录管理员"""
        # zfh: 用管理员账号密码登录测试客户端
        return self.client.login(username='admin', password='admin123')

    # zfh: 断言响应重定向到登录页
    def assert_redirect_to_login(self, response):
        """断言重定向到登录页"""
        # zfh: 断言状态码为 302
        self.assertEqual(response.status_code, 302)
        # zfh: 断言重定向地址包含 /login/
        self.assertIn('/login/', response.url)

    # zfh: 断言权限被拒绝
    def assert_permission_denied(self, response):
        """断言权限拒绝"""
        # zfh: 断言状态码为 403 或 302
        self.assertIn(response.status_code, [403, 302])


# zfh: 视图测试混入类，提供视图测试的通用方法
class ViewTestMixin:
    """
    视图测试混入类
    提供视图测试的通用方法
    """

    # zfh: 断言 GET 访问视图成功并返回响应
    def assert_view_success(self, url, status_code=200):
        """断言视图访问成功"""
        # zfh: 用测试客户端发起 GET 请求
        response = self.client.get(url)
        # zfh: 断言响应状态码与期望一致
        self.assertEqual(response.status_code, status_code)
        # zfh: 返回响应对象
        return response

    # zfh: 断言 GET 访问视图发生重定向
    def assert_view_redirect(self, url, redirect_url=None):
        """断言视图重定向"""
        # zfh: 用测试客户端发起 GET 请求
        response = self.client.get(url)
        # zfh: 断言状态码为 302
        self.assertEqual(response.status_code, 302)
        # zfh: 指定了目标地址时进一步断言重定向目标
        if redirect_url:
            self.assertRedirects(response, redirect_url)
        # zfh: 返回响应对象
        return response

    # zfh: 断言 GET 访问视图被禁止
    def assert_view_forbidden(self, url):
        """断言视图禁止访问"""
        # zfh: 用测试客户端发起 GET 请求
        response = self.client.get(url)
        # zfh: 断言状态码为 403 或 302
        self.assertIn(response.status_code, [403, 302])
        # zfh: 返回响应对象
        return response

    # zfh: 断言 POST 请求成功
    def assert_post_success(self, url, data, status_code=200):
        """断言 POST 请求成功"""
        # zfh: 用测试客户端发起 POST 请求并提交数据
        response = self.client.post(url, data)
        # zfh: 断言响应状态码与期望一致
        self.assertEqual(response.status_code, status_code)
        # zfh: 返回响应对象
        return response

    # zfh: 断言 AJAX 请求成功
    def assert_ajax_success(self, url, data=None):
        """断言 AJAX 请求成功"""
        # zfh: 以 AJAX 请求头发起 POST 请求
        response = self.client.post(
            url,
            data or {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        # zfh: 断言状态码为 200
        self.assertEqual(response.status_code, 200)
        # zfh: 返回响应对象
        return response


# zfh: Admin 测试混入类，提供 Admin 测试的通用方法
class AdminTestMixin:
    """
    Admin 测试混入类
    提供 Admin 测试的通用方法
    """

    # zfh: 获取指定模型的 Admin 列表页等地址
    def get_admin_url(self, model, action='changelist'):
        """获取 Admin URL"""
        # zfh: 读取模型所属的应用标签
        app_label = model._meta.app_label
        # zfh: 读取模型的名称
        model_name = model._meta.model_name
        # zfh: 导入 reverse 用于反向解析 URL
        from django.urls import reverse
        # zfh: 反向解析 admin 命名空间下的对应地址
        return reverse(f'admin:{app_label}_{model_name}_{action}')

    # zfh: 获取指定对象的 Admin 修改页地址
    def get_admin_change_url(self, obj):
        """获取对象的 Admin 修改 URL"""
        # zfh: 读取对象所属模型的应用标签
        app_label = obj._meta.app_label
        # zfh: 读取对象所属模型的名称
        model_name = obj._meta.model_name
        # zfh: 导入 reverse 用于反向解析 URL
        from django.urls import reverse
        # zfh: 反向解析该对象 admin 修改页地址
        return reverse(f'admin:{app_label}_{model_name}_change', args=[obj.pk])

    # zfh: 断言管理员可以访问 Admin 页面
    def assert_admin_accessible(self, model):
        """断言管理员可以访问 Admin 页面"""
        # zfh: 取得该模型的 Admin 列表页地址
        url = self.get_admin_url(model)
        # zfh: 用测试客户端发起 GET 请求
        response = self.client.get(url)
        # zfh: 断言状态码为 200
        self.assertEqual(response.status_code, 200)
        # zfh: 返回响应对象
        return response

    # zfh: 断言普通用户无法访问 Admin 页面
    def assert_admin_forbidden_for_user(self, model):
        """断言普通用户无法访问 Admin 页面"""
        # zfh: 取得该模型的 Admin 列表页地址
        url = self.get_admin_url(model)
        # zfh: 用测试客户端发起 GET 请求
        response = self.client.get(url)
        # zfh: 断言状态码为 302 或 403
        self.assertIn(response.status_code, [302, 403])
        # zfh: 返回响应对象
        return response


# zfh: 插件测试混入类，提供插件测试的通用方法
class PluginTestMixin:
    """
    插件测试混入类
    提供插件测试的通用方法
    """

    # zfh: 构造插件钩子所需的上下文字典
    def create_plugin_context(self, **kwargs):
        """创建插件上下文"""
        # zfh: 导入 HttpRequest 用于构造请求对象
        from django.http import HttpRequest
        # zfh: 创建请求对象
        request = HttpRequest()
        # zfh: 为请求对象设置用户，优先取入参 user，其次取实例的 user
        request.user = kwargs.get('user', self.user if hasattr(self, 'user') else None)

        # zfh: 组装插件上下文，包含请求、文章和内容
        context = {
            'request': request,
            'article': kwargs.get('article', None),
            'content': kwargs.get('content', ''),
        }
        # zfh: 返回上下文字典
        return context

    # zfh: 断言指定插件钩子已注册
    def assert_plugin_hook_registered(self, plugin, hook_name):
        """断言插件钩子已注册"""
        # zfh: 导入钩子管理器
        from djangoblog.plugin_manage import hooks
        # zfh: 读取该钩名下已注册的函数列表
        registered_hooks = hooks._hooks.get(hook_name, [])
        # zfh: 断言该钩子至少注册了一个函数
        self.assertTrue(len(registered_hooks) > 0, f"No hooks registered for {hook_name}")

    # zfh: 通过环境变量模拟插件配置
    def mock_plugin_config(self, plugin_name, **config):
        """Mock 插件配置"""
        # zfh: 导入 os 用于写环境变量
        import os
        # zfh: 遍历配置项，逐项写入环境变量
        for key, value in config.items():
            # zfh: 把配置值转为字符串后写入同名环境变量
            os.environ[key] = str(value)


# zfh: 外部服务 Mock 工具类
class MockExternalService:
    """
    外部服务 Mock 工具
    提供常用外部服务的 Mock
    """

    # zfh: 静态方法，声明为类级别工具
    @staticmethod
    # zfh: 构造一个模拟的 HTTP 响应对象
    def mock_http_response(status_code=200, content='', json_data=None):
        """Mock HTTP 响应"""
        # zfh: 导入 Mock 用于生成模拟对象
        from unittest.mock import Mock
        # zfh: 创建模拟响应对象
        response = Mock()
        # zfh: 设置模拟响应的状态码
        response.status_code = status_code
        # zfh: 设置模拟响应的内容
        response.content = content
        # zfh: 传入了 JSON 数据时设置 json() 的返回值
        if json_data:
            response.json.return_value = json_data
        # zfh: 返回模拟响应对象
        return response

    # zfh: 静态方法，声明为类级别工具
    @staticmethod
    # zfh: 构造一个模拟的 Elasticsearch 响应对象
    def mock_elasticsearch_response(hits=None):
        """Mock Elasticsearch 响应"""
        # zfh: 导入 Mock 用于生成模拟对象
        from unittest.mock import Mock
        # zfh: 创建模拟响应对象
        response = Mock()
        # zfh: 设置命中列表，未传时为空列表
        response.hits = hits or []
        # zfh: 用模拟对象表示 hits.total
        response.hits.total = Mock()
        # zfh: 设置命中总数
        response.hits.total.value = len(hits) if hits else 0
        # zfh: 返回模拟响应对象
        return response

    # zfh: 静态方法，声明为类级别工具
    @staticmethod
    # zfh: 构造用于 Mock 缓存读取的 patch 对象
    def mock_cache_get(return_value=None):
        """Mock 缓存获取"""
        # zfh: 导入 patch 用于打补丁
        from unittest.mock import patch
        # zfh: 对缓存 get 方法打补丁并指定返回值
        return patch('django.core.cache.cache.get', return_value=return_value)

    # zfh: 静态方法，声明为类级别工具
    @staticmethod
    # zfh: 构造用于 Mock 缓存写入的 patch 对象
    def mock_cache_set():
        """Mock 缓存设置"""
        # zfh: 导入 patch 用于打补丁
        from unittest.mock import patch
        # zfh: 对缓存 set 方法打补丁
        return patch('django.core.cache.cache.set')
