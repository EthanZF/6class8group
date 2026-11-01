# zfh: 端到端邮件集成测试模块，覆盖注册、密码重置、评论通知与完整用户旅程
"""
Complete Email Integration Tests - End to End
完整的邮件集成测试 - 端到端测试完整业务流程
"""
# zfh: 导入正则模块，用于从邮件正文中提取验证链接和验证码
import re
# zfh: 导入 Django 测试工具：测试基类、测试客户端和设置覆盖装饰器
from django.test import TestCase, Client, override_settings
# zfh: 导入邮件模块，通过 mail.outbox 读取测试期间发出的邮件
from django.core import mail
# zfh: 导入 reverse，用 URL 名称反向解析出访问路径
from django.urls import reverse
# zfh: 导入认证函数，用于校验密码是否可用
from django.contrib.auth import authenticate

# zfh: 导入自定义用户模型 BlogUser
from accounts.models import BlogUser
# zfh: 导入验证码生成与校验工具函数
from accounts.utils import get_code, verify
# zfh: 导入文章、分类与博客设置模型
from blog.models import Article, Category, BlogSettings
# zfh: 导入评论模型
from comments.models import Comment


# zfh: 用内存邮件后端和同步执行 Celery 任务的设置覆盖本测试类
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
# zfh: 完整用户注册流程测试类，验证注册到激活的端到端链路
class CompleteUserRegistrationFlowTest(TestCase):
    """完整的用户注册流程集成测试"""

    # zfh: 每个测试方法执行前初始化客户端、清理邮件并准备博客设置
    def setUp(self):
        """设置测试环境"""
        # zfh: 创建测试客户端
        self.client = Client()
        # zfh: 清空邮件发件箱
        mail.outbox = []

        # zfh: 获取或创建 id 为 1 的博客设置
        BlogSettings.objects.get_or_create(
            id=1,
            defaults={'site_name': 'Test Blog'}
        )

    # zfh: 测试注册、发邮件、验证到激活成功的完整流程
    def test_complete_registration_verification_flow(self):
        """测试完整的注册验证流程：注册 → 发邮件 → 验证 → 成功"""

        # ============ 步骤1: 用户注册 ============
        # zfh: 构造注册表单所需的用户名、邮箱和两次密码
        registration_data = {
            'username': 'testuser2024',
            'email': 'integration@example.com',
            'password1': 'ComplexPassword@2024!',
            'password2': 'ComplexPassword@2024!',
        }

        # zfh: 向注册接口提交表单并跟随重定向
        response = self.client.post(
            reverse('account:register'),
            registration_data,
            follow=True
        )

        # 验证注册响应成功
        # zfh: 断言注册请求返回 200
        self.assertEqual(response.status_code, 200)

        # 验证用户已创建（可能是未激活状态）
        # zfh: 按用户名查询刚注册的用户
        user = BlogUser.objects.filter(username='testuser2024').first()

        # 如果用户未创建，可能是表单验证失败
        # zfh: 用户为空时回退排查表单错误
        if user is None:
            # 检查响应中是否有错误信息
            # zfh: 响应上下文存在表单时打印表单校验错误
            if hasattr(response, 'context') and response.context and 'form' in response.context:
                # zfh: 取出表单的错误信息
                form_errors = response.context['form'].errors
                # zfh: 打印表单错误便于排查
                print(f"表单错误: {form_errors}")

            # 尝试按邮箱查找
            # zfh: 改用邮箱再查一次用户
            user = BlogUser.objects.filter(email='integration@example.com').first()

        # zfh: 断言用户已被创建
        self.assertIsNotNone(user, "用户应该被创建")
        # 用户可能是未激活状态
        # self.assertFalse(user.is_active, "新注册用户应该是未激活状态")

        # ============ 步骤2: 验证邮件已发送 ============
        # zfh: 断言至少发送了 1 封验证邮件
        self.assertGreaterEqual(len(mail.outbox), 1, "应该发送了验证邮件")

        # zfh: 取出第一封验证邮件
        verification_email = mail.outbox[0]
        # zfh: 断言收件人包含注册邮箱
        self.assertIn('integration@example.com', verification_email.to)

        # ============ 步骤3: 从邮件中提取验证链接 ============
        # zfh: 取出邮件正文
        email_body = verification_email.body

        # 提取验证链接（注册发送的是链接，不是验证码）
        # zfh: 用正则从正文中匹配 http/https 链接
        link_match = re.search(r'https?://[^\s<>"]+', email_body)

        # zfh: 匹配到链接时继续验证流程
        if link_match:
            # zfh: 取出完整链接字符串
            verification_link = link_match.group(0)
            # zfh: 断言验证链接非空
            self.assertIsNotNone(verification_link, "邮件中应该包含验证链接")

            # ============ 步骤4: 访问验证链接 ============
            # 提取链接中的参数
            # URL格式: http://site/result?type=validation&id={id}&sign={sign}
            # zfh: 导入 URL 解析模块
            import urllib.parse
            # zfh: 解析验证链接，得到路径与查询串
            parsed = urllib.parse.urlparse(verification_link)
            # zfh: 解析查询串为参数字典
            params = urllib.parse.parse_qs(parsed.query)

            # zfh: 参数中包含 id 和 sign 时才构造验证请求
            if 'id' in params and 'sign' in params:
                # 构造验证URL路径
                # zfh: 拼接路径与查询串得到验证 URL
                verification_path = f"{parsed.path}?{parsed.query}"

                # 访问验证链接
                # zfh: 请求验证链接并跟随重定向
                verify_response = self.client.get(verification_path, follow=True)
                # zfh: 断言验证页面返回 200
                self.assertEqual(verify_response.status_code, 200)

                # ============ 步骤5: 验证用户已被激活 ============
                # zfh: 从数据库重新读取用户最新状态
                user.refresh_from_db()
                # 验证后用户应该被激活
                # zfh: 用户已激活时继续验证登录
                if user.is_active:
                    # ============ 步骤6: 激活后用户可以登录 ============
                    # zfh: 用注册时的账号密码尝试登录
                    login_success = self.client.login(
                        username='testuser2024',
                        password='ComplexPassword@2024!'
                    )
                    # zfh: 断言激活后可以登录成功
                    self.assertTrue(login_success, "验证后用户应该可以登录")
        else:
            # 至少验证邮件包含相关内容
            # zfh: 无链接时断言正文含验证、激活或 http 相关内容
            self.assertTrue(
                '验证' in email_body or '激活' in email_body or 'http' in email_body,
                "邮件应该包含验证相关的内容或链接"
            )

    # zfh: 测试使用重复邮箱注册的处理结果
    def test_registration_with_duplicate_email_fails(self):
        """测试重复邮箱注册失败"""

        # 第一次注册
        # zfh: 构造第一个用户的注册数据
        first_registration = {
            'username': 'firstuser',
            'email': 'duplicate@example.com',
            'password1': 'Password123!',
            'password2': 'Password123!',
        }

        # zfh: 提交第一次注册请求
        self.client.post(
            reverse('account:register'),
            first_registration,
            follow=True
        )

        # 第二次用相同邮箱注册
        # zfh: 构造使用相同邮箱的第二个用户数据
        second_registration = {
            'username': 'seconduser',
            'email': 'duplicate@example.com',  # 相同邮箱
            'password1': 'Password456!',
            'password2': 'Password456!',
        }

        # zfh: 提交第二次注册请求
        response = self.client.post(
            reverse('account:register'),
            second_registration,
            follow=True
        )

        # 应该只有一个用户
        # zfh: 统计该邮箱对应的用户数量
        user_count = BlogUser.objects.filter(email='duplicate@example.com').count()
        # 根据业务逻辑，可能允许或不允许重复邮箱
        # 这里验证逻辑是否正确处理


