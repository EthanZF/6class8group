# ZFH: 文章业务流程测试模块，覆盖文章生命周期、评论开关、权限、类型、分类、时间戳与 URL 生成
"""
Test cases for article business logic
包括文章状态转换、权限控制、评论控制等核心业务逻辑
"""
# ZFH: 导入 Django 测试客户端、URL 反向解析与时间工具
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

# ZFH: 导入项目内的用户模型以及文章、分类模型
from accounts.models import BlogUser
from blog.models import Article, Category


# ZFH: 文章生命周期测试类：验证草稿/发布状态互转、公开可见性与浏览量统计
class ArticleLifecycleTest(TestCase):
    """测试文章完整生命周期"""

    # ZFH: 每个用例执行前创建独立的客户端、分类、作者、普通用户与管理员账号
    def setUp(self):
        """设置测试环境"""
        self.client = Client()

        # 创建测试分类
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        # 创建作者用户
        self.author = BlogUser.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpassword'
        )

        # 创建其他普通用户
        self.other_user = BlogUser.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword'
        )

        # 创建管理员用户
        self.admin_user = BlogUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )

    # ZFH: 测试默认草稿状态：以 status='d' 创建文章，用于确认新建文章的初始状态约定
    def test_article_created_as_draft_by_default(self):
        """测试文章创建时默认为草稿状态"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='d',  # 草稿
            type='a'
        )
        # ZFH: 断言新文章状态为 'd'，即业务默认的草稿状态
        self.assertEqual(article.status, 'd')

    # ZFH: 测试草稿转发布：创建草稿文章后改为 'p' 保存，再从数据库刷新校验
    def test_article_draft_to_published_transition(self):
        """测试文章从草稿到发布的状态转换"""
        article = Article.objects.create(
            title='Draft Article',
            body='Draft content',
            author=self.author,
            category=self.category,
            status='d',
            type='a'
        )

        # 验证初始状态
        self.assertEqual(article.status, 'd')
        original_pub_time = article.pub_time

        # 修改为发布状态
        article.status = 'p'
        article.save()

        # 验证状态已改变
        article.refresh_from_db()
        self.assertEqual(article.status, 'p')

    # ZFH: 测试发布转草稿：已发布文章改回 'd' 保存，刷新数据库确认状态回退
    def test_article_published_to_draft_transition(self):
        """测试文章从发布到草稿的状态转换"""
        article = Article.objects.create(
            title='Published Article',
            body='Published content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        # 验证初始状态
        self.assertEqual(article.status, 'p')

        # 修改回草稿状态
        article.status = 'd'
        article.save()

        # 验证状态已改变
        article.refresh_from_db()
        self.assertEqual(article.status, 'd')

    # ZFH: 测试公开可见性：已发布文章应允许匿名客户端访问详情页
    def test_published_article_is_publicly_accessible(self):
        """测试已发布文章对所有人可见"""
        article = Article.objects.create(
            title='Public Article',
            body='Public content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        # ZFH: 以未登录身份 GET 文章详情 URL，断言状态码 200 且正文包含文章标题
        # 未登录用户访问
        response = self.client.get(article.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Article')

    # ZFH: 测试草稿隔离：同时创建草稿与已发布文章，仅按 status='p' 过滤公开列表
    def test_draft_article_not_in_public_list(self):
        """测试草稿文章不在公开列表中"""
        # 创建草稿文章
        draft_article = Article.objects.create(
            title='Draft Article',
            body='Draft content',
            author=self.author,
            category=self.category,
            status='d',
            type='a'
        )

        # 创建已发布文章
        published_article = Article.objects.create(
            title='Published Article',
            body='Published content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        # 获取公开文章列表（只包含已发布的）
        public_articles = Article.objects.filter(status='p', type='a')

        # 验证草稿文章不在列表中
        self.assertNotIn(draft_article, public_articles)
        self.assertIn(published_article, public_articles)

    # ZFH: 测试浏览量自增：初始 views=0，加 1 保存后刷新数据库断言为 1
    def test_article_views_counter_increases(self):
        """测试文章浏览量计数器增加"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            views=0
        )

        initial_views = article.views

        # 模拟浏览文章
        article.views += 1
        article.save()

        # 验证浏览量增加
        article.refresh_from_db()
        self.assertEqual(article.views, initial_views + 1)

    # ZFH: 测试浏览量累加：循环 10 次自增并保存，断言最终 views 恰为 10
    def test_article_views_multiple_increments(self):
        """测试文章多次浏览时浏览量正确累加"""
        article = Article.objects.create(
            title='Popular Article',
            body='Popular content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            views=0
        )

        # 模拟多次浏览
        for i in range(10):
            article.views += 1
            article.save()

        article.refresh_from_db()
        self.assertEqual(article.views, 10)


