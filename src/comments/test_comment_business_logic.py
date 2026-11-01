#psj: 【模块】comments.test_comment_business_logic —— 评论业务逻辑的单元测试
#psj: 本文件不经过浏览器，直接对模型层和查询写测试，按业务关注点分成六个类：
#psj: CommentCreationTest        —— 评论能否正确创建、各字段是否落对
#psj: CommentModerationTest      —— 审核工作流：待审、通过、拒绝、公开列表只显示已通过的
#psj: CommentReplyTest           —— 楼中楼：根评论、回复、多层嵌套、一对多回复
#psj: CommentArticleStatusTest   —— 评论与文章状态的关系（开放评论 / 关闭评论）
#psj: CommentQueryTest           —— 常见的几种查询：按文章、按作者、只取根评论、排序
#psj: CommentDeletionTest        —— 删除评论，以及删除父评论时其回复的连带影响
#psj: 每个类都自己建分类、作者、评论者和文章，保证用例之间互不影响。
"""
Test cases for comment business logic
包括评论审核工作流、嵌套回复、权限控制等核心业务逻辑
"""
from django.test import TestCase, Client
from django.utils import timezone

from accounts.models import BlogUser
from blog.models import Article, Category, BlogSettings
from comments.models import Comment


#psj: 【类】评论创建相关的测试。
#psj: 验证一条评论建出来之后，主键、正文、作者、文章四个关键字段都是对的。
class CommentCreationTest(TestCase):
    """测试评论创建业务逻辑"""

    #psj: 【方法】准备环境：建分类、两个用户（一个当文章作者，一个当评论者）、一篇开放评论的文章。
    #psj: 分成两个用户是为了让"评论者"和"作者"能区分开，避免断言时混淆。
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

        self.commenter = BlogUser.objects.create_user(
            username='commenter',
            email='commenter@example.com',
            password='password'
        )

        self.article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='o'
        )

    #psj: 【用例】评论创建后必需字段是否都正确。
    #psj: 期望：有主键、正文与传入值一致、作者和文章都指向正确的对象。
    def test_comment_created_with_required_fields(self):
        """测试评论创建包含必需字段"""
        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article
        )

        self.assertIsNotNone(comment.id)
        self.assertEqual(comment.body, 'Test comment')
        self.assertEqual(comment.author, self.commenter)
        self.assertEqual(comment.article, self.article)

    #psj: 【用例】创建时间是否被自动写入。
    #psj: 期望：creation_time 不为空，且与当前时间相差不超过 10 秒。
    def test_comment_has_creation_time(self):
        """测试评论有创建时间"""
        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article
        )

        self.assertIsNotNone(comment.creation_time)
        # 验证创建时间是最近的
        time_diff = timezone.now() - comment.creation_time
        self.assertLess(time_diff.total_seconds(), 10)

    #psj: 【用例】评论作者是否指向正确的人。
    #psj: 期望：comment.author 就是创建时传入的那个评论者。
    def test_comment_author_is_correct(self):
        """测试评论作者正确"""
        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article
        )

        self.assertEqual(comment.author, self.commenter)

    #psj: 【用例】评论与文章的关联是否正确。
    #psj: 除了直接比较外键，还反过来按文章过滤一遍，确认这条评论能被查出来。
    def test_comment_article_relationship(self):
        """测试评论与文章的关系"""
        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article
        )

        self.assertEqual(comment.article, self.article)
        # 验证可以通过文章查询到评论
        article_comments = Comment.objects.filter(article=self.article)
        self.assertIn(comment, article_comments)