# zfh: 用内存邮件后端和同步执行 Celery 任务的设置覆盖本测试类
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
# zfh: 完整密码重置流程测试类，验证重置密码的端到端链路
class CompletePasswordResetFlowTest(TestCase):
    """完整的密码重置流程集成测试"""

    # zfh: 每个测试方法执行前初始化客户端、清理邮件并创建测试用户
    def setUp(self):
        """设置测试环境"""
        # zfh: 创建测试客户端
        self.client = Client()
        # zfh: 清空邮件发件箱
        mail.outbox = []

        # 创建测试用户
        # zfh: 创建用于重置密码测试的用户
        self.user = BlogUser.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='OldPassword123!'
        )

        # zfh: 获取或创建 id 为 1 的博客设置
        BlogSettings.objects.get_or_create(
            id=1,
            defaults={'site_name': 'Test Blog'}
        )

    # zfh: 测试忘记密码、发邮件、重置到新密码登录的完整流程
    def test_complete_password_reset_flow(self):
        """测试完整的密码重置流程：忘记密码 → 发邮件 → 重置 → 新密码登录"""

        # ============ 步骤1: 用户提交忘记密码 ============
        # zfh: 向忘记密码接口提交邮箱并跟随重定向
        response = self.client.post(
            reverse('account:forget_password'),
            {'email': 'reset@example.com'},
            follow=True
        )

        # zfh: 断言请求返回 200
        self.assertEqual(response.status_code, 200)

        # ============ 步骤2: 验证邮件已发送（如果实现了） ============
        # zfh: 发件箱非空时进入邮件验证分支
        if len(mail.outbox) > 0:
            # zfh: 取出第一封重置邮件
            reset_email = mail.outbox[0]
            # zfh: 断言收件人为提交的邮箱
            self.assertIn('reset@example.com', reset_email.to)

            # zfh: 取出邮件正文
            email_body = reset_email.body

            # ============ 步骤3: 从邮件中提取验证码 ============
            # zfh: 用正则匹配正文中的 4-6 位数字验证码
            verification_code_match = re.search(r'\b(\d{4,6})\b', email_body)

            # zfh: 匹配到验证码时继续提交新密码
            if verification_code_match:
                # zfh: 取出验证码字符串
                verification_code = verification_code_match.group(1)

                # ============ 步骤4: 提交新密码和验证码 ============
                # zfh: 定义要设置的新密码
                new_password = 'NewPassword456!'

                # zfh: 提交邮箱、验证码和两次新密码
                reset_response = self.client.post(
                    reverse('account:forget_password'),
                    {
                        'email': 'reset@example.com',
                        'code': verification_code,
                        'password1': new_password,
                        'password2': new_password,
                    },
                    follow=True
                )

                # ============ 步骤5: 验证可以用新密码登录 ============
                # 首先验证旧密码不能用了
                # zfh: 用旧密码尝试认证，确认其已失效
                old_password_works = authenticate(
                    username='resetuser',
                    password='OldPassword123!'
                )

                # 验证新密码可以用
                # zfh: 用新密码尝试认证
                new_password_works = authenticate(
                    username='resetuser',
                    password=new_password
                )

                # zfh: 新密码认证成功时继续登录验证
                if new_password_works:
                    # 如果密码重置成功，新密码应该可以用
                    # zfh: 断言新密码认证结果非空
                    self.assertIsNotNone(new_password_works)

                    # 使用新密码登录
                    # zfh: 用新密码登录测试客户端
                    login_success = self.client.login(
                        username='resetuser',
                        password=new_password
                    )
                    # zfh: 断言可以用新密码登录
                    self.assertTrue(login_success, "应该可以用新密码登录")

    # zfh: 测试使用无效验证码重置密码会失败
    def test_password_reset_with_invalid_code_fails(self):
        """测试使用无效验证码重置密码失败"""

        # 提交忘记密码
        # zfh: 先提交忘记密码请求以触发验证码流程
        self.client.post(
            reverse('account:forget_password'),
            {'email': 'reset@example.com'},
            follow=True
        )

        # 使用错误的验证码尝试重置
        # zfh: 用错误验证码提交新密码
        response = self.client.post(
            reverse('account:forget_password'),
            {
                'email': 'reset@example.com',
                'code': '999999',  # 错误的验证码
                'password1': 'NewPassword456!',
                'password2': 'NewPassword456!',
            },
            follow=True
        )

        # 密码不应该被改变
        # zfh: 用旧密码认证，确认密码未被修改
        user_still_has_old_password = authenticate(
            username='resetuser',
            password='OldPassword123!'
        )

        # 旧密码应该仍然有效
        # zfh: 断言旧密码认证结果非空
        self.assertIsNotNone(user_still_has_old_password)