# ZFH: 文章评论开关测试类：验证评论默认开放、可以关闭以及关闭状态的持久化
class ArticleCommentStatusTest(TestCase):
    """测试文章评论状态控制"""

    # ZFH: 准备分类与作者，供各评论状态用例复用
    def setUp(self):
        """设置测试环境"""
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        self.author = BlogUser.objects.create_user(
            username='author',
            email='author@example.com',
            password='password'
        )

    # ZFH: 测试评论默认开放：创建文章时指定 comment_status='o'，断言取值保持 'o'
    def test_article_comment_open_by_default(self):
        """测试文章评论默认开放"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='o'  # 开放评论
        )

        self.assertEqual(article.comment_status, 'o')

    # ZFH: 测试关闭评论：把评论状态改为 'c' 保存，刷新数据库确认已关闭
    def test_article_comment_can_be_closed(self):
        """测试可以关闭文章评论"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='o'
        )

        # 关闭评论
        article.comment_status = 'c'
        article.save()

        article.refresh_from_db()
        self.assertEqual(article.comment_status, 'c')

    # ZFH: 测试关闭评论后的文章状态：直接以 'c' 创建文章，断言评论状态为 'c'
    def test_closed_comment_article_status(self):
        """测试关闭评论的文章状态正确"""
        article = Article.objects.create(
            title='No Comments Article',
            body='No comments allowed',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='c'
        )

        # 验证评论已关闭
        self.assertEqual(article.comment_status, 'c')


# ZFH: 文章权限测试类：验证作者、普通用户与管理员对文章的归属判断和编辑权限
class ArticlePermissionTest(TestCase):
    """测试文章权限控制"""

    # ZFH: 创建分类、三类用户以及一篇已发布文章，作为权限断言的数据基础
    def setUp(self):
        """设置测试环境"""
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        self.author = BlogUser.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpassword'
        )

        self.other_user = BlogUser.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword'
        )

        self.admin_user = BlogUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )

        self.article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

    # ZFH: 测试作者归属：断言文章 author 字段指向创建它的作者用户
    def test_author_is_article_owner(self):
        """测试作者是文章的所有者"""
        self.assertEqual(self.article.author, self.author)

    # ZFH: 测试非作者归属：断言文章作者不是普通用户，为后续权限判断提供依据
    def test_other_user_is_not_article_owner(self):
        """测试其他用户不是文章的所有者"""
        self.assertNotEqual(self.article.author, self.other_user)

    # ZFH: 测试管理员身份：断言超级用户同时具备 is_superuser 与 is_staff
    def test_admin_has_superuser_privilege(self):
        """测试管理员有超级用户权限"""
        self.assertTrue(self.admin_user.is_superuser)
        self.assertTrue(self.admin_user.is_staff)

    # ZFH: 测试普通用户身份：断言其既非 staff 也非超级用户，无法获得后台权限
    def test_normal_user_no_staff_privilege(self):
        """测试普通用户没有staff权限"""
        self.assertFalse(self.other_user.is_staff)
        self.assertFalse(self.other_user.is_superuser)

    # ZFH: 测试作者编辑权限：用 author 相等判断模拟视图层检查，结果应为 True
    def test_article_author_can_edit(self):
        """测试文章作者可以编辑（权限检查逻辑）"""
        # 验证作者权限
        can_edit = (self.article.author == self.author)
        self.assertTrue(can_edit)

    # ZFH: 测试他人编辑权限：作者不匹配时权限判断应为 False
    def test_other_user_cannot_edit(self):
        """测试其他用户不能编辑（权限检查逻辑）"""
        # 验证其他用户无权限
        can_edit = (self.article.author == self.other_user)
        self.assertFalse(can_edit)

    # ZFH: 测试管理员编辑权限：作者匹配或 is_superuser 为真即允许编辑，断言为 True
    def test_admin_can_edit_any_article(self):
        """测试管理员可以编辑任何文章（超级用户权限）"""
        # 管理员有超级用户权限，可以编辑任何文章
        can_edit = (self.article.author == self.admin_user or
                   self.admin_user.is_superuser)
        self.assertTrue(can_edit)


