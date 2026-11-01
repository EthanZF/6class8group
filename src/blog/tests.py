# ZFH: 集成测试模块：验证博客文章从创建、展示到搜索、归档的完整链路，覆盖视图、模板标签与工具函数
import os

# ZFH: Django 框架相关导入：配置、上传文件、管理命令、分页器、静态文件、测试工具与 URL 反向解析
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.paginator import Paginator
from django.templatetags.static import static
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

# ZFH: 项目内部模型导入：博客用户、搜索表单、博客核心模型
from accounts.models import BlogUser
from blog.forms import BlogSearchForm
from blog.models import Article, Category, Tag, SideBar, Links
from blog.templatetags.blog_tags import load_pagination_info, load_articletags, highlight_search_term, highlight_content
# ZFH: 项目工具函数与 OAuth 模型导入，供功能验证使用
from djangoblog.utils import get_current_site, get_sha256
from oauth.models import OAuthUser, OAuthConfig


# Create your tests here.

# ZFH: 文章与站点核心功能集成测试，覆盖文章详情、分类、标签、侧边栏、分页、搜索、上传与后台访问等
class ArticleTest(TestCase):
    # ZFH: setUp 初始化测试客户端 Client 与请求工厂 RequestFactory，供后续各测试方法复用
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

    # ZFH: 端到端验证文章、分类、标签、侧边栏等对象的创建及各类页面访问均返回 200
    def test_validate_article(self):
        site = get_current_site().domain
        # ZFH: 前置数据：创建超级用户作为文章作者
        user = BlogUser.objects.get_or_create(
            email="liangliangyy@gmail.com",
            username="liangliangyy")[0]
        user.set_password("liangliangyy")
        user.is_staff = True
        user.is_superuser = True
        user.save()
        # ZFH: 访问用户主页，期望 200
        response = self.client.get(user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        # ZFH: 访问后台邮件发送日志与操作日志页面，验证路由可达
        response = self.client.get('/admin/servermanager/emailsendlog/')
        response = self.client.get('admin/admin/logentry/')
        # ZFH: 前置数据：创建启用的侧边栏对象
        s = SideBar()
        s.sequence = 1
        s.name = 'test'
        s.content = 'test content'
        s.is_enable = True
        s.save()

        # ZFH: 前置数据：创建文章分类
        category = Category()
        category.name = "category"
        category.creation_time = timezone.now()
        category.last_mod_time = timezone.now()
        category.save()

        # ZFH: 前置数据：创建文章标签
        tag = Tag()
        tag.name = "nicetag"
        tag.save()

        # ZFH: 前置数据：创建一篇已发布文章
        article = Article()
        article.title = "nicetitle"
        article.body = "nicecontent"
        article.author = user
        article.category = category
        article.type = 'a'
        article.status = 'p'

        article.save()
        # ZFH: 新文章初始无标签，添加后应有一个标签
        self.assertEqual(0, article.tags.count())
        article.tags.add(tag)
        article.save()
        self.assertEqual(1, article.tags.count())

        # ZFH: 批量创建 20 篇文章作为分页与归档测试的数据基础
        for i in range(20):
            article = Article()
            article.title = "nicetitle" + str(i)
            article.body = "nicetitle" + str(i)
            article.author = user
            article.category = category
            article.type = 'a'
            article.status = 'p'
            article.save()
            article.tags.add(tag)
            article.save()
        # ZFH: 若启用 Elasticsearch，则构建索引并验证按标题搜索可访问
        from blog.documents import ELASTICSEARCH_ENABLED
        if ELASTICSEARCH_ENABLED:
            call_command("build_index")
            response = self.client.get('/search', {'q': 'nicetitle'})
            self.assertEqual(response.status_code, 200)

        # ZFH: 访问文章详情页，期望 200
        response = self.client.get(article.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        # ZFH: 文章发布后触发蜘蛛推送通知，验证通知流程不会抛异常
        from djangoblog.spider_notify import SpiderNotify
        SpiderNotify.notify(article.get_absolute_url())
        # ZFH: 访问标签页与分类页，期望 200
        response = self.client.get(tag.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.get(category.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # ZFH: 按关键词搜索，期望 200；并验证 load_articletags 返回结果非空
        response = self.client.get('/search', {'q': 'django'})
        self.assertEqual(response.status_code, 200)
        s = load_articletags(article)
        self.assertIsNotNone(s)

        # ZFH: 登录后访问归档页，期望 200
        self.client.login(username='liangliangyy', password='liangliangyy')

        response = self.client.get(reverse('blog:archives'))
        self.assertEqual(response.status_code, 200)

        # ZFH: 分别以全部文章、标签、作者、分类构造分页器，验证分页导航链接可达
        p = Paginator(Article.objects.all(), settings.PAGINATE_BY)
        self.check_pagination(p, '', '')

        p = Paginator(Article.objects.filter(tags=tag), settings.PAGINATE_BY)
        self.check_pagination(p, '分类标签归档', tag.slug)

        p = Paginator(
            Article.objects.filter(
                author__username='liangliangyy'), settings.PAGINATE_BY)
        self.check_pagination(p, '作者文章归档', 'liangliangyy')

        p = Paginator(Article.objects.filter(category=category), settings.PAGINATE_BY)
        self.check_pagination(p, '分类目录归档', category.slug)

        # ZFH: 执行搜索表单的 search 方法，验证搜索流程可运行
        f = BlogSearchForm()
        f.search()
        # self.client.login(username='liangliangyy', password='liangliangyy')
        # ZFH: 触发百度蜘蛛推送，验证通知逻辑不抛异常
        from djangoblog.spider_notify import SpiderNotify
        SpiderNotify.baidu_notify([article.get_full_url()])

        # ZFH: 验证 gravatar 头像 URL 生成函数可正常调用
        from blog.templatetags.blog_tags import gravatar_url, gravatar
        u = gravatar_url('liangliangyy@gmail.com')
        u = gravatar('liangliangyy@gmail.com')

        # ZFH: 前置数据：创建友情链接并访问友链页，期望 200
        link = Links(
            sequence=1,
            name="lylinux",
            link='https://wwww.lylinux.net')
        link.save()
        response = self.client.get('/links.html')
        self.assertEqual(response.status_code, 200)

        # ZFH: 访问 RSS 订阅源与站点地图，期望 200
        response = self.client.get('/feed/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)

        # ZFH: 访问后台删除、邮件日志与操作日志等管理页面，验证路由可达
        self.client.get("/admin/blog/article/1/delete/")
        self.client.get('/admin/servermanager/emailsendlog/')
        self.client.get('/admin/admin/logentry/')
        self.client.get('/admin/admin/logentry/1/change/')

    # ZFH: 遍历分页器所有页，验证上一页/下一页链接均可访问并返回 200
    def check_pagination(self, p, type, value):
        for page in range(1, p.num_pages + 1):
            s = load_pagination_info(p.page(page), type, value)
            self.assertIsNotNone(s)
            if s['previous_url']:
                response = self.client.get(s['previous_url'])
                self.assertEqual(response.status_code, 200)
            if s['next_url']:
                response = self.client.get(s['next_url'])
                self.assertEqual(response.status_code, 200)

    # ZFH: 验证图片上传接口：无签名应返回 403，带正确签名应返回 200
    def test_image(self):
        # ZFH: 延迟导入 requests，仅在图片上传测试真正执行时才需要该依赖
        import requests
        # ZFH: 从网络下载一张图片作为上传测试文件
        rsp = requests.get(
            'https://www.python.org/static/img/python-logo.png')
        imagepath = os.path.join(settings.BASE_DIR, 'python.png')
        # ZFH: 将网络图片写入项目根目录下的临时文件，之后以文件形式上传
        with open(imagepath, 'wb') as file:
            file.write(rsp.content)
        # ZFH: 未携带签名直接上传，期望 403 拒绝
        rsp = self.client.post('/upload')
        self.assertEqual(rsp.status_code, 403)
        # ZFH: 使用 SECRET_KEY 双重 SHA256 生成签名后上传，期望 200
        sign = get_sha256(get_sha256(settings.SECRET_KEY))
        with open(imagepath, 'rb') as file:
            imgfile = SimpleUploadedFile(
                'python.png', file.read(), content_type='image/jpg')
            form_data = {'python.png': imgfile}
            rsp = self.client.post(
                '/upload?sign=' + sign, form_data, follow=True)
            self.assertEqual(rsp.status_code, 200)
        os.remove(imagepath)
        # ZFH: 调用发送邮件与保存用户头像工具，验证其可正常执行
        from djangoblog.utils import save_user_avatar, send_email
        send_email(['qq@qq.com'], 'testTitle', 'testContent')
        save_user_avatar(
            'https://www.python.org/static/img/python-logo.png')

    # ZFH: 验证访问不存在的路径返回 404
    def test_errorpage(self):
        rsp = self.client.get('/eee')
        self.assertEqual(rsp.status_code, 404)

    # ZFH: 验证 OAuth 配置/用户数据准备以及各管理命令可正常执行
    def test_commands(self):
        user = BlogUser.objects.get_or_create(
            email="liangliangyy@gmail.com",
            username="liangliangyy")[0]
        user.set_password("liangliangyy")
        user.is_staff = True
        user.is_superuser = True
        user.save()

        # ZFH: 构造 QQ OAuth 配置对象，为管理命令提供第三方登录配置数据
        c = OAuthConfig()
        c.type = 'qq'
        c.appkey = 'appkey'
        c.appsecret = 'appsecret'
        c.save()

        # ZFH: 构造 OAuth 用户：首个用户使用静态头像路径，元数据为单行 JSON
        u = OAuthUser()
        u.type = 'qq'
        u.openid = 'openid'
        u.user = user
        u.picture = static("/blog/img/avatar.png")
        u.metadata = '''
{
"figureurl": "https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30"
}'''
        u.save()

        # ZFH: 第二个 OAuth 用户不关联本地用户且头像为完整 URL，覆盖不同元数据与头像场景
        u = OAuthUser()
        u.type = 'qq'
        u.openid = 'openid1'
        u.picture = 'https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30'
        u.metadata = '''
        {
       "figureurl": "https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30"
        }'''
        u.save()

        from blog.documents import ELASTICSEARCH_ENABLED
        if ELASTICSEARCH_ENABLED:
            call_command("build_index")
        # ZFH: 依次执行各管理命令，确认 ping_baidu/create_testdata/clear_cache 等命令可正常运行
        call_command("ping_baidu", "all")
        call_command("create_testdata")
        call_command("clear_cache")
        call_command("sync_user_avatar")
        call_command("build_search_words")


# ZFH: 搜索高亮测试类：验证标题与正文高亮过滤器及搜索页面上下文
class SearchHighlightTest(TestCase):
    """测试搜索高亮功能"""

    # ZFH: 标题高亮过滤器：覆盖基本匹配、大小写不敏感、多关键词、空查询与空文本
    def test_highlight_search_term_filter(self):
        """测试标题高亮filter"""
        # ZFH: 基本场景：小写查询词应命中并以 <mark> 标签包裹
        # 测试基本高亮
        text = "Django is a web framework"
        result = highlight_search_term(text, "django")
        self.assertIn("<mark>Django</mark>", result)
        self.assertIn("web framework", result)

        # ZFH: 大小写不敏感：查询为大写时两处 python 都应被高亮
        # 测试不区分大小写
        text = "Python and python"
        result = highlight_search_term(text, "PYTHON")
        self.assertEqual(result.count("<mark>"), 2)

        # ZFH: 多关键词：空格分隔的查询词应被分别高亮
        # 测试多个关键词
        text = "Django web framework with Python"
        result = highlight_search_term(text, "django python")
        self.assertIn("<mark>Django</mark>", result)
        self.assertIn("<mark>Python</mark>", result)

        # ZFH: 空查询：不做任何替换，原样返回文本
        # 测试空查询
        text = "Some text"
        result = highlight_search_term(text, "")
        self.assertEqual(result, text)

        # ZFH: 空文本：输入为空字符串时结果同样为空
        # 测试空文本
        result = highlight_search_term("", "query")
        self.assertEqual(result, "")

    # ZFH: 正文高亮过滤器：验证 HTML 内容去标签后插入高亮标记的逻辑
    def test_highlight_content_filter(self):
        """测试正文高亮filter"""
        # 测试HTML内容高亮
        # ZFH: 输入为含两个 Django 关键词的 HTML 段落
        html = "<p>Django is a great web framework. Django makes development easy.</p>"
        result = highlight_content(html, "django")

        # ZFH: 断言输出含高亮标记，且原始 <p> 标签已被去除
        # 应该包含高亮标记
        self.assertIn("<mark>", result)
        self.assertIn("</mark>", result)

        # HTML标签应该被去除
        self.assertNotIn("<p>", result)

        # 应该包含Django关键词（不区分大小写）
        self.assertIn("django", result.lower())

        # ZFH: 空查询时应原样返回原始 HTML 内容
        # 测试空查询
        result = highlight_content(html, "")
        self.assertEqual(result, html)

    # ZFH: 搜索页面：断言页面可访问且视图上下文正确传递查询参数
    def test_search_page_access(self):
        """测试搜索页面访问"""
        # 测试搜索页面可以正常访问
        response = self.client.get('/search', {'q': 'django'})
        self.assertEqual(response.status_code, 200)

        # ZFH: 校验上下文中的 query 与请求参数一致
        # 检查响应中是否有查询参数
        self.assertIn('query', response.context)
        self.assertEqual(response.context['query'], 'django')

    # ZFH: 中文关键词高亮：中文文本中夹杂英文关键词时仍应正确高亮
    def test_chinese_keyword_highlight(self):
        """测试中文关键词高亮"""
        text = "这是一个Django博客系统"
        result = highlight_search_term(text, "Django")
        self.assertIn("<mark>Django</mark>", result)

        # ZFH: 第二组输入：中文标题中嵌入 Django 关键词
        # 测试中文关键词
        text = "欢迎使用DjangoBlog系统"
        result = highlight_search_term(text, "Django")
        self.assertIn("<mark>Django</mark>", result)