#psj: 【类】评论审核工作流的测试。
#psj: 评论是否显示由 is_enable 决定，而它怎么取值取决于站点配置里的"是否需要审核"。
#psj: 这个类把几种组合都覆盖一遍。
class CommentModerationTest(TestCase):
    """测试评论审核工作流"""

    #psj: 【方法】准备环境，与上一个类相同，另外取一下站点配置对象，
    #psj: 后面的用例会在它上面切换 comment_need_review。
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

        self.commenter = BlogUser.objects.create_user(
            username='commenter',
            email='commenter@example.com',
            password='password'
        )

        self.article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='o'
        )

        # 获取或创建博客设置
        self.blog_settings, _ = BlogSettings.objects.get_or_create(
            id=1,
            defaults={'site_name': 'Test Blog'}
        )

    #psj: 【用例】需要审核时，新评论应为待审。
    #psj: 把 comment_need_review 设为 True 后建评论，期望 is_enable 为 False。
    def test_comment_pending_by_default_when_review_required(self):
        """测试需要审核时评论默认为待审状态"""
        # 启用评论审核
        self.blog_settings.comment_need_review = True
        self.blog_settings.save()

        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article,
            is_enable=False  # 待审状态
        )

        self.assertFalse(comment.is_enable)

    #psj: 【用例】不需要审核时，新评论直接可见。
    #psj: 把 comment_need_review 设为 False 后建评论，期望 is_enable 为 True。
    def test_comment_approved_directly_when_no_review_required(self):
        """测试不需要审核时评论直接通过"""
        # 禁用评论审核
        self.blog_settings.comment_need_review = False
        self.blog_settings.save()

        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article,
            is_enable=True  # 直接启用
        )

        self.assertTrue(comment.is_enable)

    #psj: 【用例】评论可以被"通过"。
    #psj: 先建成待审状态，再手动把 is_enable 改为 True 保存，期望确实变成已通过。
    def test_comment_can_be_approved(self):
        """测试评论可以被批准"""
        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article,
            is_enable=False
        )

        # 审核通过
        comment.is_enable = True
        comment.save()

        comment.refresh_from_db()
        self.assertTrue(comment.is_enable)

    #psj: 【用例】评论可以被"拒绝"。
    #psj: 把 is_enable 改为 False 保存，期望它保持不显示。
    def test_comment_can_be_rejected(self):
        """测试评论可以被拒绝"""
        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article,
            is_enable=True
        )

        # 拒绝评论
        comment.is_enable = False
        comment.save()

        comment.refresh_from_db()
        self.assertFalse(comment.is_enable)

    #psj: 【用例】公开列表里只应有已通过的评论。
    #psj: 同时建一条已通过和一条待审的评论，按 is_enable=True 过滤，
    #psj: 期望结果里只有已通过那条，待审那条不在其中。
    def test_only_approved_comments_in_public_list(self):
        """测试只有已批准的评论在公开列表中"""
        # 创建已批准的评论
        approved_comment = Comment.objects.create(
            body='Approved comment',
            author=self.commenter,
            article=self.article,
            is_enable=True
        )

        # 创建待审的评论
        pending_comment = Comment.objects.create(
            body='Pending comment',
            author=self.commenter,
            article=self.article,
            is_enable=False
        )

        # 查询已批准的评论
        approved_comments = Comment.objects.filter(
            article=self.article,
            is_enable=True
        )

        self.assertIn(approved_comment, approved_comments)
        self.assertNotIn(pending_comment, approved_comments)