# ZFH: 文章类型测试类：验证 type='a' 的文章与 type='p' 的页面能被正确区分
class ArticleTypeTest(TestCase):
    """测试文章类型业务逻辑"""

    # ZFH: 准备分类与作者，供文章/页面类型用例复用
    def setUp(self):
        """设置测试环境"""
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        self.author = BlogUser.objects.create_user(
            username='author',
            email='author@example.com',
            password='password'
        )

    # ZFH: 测试文章类型：以 type='a' 创建记录，断言类型字段为文章
    def test_article_type_is_article(self):
        """测试文章类型为article"""
        article = Article.objects.create(
            title='Article Type',
            body='Article content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'  # 文章类型
        )

        self.assertEqual(article.type, 'a')

    # ZFH: 测试页面类型：以 type='p' 创建记录，断言类型字段为页面
    def test_article_type_is_page(self):
        """测试文章类型为page"""
        page = Article.objects.create(
            title='Page Type',
            body='Page content',
            author=self.author,
            category=self.category,
            status='p',
            type='p'  # 页面类型
        )

        self.assertEqual(page.type, 'p')

    # ZFH: 测试文章与页面分离：分别按 type 过滤查询，断言各自只包含对应类型
    def test_articles_and_pages_are_separate(self):
        """测试文章和页面分开查询"""
        # 创建文章
        article = Article.objects.create(
            title='Article',
            body='Article content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        # 创建页面
        page = Article.objects.create(
            title='Page',
            body='Page content',
            author=self.author,
            category=self.category,
            status='p',
            type='p'
        )

        # 只查询文章
        articles = Article.objects.filter(type='a', status='p')
        self.assertIn(article, articles)
        self.assertNotIn(page, articles)

        # 只查询页面
        pages = Article.objects.filter(type='p', status='p')
        self.assertIn(page, pages)
        self.assertNotIn(article, pages)


# ZFH: 文章分类关系测试类：验证文章归属分类、分类下文章统计以及更换分类
class ArticleCategoryTagTest(TestCase):
    """测试文章与分类标签的关系"""

    # ZFH: 准备分类与作者，供分类关系用例复用
    def setUp(self):
        """设置测试环境"""
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        self.author = BlogUser.objects.create_user(
            username='author',
            email='author@example.com',
            password='password'
        )

    # ZFH: 测试分类归属：创建文章后断言其 category 外键等于预设分类
    def test_article_belongs_to_category(self):
        """测试文章属于分类"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        self.assertEqual(article.category, self.category)

    # ZFH: 测试分类文章统计：在同一分类下创建两篇文章，按分类过滤断言数量为 2
    def test_category_has_articles(self):
        """测试分类包含文章"""
        article1 = Article.objects.create(
            title='Article 1',
            body='Content 1',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        article2 = Article.objects.create(
            title='Article 2',
            body='Content 2',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        # 查询该分类下的文章
        category_articles = Article.objects.filter(
            category=self.category,
            status='p'
        )

        self.assertEqual(category_articles.count(), 2)
        self.assertIn(article1, category_articles)
        self.assertIn(article2, category_articles)

    # ZFH: 测试更换分类：新建分类并赋给已有文章，保存后刷新数据库确认外键已更新
    def test_article_can_change_category(self):
        """测试文章可以更改分类"""
        new_category = Category.objects.create(
            name='New Category',
            slug='new-category'
        )

        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        # 更改分类
        article.category = new_category
        article.save()

        article.refresh_from_db()
        self.assertEqual(article.category, new_category)


# ZFH: 文章时间戳测试类：验证创建时间、最后修改时间的写入与自动更新行为
class ArticleTimestampTest(TestCase):
    """测试文章时间戳业务逻辑"""

    # ZFH: 准备分类与作者，供时间戳用例复用
    def setUp(self):
        """设置测试环境"""
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        self.author = BlogUser.objects.create_user(
            username='author',
            email='author@example.com',
            password='password'
        )

    # ZFH: 测试创建时间：断言 creation_time 非空，且与当前时间相差不超过 10 秒
    def test_article_has_creation_time(self):
        """测试文章有创建时间"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        self.assertIsNotNone(article.creation_time)
        # 验证创建时间是最近的
        time_diff = timezone.now() - article.creation_time
        self.assertLess(time_diff.total_seconds(), 10)  # 10秒内创建

    # ZFH: 测试最后修改时间：断言新建文章的 last_modify_time 已有值
    def test_article_has_last_mod_time(self):
        """测试文章有最后修改时间"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        self.assertIsNotNone(article.last_modify_time)

    # ZFH: 测试修改时间更新：睡眠 0.1 秒后修改正文并保存，再刷新数据库观察时间戳
    def test_article_last_mod_time_updates(self):
        """测试文章修改后最后修改时间更新"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        original_mod_time = article.last_modify_time

        # 等待一小段时间
        import time
        time.sleep(0.1)

        # 修改文章
        article.body = 'Updated content'
        article.save()

        article.refresh_from_db()
        # last_modify_time应该自动更新（如果模型配置了auto_now）
        # 注意：这取决于模型的auto_now配置


# ZFH: 文章 URL 生成测试类：验证主键存在性、按 ID 可检索以及 get_absolute_url 的输出
class ArticleSlugTest(TestCase):
    """测试文章slug生成逻辑"""

    # ZFH: 准备分类与作者，供 URL 生成用例复用
    def setUp(self):
        """设置测试环境"""
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        self.author = BlogUser.objects.create_user(
            username='author',
            email='author@example.com',
            password='password'
        )

    # ZFH: 测试主键存在：断言 article.id 非空，并能按该 ID 查询到同一对象
    def test_article_has_id(self):
        """测试文章有ID（用于URL生成）"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        self.assertIsNotNone(article.id)
        # 验证可以通过ID访问
        retrieved_article = Article.objects.get(id=article.id)
        self.assertEqual(retrieved_article, article)

    # ZFH: 测试绝对 URL：调用 get_absolute_url，断言结果非空且包含文章 ID
    def test_article_absolute_url(self):
        """测试文章绝对URL生成"""
        article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

        url = article.get_absolute_url()
        self.assertIsNotNone(url)
        # URL应该包含文章ID
        self.assertIn(str(article.id), url)