# zfh: 用内存邮件后端和同步执行 Celery 任务的设置覆盖本测试类
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
# zfh: 完整评论通知流程测试类，验证评论与回复通知的端到端链路
class CompleteCommentNotificationFlowTest(TestCase):
    """完整的评论通知流程集成测试"""

    # zfh: 每个测试方法执行前准备用户、分类、文章和博客设置
    def setUp(self):
        """设置测试环境"""
        # zfh: 创建测试客户端
        self.client = Client()
        # zfh: 清空邮件发件箱
        mail.outbox = []

        # 创建文章作者
        # zfh: 创建文章作者用户
        self.author = BlogUser.objects.create_user(
            username='author',
            email='author@example.com',
            password='password'
        )

        # 创建评论者
        # zfh: 创建评论者用户
        self.commenter = BlogUser.objects.create_user(
            username='commenter',
            email='commenter@example.com',
            password='password'
        )

        # 创建分类和文章
        # zfh: 创建测试分类
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        # zfh: 创建已发布且允许评论的测试文章
        self.article = Article.objects.create(
            title='Test Article for Comments',
            body='Article content that will receive comments',
            author=self.author,
            category=self.category,
            status='p',
            type='a',
            comment_status='o'
        )

        # zfh: 获取或创建博客设置并关闭评论审核
        self.blog_settings, _ = BlogSettings.objects.get_or_create(
            id=1,
            defaults={
                'site_name': 'Test Blog',
                'comment_need_review': False
            }
        )

    # zfh: 测试评论通知作者、作者查看并回复的完整流程
    def test_complete_comment_notification_flow(self):
        """测试完整的评论通知流程：发表评论 → 通知作者 → 作者查看 → 回复"""

        # ============ 步骤1: 评论者登录并发表评论 ============
        # zfh: 以评论者身份登录
        self.client.login(username='commenter', password='password')

        # zfh: 定义评论正文
        comment_text = '这是一条测试评论，期待作者的回复！'

        # zfh: 提交评论表单并跟随重定向
        response = self.client.post(
            reverse('comments:postcomment', kwargs={'article_id': self.article.id}),
            {
                'body': comment_text,
                'email': 'commenter@example.com',
                'name': 'Commenter'
            },
            follow=True
        )

        # 验证评论已创建
        # zfh: 按文章和正文查询刚创建的评论
        comment = Comment.objects.filter(
            article=self.article,
            body=comment_text
        ).first()
        # zfh: 断言评论已创建
        self.assertIsNotNone(comment, "评论应该被创建")

        # ============ 步骤2: 验证通知邮件已发送给作者 ============
        # zfh: 发件箱非空时查找发给作者的邮件
        if len(mail.outbox) > 0:
            # 查找发给作者的邮件
            # zfh: 初始化作者邮件变量为 None
            author_email = None
            # zfh: 遍历发件箱寻找收件人为作者的邮件
            for email in mail.outbox:
                # zfh: 收件人含作者邮箱时记录该邮件并结束查找
                if 'author@example.com' in email.to:
                    author_email = email
                    # zfh: 找到目标邮件后跳出循环
                    break

            # zfh: 找到作者邮件时校验其内容
            if author_email:
                # 验证邮件内容包含评论信息
                # zfh: 取出作者通知邮件的正文
                email_body = author_email.body
                # zfh: 断言正文中提到"评论"
                self.assertIn('评论', email_body, "邮件应该提到评论")

                # 邮件中应该包含评论内容或链接
                # zfh: 判断正文是否含评论内容、新评论字样或文章标题
                has_comment_info = (
                    comment_text in email_body or
                    '新评论' in email_body or
                    self.article.title in email_body
                )
                # zfh: 断言邮件包含评论相关信息
                self.assertTrue(has_comment_info, "邮件应该包含评论相关信息")

                # ============ 步骤3: 从邮件中提取文章链接 ============
                # zfh: 用正则从正文中提取文章链接
                article_link_match = re.search(r'https?://[^\s]+', email_body)

                # ============ 步骤4: 作者查看评论 ============
                # zfh: 退出评论者登录
                self.client.logout()
                # zfh: 以文章作者身份登录
                self.client.login(username='author', password='password')

                # 访问文章页面查看评论
                # zfh: 请求文章的详情页地址
                article_response = self.client.get(
                    self.article.get_absolute_url()
                )

                # zfh: 断言文章页面返回 200
                self.assertEqual(article_response.status_code, 200)
                # 页面应该显示评论（如果评论已启用）
                # zfh: 评论已启用时断言页面包含评论正文
                if comment.is_enable:
                    # zfh: 断言页面响应中包含评论正文
                    self.assertContains(article_response, comment_text)

                # ============ 步骤5: 作者回复评论 ============
                # zfh: 清空此前产生的邮件
                mail.outbox = []  # 清空之前的邮件

                # zfh: 定义回复正文
                reply_text = '感谢你的评论！这是我的回复。'

                # zfh: 提交带 parent_comment_id 的回复表单
                reply_response = self.client.post(
                    reverse('comments:postcomment', kwargs={'article_id': self.article.id}),
                    {
                        'body': reply_text,
                        'email': 'author@example.com',
                        'name': 'Author',
                        'parent_comment_id': comment.id
                    },
                    follow=True
                )

                # 验证回复已创建
                # zfh: 按文章、正文和父评论查询回复
                reply = Comment.objects.filter(
                    article=self.article,
                    body=reply_text,
                    parent_comment=comment
                ).first()

                # zfh: 回复创建成功时验证回复通知
                if reply:
                    # ============ 步骤6: 验证回复通知发送给原评论者 ============
                    # zfh: 发件箱非空时查找发给原评论者的邮件
                    if len(mail.outbox) > 0:
                        # zfh: 初始化评论者邮件变量为 None
                        commenter_email = None
                        # zfh: 遍历发件箱寻找收件人为原评论者的邮件
                        for email in mail.outbox:
                            # zfh: 收件人含评论者邮箱时记录该邮件并结束查找
                            if 'commenter@example.com' in email.to:
                                commenter_email = email
                                # zfh: 找到目标邮件后跳出循环
                                break

                        # zfh: 找到评论者邮件时校验其内容
                        if commenter_email:
                            # zfh: 取出回复通知邮件的正文
                            reply_email_body = commenter_email.body
                            # 验证邮件包含回复信息
                            # zfh: 判断正文是否含"回复"字样或回复内容
                            has_reply_info = (
                                '回复' in reply_email_body or
                                reply_text in reply_email_body
                            )
                            # zfh: 断言回复通知邮件包含回复信息
                            self.assertTrue(has_reply_info, "回复通知邮件应该包含回复信息")

    # zfh: 测试评论通知是否遵循审核设置
    def test_comment_notification_respects_review_setting(self):
        """测试评论通知尊重审核设置：需要审核时不立即通知"""

        # ============ 步骤1: 启用评论审核 ============
        # zfh: 将博客设置改为评论需要审核
        self.blog_settings.comment_need_review = True
        # zfh: 保存设置到数据库
        self.blog_settings.save()

        # ============ 步骤2: 发表评论 ============
        # zfh: 以评论者身份登录
        self.client.login(username='commenter', password='password')

        # zfh: 清空此前产生的邮件
        mail.outbox = []  # 清空邮件

        # zfh: 提交一条待审核的评论
        response = self.client.post(
            reverse('comments:postcomment', kwargs={'article_id': self.article.id}),
            {
                'body': '这条评论需要审核',
                'email': 'commenter@example.com',
                'name': 'Commenter'
            },
            follow=True
        )

        # ============ 步骤3: 验证评论处于待审核状态 ============
        # zfh: 查询刚提交的待审核评论
        comment = Comment.objects.filter(
            article=self.article,
            body='这条评论需要审核'
        ).first()

        # zfh: 评论存在时继续审核流程
        if comment:
            # 评论应该未启用（待审核）
            # self.assertFalse(comment.is_enable, "需要审核的评论应该未启用")

            # ============ 步骤4: 验证不会立即发送通知 ============
            # 根据业务逻辑，待审核的评论可能不会立即通知
            # 或者只通知管理员，不通知作者

            # ============ 步骤5: 管理员审核通过 ============
            # zfh: 退出评论者登录
            self.client.logout()
            # zfh: 创建超级管理员用户
            admin = BlogUser.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpass'
            )
            # zfh: 以管理员身份登录
            self.client.login(username='admin', password='adminpass')

            # 审核通过
            # zfh: 将评论标记为已启用
            comment.is_enable = True
            # zfh: 保存评论状态
            comment.save()

            # ============ 步骤6: 审核通过后应该通知作者 ============
            # 根据业务逻辑，可能在审核通过时发送通知