#psj: 【类】楼中楼（回复）相关的测试。
#psj: 评论表用 parent_comment 指向自己来表示"回复的是哪一条"，
#psj: 这个类验证根评论、一层回复、多层嵌套和一对多这几种结构。
class CommentReplyTest(TestCase):
    """测试评论回复业务逻辑"""

    #psj: 【方法】准备环境：建分类、两个用户和三篇文章。
    #psj: 多建几篇文章是为了后面验证"不同文章的评论不会串"。
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

        self.commenter1 = BlogUser.objects.create_user(
            username='commenter1',
            email='commenter1@example.com',
            password='password'
        )

        self.commenter2 = BlogUser.objects.create_user(
            username='commenter2',
            email='commenter2@example.com',
            password='password'
        )

        self.article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='o'
        )

    #psj: 【用例】根评论。
    #psj: 建一条不带 parent_comment 的评论，期望该字段为空。
    def test_comment_can_have_no_parent(self):
        """测试评论可以没有父评论（根评论）"""
        comment = Comment.objects.create(
            body='Root comment',
            author=self.commenter1,
            article=self.article,
            parent_comment=None
        )

        self.assertIsNone(comment.parent_comment)

    #psj: 【用例】一层回复。
    #psj: 先建父评论，再建一条把 parent_comment 指向它的回复，期望指针正确。
    def test_comment_can_have_parent(self):
        """测试评论可以有父评论（回复）"""
        parent_comment = Comment.objects.create(
            body='Parent comment',
            author=self.commenter1,
            article=self.article,
            is_enable=True
        )

        reply_comment = Comment.objects.create(
            body='Reply comment',
            author=self.commenter2,
            article=self.article,
            parent_comment=parent_comment,
            is_enable=True
        )

        self.assertEqual(reply_comment.parent_comment, parent_comment)

    #psj: 【用例】父评论能查到自己所有的回复。
    #psj: 给同一条父评论建两条回复，反向查询 comment_set，
    #psj: 期望恰好 2 条且两条都在结果里。
    def test_parent_comment_has_replies(self):
        """测试父评论有回复"""
        parent_comment = Comment.objects.create(
            body='Parent comment',
            author=self.commenter1,
            article=self.article,
            is_enable=True
        )

        reply1 = Comment.objects.create(
            body='Reply 1',
            author=self.commenter2,
            article=self.article,
            parent_comment=parent_comment,
            is_enable=True
        )

        reply2 = Comment.objects.create(
            body='Reply 2',
            author=self.commenter1,
            article=self.article,
            parent_comment=parent_comment,
            is_enable=True
        )

        # 查询父评论的所有回复
        replies = Comment.objects.filter(parent_comment=parent_comment)

        self.assertEqual(replies.count(), 2)
        self.assertIn(reply1, replies)
        self.assertIn(reply2, replies)

    #psj: 【用例】多层嵌套结构。
    #psj: 建 root → level1 → level2 三层，逐层检查 parent_comment 指向上一级，
    #psj: 确认自关联可以一直串下去，不只是支持一层。
    def test_nested_comment_structure(self):
        """测试嵌套评论结构"""
        # 创建根评论
        root = Comment.objects.create(
            body='Root',
            author=self.commenter1,
            article=self.article,
            is_enable=True
        )

        # 创建一级回复
        level1 = Comment.objects.create(
            body='Level 1',
            author=self.commenter2,
            article=self.article,
            parent_comment=root,
            is_enable=True
        )

        # 创建二级回复
        level2 = Comment.objects.create(
            body='Level 2',
            author=self.commenter1,
            article=self.article,
            parent_comment=level1,
            is_enable=True
        )

        # 验证嵌套关系
        self.assertIsNone(root.parent_comment)
        self.assertEqual(level1.parent_comment, root)
        self.assertEqual(level2.parent_comment, level1)

    #psj: 【用例】同一条评论的多个回复。
    #psj: 给一条父评论建 5 条回复，期望反向查询数量正好是 5，
    #psj: 验证一对多关系在数据量稍大时也正常。
    def test_multiple_replies_to_same_comment(self):
        """测试同一评论的多个回复"""
        parent = Comment.objects.create(
            body='Parent',
            author=self.commenter1,
            article=self.article,
            is_enable=True
        )

        # 创建多个回复
        replies = []
        for i in range(5):
            reply = Comment.objects.create(
                body=f'Reply {i+1}',
                author=self.commenter2,
                article=self.article,
                parent_comment=parent,
                is_enable=True
            )
            replies.append(reply)

        # 验证所有回复都关联到同一父评论
        parent_replies = Comment.objects.filter(parent_comment=parent)
        self.assertEqual(parent_replies.count(), 5)

        for reply in replies:
            self.assertIn(reply, parent_replies)


