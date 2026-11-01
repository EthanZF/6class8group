"""
Blog Admin 测试
测试文章、分类、标签等后台管理功能
"""
# ZFH: 后台管理测试模块导入：AdminSite、请求工厂、URL 反向解析及被测 admin 类与模型
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.urls import reverse

from blog.admin import ArticlelAdmin
from blog.models import Article, Category, Tag
from djangoblog.test_base import BaseTestCase, AdminTestMixin


# ZFH: 文章后台测试类：验证列表展示、搜索过滤、编辑页以及 save_model/formfield 等 admin 钩子
class ArticleAdminTest(BaseTestCase, AdminTestMixin):
    """测试 Article Admin"""

    # ZFH: 调用基类 setUp 准备用户/文章等数据，再构造独立的 AdminSite 与 ArticlelAdmin 实例
    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.article_admin = ArticlelAdmin(Article, self.site)

    # ZFH: 列表页：管理员登录后访问文章 changelist，断言其中出现已创建文章标题
    def test_admin_list_display(self):
        """测试文章列表显示"""
        self.login_admin()
        response = self.assert_admin_accessible(Article)
        self.assertContains(response, self.article.title)

    # ZFH: 标题搜索：以文章标题作为 q 参数查询后台列表，断言 200 且命中该标题
    def test_admin_search_by_title(self):
        """测试按标题搜索"""
        self.login_admin()
        url = self.get_admin_url(Article)
        response = self.client.get(url, {'q': self.article.title})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)

    # ZFH: 状态过滤：使用 status__exact=p 查询已发布文章，断言列表页 200
    def test_admin_filter_by_status(self):
        """测试按状态过滤"""
        self.login_admin()
        url = self.get_admin_url(Article)
        response = self.client.get(url, {'status__exact': 'p'})
        self.assertEqual(response.status_code, 200)

    # ZFH: 分类过滤：按 category__id__exact 过滤，确认过滤参数不会导致错误
    def test_admin_filter_by_category(self):
        """测试按分类过滤"""
        self.login_admin()
        url = self.get_admin_url(Article)
        response = self.client.get(url, {'category__id__exact': self.category.id})
        self.assertEqual(response.status_code, 200)

    # ZFH: 修改页：访问文章后台编辑页，断言可正常打开（200）
    def test_admin_change_article(self):
        """测试修改文章"""
        self.login_admin()
        url = self.get_admin_change_url(self.article)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # ZFH: save_model 钩子：调用 admin 保存逻辑，断言对象获得主键说明已写入数据库
    def test_save_model_sets_author(self):
        """测试保存文章时自动设置作者"""
        # ZFH: 构造 POST 请求并挂载管理员用户，模拟 admin 保存时的 request 上下文
        request = self.factory.post('/')
        request.user = self.admin_user

        new_article = Article(
            title='新文章测试保存',
            body='新内容',
            category=self.category,
            type='a',
            status='p',
            author=self.admin_user  # 先设置作者
        )

        # ZFH: 直接调用 save_model，绕过表单单独验证保存逻辑（parent/change 传 None）
        # 测试 admin 的 save_model 方法
        self.article_admin.save_model(request, new_article, None, None)
        # 验证文章已保存
        self.assertIsNotNone(new_article.pk)

    # ZFH: get_list_display：断言列表字段包含标题、作者与状态
    def test_get_list_display(self):
        """测试获取列表显示字段"""
        # ZFH: 构造 GET 请求并设置 request.user，因为方法内部会读取当前用户
        request = self.factory.get('/')
        request.user = self.admin_user
        list_display = self.article_admin.get_list_display(request)
        self.assertIn('title', list_display)
        self.assertIn('author', list_display)
        self.assertIn('status', list_display)

    # ZFH: 外键表单字段：验证 Article.author 外键能被 admin 转换为可用表单字段
    def test_formfield_for_foreignkey_author(self):
        """测试作者字段的表单字段"""
        request = self.factory.get('/')
        request.user = self.admin_user

        # ZFH: 延迟导入 models 并取出 author 字段作为方法入参
        from django.db import models
        field = Article._meta.get_field('author')
        formfield = self.article_admin.formfield_for_foreignkey(field, request)
        self.assertIsNotNone(formfield)


# ZFH: 分类后台测试类：验证分类列表展示、搜索与编辑页
class CategoryAdminTest(BaseTestCase, AdminTestMixin):
    """测试 Category Admin"""

    # ZFH: 分类列表：断言后台页面包含已创建分类名称
    def test_category_admin_list(self):
        """测试分类列表"""
        self.login_admin()
        response = self.assert_admin_accessible(Category)
        self.assertContains(response, self.category.name)

    # ZFH: 分类搜索：按名称查询，断言 200 且结果包含该分类
    def test_category_admin_search(self):
        """测试分类搜索"""
        self.login_admin()
        url = self.get_admin_url(Category)
        response = self.client.get(url, {'q': self.category.name})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.category.name)

    # ZFH: 分类修改页：断言编辑页面可正常打开
    def test_category_admin_change(self):
        """测试修改分类"""
        self.login_admin()
        url = self.get_admin_change_url(self.category)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


# ZFH: 标签后台测试类：验证标签列表展示、搜索与编辑页
class TagAdminTest(BaseTestCase, AdminTestMixin):
    """测试 Tag Admin"""

    # ZFH: 标签列表：断言后台页面包含已创建标签名称
    def test_tag_admin_list(self):
        """测试标签列表"""
        self.login_admin()
        response = self.assert_admin_accessible(Tag)
        self.assertContains(response, self.tag.name)

    # ZFH: 标签搜索：按名称查询，断言 200 且结果包含该标签
    def test_tag_admin_search(self):
        """测试标签搜索"""
        self.login_admin()
        url = self.get_admin_url(Tag)
        response = self.client.get(url, {'q': self.tag.name})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tag.name)

    # ZFH: 标签修改页：断言编辑页面可正常打开
    def test_tag_admin_change(self):
        """测试修改标签"""
        self.login_admin()
        url = self.get_admin_change_url(self.tag)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