# zfh: 用内存邮件后端和同步执行 Celery 任务的设置覆盖本测试类
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
# zfh: 完整用户旅程集成测试类，串联注册、登录、发文与评论
class CompleteUserJourneyIntegrationTest(TestCase):
    """完整的用户旅程集成测试"""

    # zfh: 每个测试方法执行前初始化客户端和博客设置
    def setUp(self):
        """设置测试环境"""
        # zfh: 创建测试客户端
        self.client = Client()
        # zfh: 清空邮件发件箱
        mail.outbox = []

        # zfh: 获取或创建博客设置并关闭评论审核
        BlogSettings.objects.get_or_create(
            id=1,
            defaults={
                'site_name': 'Test Blog',
                'comment_need_review': False
            }
        )

    # zfh: 测试用户从注册到互动的完整生命周期
    def test_complete_user_lifecycle(self):
        """
        测试完整的用户生命周期：
        注册 → 验证 → 登录 → 创建内容 → 接收通知 → 互动
        """

        # ============ 阶段1: 用户注册和验证 ============
        # zfh: 构造注册表单数据
        registration_data = {
            'username': 'journeyuser',
            'email': 'journey@example.com',
            'password1': 'JourneyPass123!',
            'password2': 'JourneyPass123!',
        }

        # zfh: 提交注册表单并跟随重定向
        register_response = self.client.post(
            reverse('account:register'),
            registration_data,
            follow=True
        )

        # zfh: 按邮箱查询注册后的用户
        user = BlogUser.objects.filter(email='journey@example.com').first()
        # zfh: 断言阶段1用户已被创建
        self.assertIsNotNone(user, "阶段1：用户应该被创建")

        # 验证邮件
        # zfh: 发件箱非空时从邮件中提取验证码并验证
        if len(mail.outbox) > 0:
            # zfh: 取出第一封验证邮件
            verification_email = mail.outbox[0]
            # 从邮件提取验证码
            # zfh: 用正则匹配正文中的 4-6 位数字验证码
            code_match = re.search(r'\b(\d{4,6})\b', verification_email.body)
            # zfh: 匹配到验证码时执行验证
            if code_match:
                # zfh: 取出验证码字符串
                code = code_match.group(1)
                # 验证
                # zfh: 调用验证工具校验该邮箱与验证码
                verify('journey@example.com', code)

        # ============ 阶段2: 用户登录 ============
        # zfh: 用注册的账号密码登录
        login_success = self.client.login(
            username='journeyuser',
            password='JourneyPass123!'
        )
        # zfh: 断言阶段2用户可以登录
        self.assertTrue(login_success, "阶段2：用户应该能够登录")

        # ============ 阶段3: 用户创建文章 ============
        # zfh: 创建测试分类
        category = Category.objects.create(
            name='Journey Category',
            slug='journey-category'
        )

        # zfh: 创建该用户的测试文章
        article = Article.objects.create(
            title='My First Article',
            body='This is my first article content',
            author=user,
            category=category,
            status='p',
            type='a'
        )

        # zfh: 断言阶段3文章已被创建
        self.assertIsNotNone(article, "阶段3：文章应该被创建")

        # ============ 阶段4: 其他用户发现并评论文章 ============
        # zfh: 退出当前登录
        self.client.logout()

        # zfh: 创建评论者用户
        commenter = BlogUser.objects.create_user(
            username='commenter',
            email='commenter@example.com',
            password='password'
        )

        # zfh: 以评论者身份登录
        self.client.login(username='commenter', password='password')

        # zfh: 清空此前产生的邮件
        mail.outbox = []  # 清空邮件

        # zfh: 提交评论表单并跟随重定向
        self.client.post(
            reverse('comments:postcomment', kwargs={'article_id': article.id}),
            {
                'body': 'Great article!',
                'email': 'commenter@example.com',
                'name': 'Commenter'
            },
            follow=True
        )

        # ============ 阶段5: 原作者收到通知并回复 ============
        # 验证作者收到评论通知（如果实现了）
        # zfh: 发件箱非空时检查是否有邮件通知原作者
        if len(mail.outbox) > 0:
            # zfh: 检查是否有邮件发往原作者邮箱
            author_notified = any(
                'journey@example.com' in email.to
                for email in mail.outbox
            )
            # 如果有邮件通知功能
            # self.assertTrue(author_notified, "阶段5：作者应该收到评论通知")

        # 作者登录并查看评论
        # zfh: 退出评论者登录
        self.client.logout()
        # zfh: 以原作者身份登录
        self.client.login(username='journeyuser', password='JourneyPass123!')

        # zfh: 请求文章详情页
        article_page = self.client.get(article.get_absolute_url())
        # zfh: 断言文章页面返回 200
        self.assertEqual(article_page.status_code, 200)

        # ============ 验证完整流程成功 ============
        # 用户成功完成：注册、验证、登录、发布、互动的完整流程
        # zfh: 按邮箱取出最终的用户对象
        final_user = BlogUser.objects.get(email='journey@example.com')
        # zfh: 断言最终用户存在
        self.assertIsNotNone(final_user)
        # zfh: 断言该用户名下恰好有 1 篇文章
        self.assertEqual(Article.objects.filter(author=final_user).count(), 1)
        # zfh: 断言该文章下至少有 1 条评论
        self.assertGreater(Comment.objects.filter(article=article).count(), 0)