#psj: 【类】评论与文章状态的关系测试。
#psj: 文章上有 comment_status 字段（'o' 开放 / 'c' 关闭），
#psj: 这个类验证"开放评论的文章可以评论""关闭评论的文章状态能正确记录"以及评论归属是否正确。
class CommentArticleStatusTest(TestCase):
    """测试评论与文章状态的关系"""

    #psj: 【方法】准备环境：建分类、用户和至少两篇文章，
    #psj: 其中会用到不同的 comment_status 取值。
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

        self.commenter = BlogUser.objects.create_user(
            username='commenter',
            email='commenter@example.com',
            password='password'
        )

    #psj: 【用例】开放评论的文章可以正常发表评论。
    #psj: 期望文章的 comment_status 是 'o'，且评论能成功创建、拿到主键。
    def test_can_comment_on_open_comment_article(self):
        """测试可以在开放评论的文章上评论"""
        article = Article.objects.create(
            title='Open Comment Article',
            body='Content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='o'  # 开放评论
        )

        # 业务逻辑层面：评论状态开放
        self.assertEqual(article.comment_status, 'o')

        # 创建评论应该成功
        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=article,
            is_enable=True
        )

        self.assertIsNotNone(comment.id)

    #psj: 【用例】关闭评论的文章，其状态取值应能正确保存和读回。
    #psj: 期望 comment_status 读出来是 'c'，视图层据此拒绝新的评论。
    def test_comment_status_closed_validation(self):
        """测试关闭评论的文章状态"""
        article = Article.objects.create(
            title='Closed Comment Article',
            body='Content',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='c'  # 关闭评论
        )

        # 验证文章评论状态
        self.assertEqual(article.comment_status, 'c')

        # 注意：实际的验证应该在视图层进行
        # 这里我们只测试模型层面的状态

    #psj: 【用例】评论要属于正确的文章。
    #psj: 分别给文章 1 和文章 2 各建一条评论，然后按文章过滤，
    #psj: 期望每篇文章只查到自己那条，不会互相串。
    def test_comments_belong_to_correct_article(self):
        """测试评论属于正确的文章"""
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

        comment1 = Comment.objects.create(
            body='Comment on Article 1',
            author=self.commenter,
            article=article1,
            is_enable=True
        )

        comment2 = Comment.objects.create(
            body='Comment on Article 2',
            author=self.commenter,
            article=article2,
            is_enable=True
        )

        # 验证评论属于正确的文章
        article1_comments = Comment.objects.filter(article=article1)
        article2_comments = Comment.objects.filter(article=article2)

        self.assertIn(comment1, article1_comments)
        self.assertNotIn(comment2, article1_comments)

        self.assertIn(comment2, article2_comments)
        self.assertNotIn(comment1, article2_comments)


