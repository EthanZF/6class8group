# ZFH: SEO 上下文处理器测试模块，验证 seo_processor 的返回字段、缓存机制与动态值处理
"""
Test cases for blog context processors
"""
# ZFH: 导入 mock 工具，用 patch 与 Mock 替换博客设置和日志对象
from unittest.mock import patch, Mock

# ZFH: 导入 Django 测试基类、请求工厂与时间工具
from django.test import TestCase, RequestFactory
from django.utils import timezone

# ZFH: 导入用户模型、被测上下文处理器、文章分类模型与缓存工具
from accounts.models import BlogUser
from blog.context_processors import seo_processor
from blog.models import Category, Article
from djangoblog.utils import cache


# ZFH: SEO 上下文处理器测试类：覆盖返回字段、缓存命中/失效、主机名与导航数据
class SeoProcessorTest(TestCase):
    """测试SEO上下文处理器"""

    # ZFH: 构造请求工厂，并准备用户、分类、已发布页面等基础数据
    def setUp(self):
        """设置测试环境"""
        # ZFH: 使用 RequestFactory 构造不经过中间件的请求对象
        self.factory = RequestFactory()

        # 创建测试用户
        self.user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # 创建测试分类
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        # 创建测试页面
        self.page = Article.objects.create(
            title='Test Page',
            body='Test page content',
            author=self.user,
            type='p',  # 页面类型
            status='p',  # 已发布
            category=self.category
        )

        # ZFH: 清空缓存，避免上一个用例残留的 seo_processor 缓存影响本用例断言
        # 清空缓存
        cache.clear()

    # ZFH: 每个用例结束后清理缓存，保证缓存相关用例之间互不污染
    def tearDown(self):
        """清理测试环境"""
        cache.clear()

    # ZFH: 测试必需变量：调用处理器后逐一断言 20 个 SEO/导航配置键都存在于返回字典
    def test_processor_returns_required_variables(self):
        """测试上下文处理器返回必需的变量"""
        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证必需的变量
        required_keys = [
            'SITE_NAME',
            'SHOW_GOOGLE_ADSENSE',
            'GOOGLE_ADSENSE_CODES',
            'SITE_SEO_DESCRIPTION',
            'SITE_DESCRIPTION',
            'SITE_KEYWORDS',
            'SITE_BASE_URL',
            'ARTICLE_SUB_LENGTH',
            'nav_category_list',
            'nav_pages',
            'OPEN_SITE_COMMENT',
            'BEIAN_CODE',
            'ANALYTICS_CODE',
            'BEIAN_CODE_GONGAN',
            'SHOW_GONGAN_CODE',
            'CURRENT_YEAR',
            'GLOBAL_HEADER',
            'GLOBAL_FOOTER',
            'COMMENT_NEED_REVIEW',
            'COLOR_SCHEME',
        ]

        for key in required_keys:
            self.assertIn(key, result)

    # ZFH: 测试缓存写入与命中：首次调用后断言缓存键存在，二次调用返回相同基础数据
    def test_processor_caching(self):
        """测试上下文处理器的缓存机制"""
        request = self.factory.get('/')

        # 第一次调用 - 应该设置缓存
        result1 = seo_processor(request)

        # 验证缓存已设置
        cached_value = cache.get('seo_processor')
        self.assertIsNotNone(cached_value)

        # 第二次调用 - 应该从缓存获取
        result2 = seo_processor(request)

        # 验证两次调用返回相同的基础数据
        # 注意：SITE_BASE_URL和CURRENT_YEAR是动态的，可能不同
        self.assertEqual(result1['SITE_NAME'], result2['SITE_NAME'])
        self.assertEqual(result1['SITE_DESCRIPTION'], result2['SITE_DESCRIPTION'])

    # ZFH: 测试匿名请求：未登录时处理器仍应返回结果并包含 SITE_BASE_URL
    def test_processor_with_anonymous_user(self):
        """测试匿名用户访问时的上下文处理器"""
        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证返回结果
        self.assertIsNotNone(result)
        self.assertIn('SITE_BASE_URL', result)

    # ZFH: 测试 HTTPS：以 secure=True 构造请求，断言 SITE_BASE_URL 以 https:// 开头
    def test_processor_with_https_request(self):
        """测试HTTPS请求的SITE_BASE_URL"""
        request = self.factory.get('/', secure=True)
        result = seo_processor(request)

        # 验证SITE_BASE_URL包含https
        self.assertTrue(result['SITE_BASE_URL'].startswith('https://'))

    # ZFH: 测试 HTTP：普通请求的 SITE_BASE_URL 应以 http:// 开头
    def test_processor_with_http_request(self):
        """测试HTTP请求的SITE_BASE_URL"""
        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证SITE_BASE_URL包含http
        self.assertTrue(result['SITE_BASE_URL'].startswith('http://'))

    # ZFH: 测试当前年份：断言返回的 CURRENT_YEAR 等于 timezone.now().year
    def test_processor_current_year(self):
        """测试CURRENT_YEAR是当前年份"""
        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证CURRENT_YEAR是当前年份
        current_year = timezone.now().year
        self.assertEqual(result['CURRENT_YEAR'], current_year)

    # ZFH: 测试导航分类：断言 nav_category_list 非空且包含已创建的分类名
    def test_processor_nav_category_list(self):
        """测试导航分类列表"""
        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证nav_category_list包含创建的分类
        nav_categories = list(result['nav_category_list'])
        self.assertGreater(len(nav_categories), 0)

        # 验证分类在列表中
        category_names = [cat.name for cat in nav_categories]
        self.assertIn('Test Category', category_names)

    # ZFH: 测试导航页面：断言 nav_pages 非空且包含已发布页面的标题
    def test_processor_nav_pages(self):
        """测试导航页面列表"""
        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证nav_pages包含已发布的页面
        nav_pages = list(result['nav_pages'])
        self.assertGreater(len(nav_pages), 0)

        # 验证创建的页面在列表中
        page_titles = [page.title for page in nav_pages]
        self.assertIn('Test Page', page_titles)

    # ZFH: 测试草稿过滤：新增草稿页面并清缓存，断言导航不出现草稿但保留已发布页面
    def test_processor_only_shows_published_pages(self):
        """测试上下文处理器只显示已发布的页面"""
        # 创建草稿页面
        draft_page = Article.objects.create(
            title='Draft Page',
            body='Draft content',
            author=self.user,
            type='p',  # 页面类型
            status='d',  # 草稿状态
            category=self.category
        )

        # 清除缓存以确保重新查询
        cache.clear()

        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证草稿页面不在导航页面列表中
        nav_pages = list(result['nav_pages'])
        page_titles = [page.title for page in nav_pages]
        self.assertNotIn('Draft Page', page_titles)
        self.assertIn('Test Page', page_titles)

    # ZFH: 测试缓存过期：手动删除缓存键后再次调用，应重新生成且结果仍含 SITE_NAME
    def test_processor_cache_expiration(self):
        """测试缓存过期"""
        request = self.factory.get('/')

        # 第一次调用
        result1 = seo_processor(request)

        # 手动删除缓存模拟过期
        cache.delete('seo_processor')

        # 第二次调用应该重新生成缓存
        result2 = seo_processor(request)

        # 验证结果仍然正确
        self.assertIsNotNone(result2)
        self.assertIn('SITE_NAME', result2)

    # ZFH: patch 处理器内部的 get_blog_setting，用 Mock 返回自定义站点配置
    @patch('blog.context_processors.get_blog_setting')
    # ZFH: 测试自定义设置：断言输出与 Mock 的站点名、描述、关键词等配置一致
    def test_processor_with_custom_blog_settings(self, mock_get_blog_setting):
        """测试使用自定义博客设置"""
        # 模拟博客设置
        mock_setting = Mock()
        mock_setting.site_name = 'Test Blog'
        mock_setting.site_description = 'A test blog'
        mock_setting.site_seo_description = 'SEO description'
        mock_setting.site_keywords = 'test, blog'
        mock_setting.article_sub_length = 100
        mock_setting.show_google_adsense = False
        mock_setting.google_adsense_codes = ''
        mock_setting.open_site_comment = True
        mock_setting.beian_code = ''
        mock_setting.analytics_code = ''
        mock_setting.gongan_beiancode = ''
        mock_setting.show_gongan_code = False
        mock_setting.global_header = ''
        mock_setting.global_footer = ''
        mock_setting.comment_need_review = False
        mock_setting.color_scheme = 'light'

        # ZFH: 让被 patch 的设置查询固定返回上面构造的 Mock 对象
        mock_get_blog_setting.return_value = mock_setting

        # 清除缓存
        cache.clear()

        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证返回的值与模拟的设置匹配
        # ZFH: 逐项比对返回字典与模拟配置，确认设置值被正确映射到上下文变量
        self.assertEqual(result['SITE_NAME'], 'Test Blog')
        self.assertEqual(result['SITE_DESCRIPTION'], 'A test blog')
        self.assertEqual(result['SITE_SEO_DESCRIPTION'], 'SEO description')
        self.assertEqual(result['SITE_KEYWORDS'], 'test, blog')
        self.assertEqual(result['ARTICLE_SUB_LENGTH'], 100)
        self.assertEqual(result['SHOW_GOOGLE_ADSENSE'], False)

    # ZFH: 测试多主机名：循环不同 Host 发起请求，断言 SITE_BASE_URL 含对应主机名
    def test_processor_site_base_url_with_different_hosts(self):
        """测试不同主机名的SITE_BASE_URL"""
        hosts = ['example.com', 'blog.example.com', 'localhost:8000']

        for host in hosts:
            request = self.factory.get('/', HTTP_HOST=host)
            result = seo_processor(request)

            # 验证SITE_BASE_URL包含正确的主机名
            self.assertIn(host, result['SITE_BASE_URL'])

    # ZFH: 测试动态值不缓存：HTTP 与 HTTPS 两次请求应得到不同的 SITE_BASE_URL
    def test_processor_dynamic_values_not_cached(self):
        """测试动态值不被缓存（SITE_BASE_URL和CURRENT_YEAR）"""
        # 第一次请求 - HTTP
        request1 = self.factory.get('/')
        result1 = seo_processor(request1)
        site_url1 = result1['SITE_BASE_URL']

        # 第二次请求 - HTTPS（使用缓存的数据但动态值应该更新）
        request2 = self.factory.get('/', secure=True)
        result2 = seo_processor(request2)
        site_url2 = result2['SITE_BASE_URL']

        # 验证SITE_BASE_URL不同（一个是http，一个是https）
        self.assertNotEqual(site_url1, site_url2)
        self.assertTrue(site_url1.startswith('http://'))
        self.assertTrue(site_url2.startswith('https://'))

    # ZFH: 测试空设置容错：清缓存后调用处理器，即使配置为空也不应报错
    def test_processor_handles_empty_settings(self):
        """测试处理器处理空设置"""
        # 清除缓存
        cache.clear()

        request = self.factory.get('/')
        result = seo_processor(request)

        # 即使某些设置为空，处理器也应该正常工作
        self.assertIsNotNone(result)
        self.assertIn('SITE_NAME', result)

    # ZFH: patch 模块内的 logger，用于捕获缓存未命中时的日志调用
    @patch('blog.context_processors.logger')
    # ZFH: 测试缓存未命中日志：清缓存后首次调用应记录 'set processor cache'
    def test_processor_logs_cache_miss(self, mock_logger):
        """测试缓存未命中时记录日志"""
        # 清除缓存
        cache.clear()

        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证logger.info被调用
        self.assertTrue(mock_logger.info.called)
        # 验证日志消息
        call_args = str(mock_logger.info.call_args)
        self.assertIn('set processor cache', call_args)

    # ZFH: 测试多分类：再建两个分类，断言导航分类数为 3
    def test_processor_multiple_categories(self):
        """测试多个分类的情况"""
        # 创建额外的分类
        Category.objects.create(name='Category 2', slug='category-2')
        Category.objects.create(name='Category 3', slug='category-3')

        # 清除缓存
        cache.clear()

        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证所有分类都在列表中
        nav_categories = list(result['nav_category_list'])
        self.assertEqual(len(nav_categories), 3)

    # ZFH: 测试多页面：再建两个已发布页面，断言导航页面数为 3
    def test_processor_multiple_pages(self):
        """测试多个页面的情况"""
        # 创建额外的页面
        Article.objects.create(
            title='Page 2',
            body='Content 2',
            author=self.user,
            type='p',
            status='p',
            category=self.category
        )
        Article.objects.create(
            title='Page 3',
            body='Content 3',
            author=self.user,
            type='p',
            status='p',
            category=self.category
        )

        # 清除缓存
        cache.clear()

        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证所有页面都在列表中
        nav_pages = list(result['nav_pages'])
        self.assertEqual(len(nav_pages), 3)

    # ZFH: 测试排除文章：创建 type='a' 的记录，断言它不会出现在 nav_pages 中
    def test_processor_excludes_articles_from_nav_pages(self):
        """测试nav_pages不包含文章（只包含页面）"""
        # 创建一个文章
        Article.objects.create(
            title='Test Article',
            body='Article content',
            author=self.user,
            type='a',  # 文章类型
            status='p',
            category=self.category
        )

        # 清除缓存
        cache.clear()

        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证文章不在nav_pages中
        nav_pages = list(result['nav_pages'])
        page_titles = [page.title for page in nav_pages]
        self.assertNotIn('Test Article', page_titles)
        self.assertIn('Test Page', page_titles)  # 但页面应该在

    # ZFH: 测试配色方案：断言 COLOR_SCHEME 键存在且值非空
    def test_processor_color_scheme_setting(self):
        """测试COLOR_SCHEME设置"""
        request = self.factory.get('/')
        result = seo_processor(request)

        # 验证COLOR_SCHEME存在且有值
        self.assertIn('COLOR_SCHEME', result)
        self.assertIsNotNone(result['COLOR_SCHEME'])