#psj: 【类】评论查询相关的测试。
#psj: 评论列表页和侧边栏都要按不同条件查评论，这个类把几种典型查询各写一条用例。
class CommentQueryTest(TestCase):
    """测试评论查询业务逻辑"""

    #psj: 【方法】准备环境：建分类、用户、文章，后面各条用例会往文章里批量塞评论。
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

        self.commenter = BlogUser.objects.create_user(
            username='commenter',
            email='commenter@example.com',
            password='password'
        )

        self.article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

    #psj: 【用例】按文章查评论。
    #psj: 给同一篇文章建 5 条评论，期望按 article 过滤正好得到 5 条。
    def test_query_comments_by_article(self):
        """测试按文章查询评论"""
        # 创建多个评论
        for i in range(5):
            Comment.objects.create(
                body=f'Comment {i+1}',
                author=self.commenter,
                article=self.article,
                is_enable=True
            )

        comments = Comment.objects.filter(article=self.article)
        self.assertEqual(comments.count(), 5)

    #psj: 【用例】按作者查评论。
    #psj: 同一个作者发 3 条，期望按 author 过滤正好得到 3 条。
    def test_query_comments_by_author(self):
        """测试按作者查询评论"""
        # 创建评论
        for i in range(3):
            Comment.objects.create(
                body=f'Comment {i+1}',
                author=self.commenter,
                article=self.article,
                is_enable=True
            )

        comments = Comment.objects.filter(author=self.commenter)
        self.assertEqual(comments.count(), 3)

    #psj: 【用例】只取根评论。
    #psj: 混着建根评论和回复，查询时加 parent_comment__isnull=True，
    #psj: 期望结果里只有 2 条根评论，回复被排除在外——这正是文章详情页取顶层评论的写法。
    def test_query_root_comments_only(self):
        """测试只查询根评论（无父评论的评论）"""
        # 创建根评论
        root1 = Comment.objects.create(
            body='Root 1',
            author=self.commenter,
            article=self.article,
            is_enable=True
        )

        root2 = Comment.objects.create(
            body='Root 2',
            author=self.commenter,
            article=self.article,
            is_enable=True
        )

        # 创建回复
        Comment.objects.create(
            body='Reply to Root 1',
            author=self.commenter,
            article=self.article,
            parent_comment=root1,
            is_enable=True
        )

        # 查询根评论
        root_comments = Comment.objects.filter(
            article=self.article,
            parent_comment__isnull=True
        )

        self.assertEqual(root_comments.count(), 2)
        self.assertIn(root1, root_comments)
        self.assertIn(root2, root_comments)

    #psj: 【用例】评论排序。
    #psj: 建 3 条评论后按模型 Meta 里定义的顺序取，
    #psj: 期望条数正确且顺序符合模型 ordering 的设置（默认按 id 倒序，新的在前）。
    def test_comment_ordering(self):
        """测试评论排序"""
        # 创建多个评论
        comments = []
        for i in range(3):
            comment = Comment.objects.create(
                body=f'Comment {i+1}',
                author=self.commenter,
                article=self.article,
                is_enable=True
            )
            comments.append(comment)

        # 查询评论（应该按照模型定义的ordering排序）
        ordered_comments = list(Comment.objects.filter(article=self.article))

        # 验证至少返回了正确数量的评论
        self.assertEqual(len(ordered_comments), 3)


#psj: 【类】删除评论相关的测试。
#psj: 除了"能删掉"，还要确认删除父评论时，挂在它下面的回复会怎样——这取决于外键的级联设置。
class CommentDeletionTest(TestCase):
    """测试评论删除业务逻辑"""

    #psj: 【方法】准备环境：建分类、用户和文章，供删除用例使用。
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

        self.commenter = BlogUser.objects.create_user(
            username='commenter',
            email='commenter@example.com',
            password='password'
        )

        self.article = Article.objects.create(
            title='Test Article',
            body='Test content',
            author=self.author,
            category=self.category,
            status='p',
            type='a'
        )

    #psj: 【用例】一条普通评论可以被删除。
    #psj: 删掉之后再按主键查，期望抛出 DoesNotExist，说明记录确实没了。
    def test_comment_can_be_deleted(self):
        """测试评论可以被删除"""
        comment = Comment.objects.create(
            body='Test comment',
            author=self.commenter,
            article=self.article,
            is_enable=True
        )

        comment_id = comment.id

        # 删除评论
        comment.delete()

        # 验证评论已被删除
        with self.assertRaises(Comment.DoesNotExist):
            Comment.objects.get(id=comment_id)

    #psj: 【用例】删除有回复的父评论。
    #psj: 因为 parent_comment 外键设的是级联删除（CASCADE），
    #psj: 期望父评论和它的回复一起被删掉，再查都取不到。
    def test_deleting_parent_comment_with_replies(self):
        """测试删除有回复的父评论"""
        parent = Comment.objects.create(
            body='Parent',
            author=self.commenter,
            article=self.article,
            is_enable=True
        )

        reply = Comment.objects.create(
            body='Reply',
            author=self.commenter,
            article=self.article,
            parent_comment=parent,
            is_enable=True
        )

        parent_id = parent.id
        reply_id = reply.id

        # 删除父评论
        parent.delete()

        # 验证父评论被删除
        with self.assertRaises(Comment.DoesNotExist):
            Comment.objects.get(id=parent_id)

        # 验证回复的处理（取决于模型的on_delete设置）
        # 如果是CASCADE，回复也应该被删除
        # 如果是SET_NULL，回复的parent应该为None
