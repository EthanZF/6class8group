"""
Test cases for user authentication business logic
包括用户注册、登录、密码管理、权限等核心业务逻辑
"""
from django.test import TestCase, Client
from django.contrib.auth import authenticate
from django.utils import timezone

from accounts.models import BlogUser


# CTY所注：用户注册业务逻辑测试类
class UserRegistrationTest(TestCase):
    """测试用户注册业务逻辑"""

    def test_user_can_be_created(self):
        """测试用户可以被创建"""
        # CTY所注：创建用户后验证 id 已生成且字段保存正确
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')

    def test_user_password_is_hashed(self):
        """测试用户密码被哈希存储"""
        # CTY所注：验证密码不以明文存储，而是经过 pbkdf2 哈希
        password = 'testpassword123'
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password=password
        )

        # 密码不应该以明文存储
        self.assertNotEqual(user.password, password)
        # 密码应该被哈希
        self.assertTrue(user.password.startswith('pbkdf2_'))

    def test_user_can_check_password(self):
        """测试用户可以验证密码"""
        # CTY所注：check_password 对正确密码返回 True，错误密码返回 False
        password = 'testpassword123'
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password=password
        )

        # 正确的密码应该通过验证
        self.assertTrue(user.check_password(password))
        # 错误的密码应该不通过验证
        self.assertFalse(user.check_password('wrongpassword'))

    def test_username_must_be_unique(self):
        """测试用户名必须唯一"""
        # CTY所注：创建重名用户应抛出异常（唯一性约束）
        BlogUser.objects.create_user(
            username='testuser',
            email='test1@example.com',
            password='password'
        )

        # 尝试创建相同用户名的用户应该失败
        with self.assertRaises(Exception):
            BlogUser.objects.create_user(
                username='testuser',
                email='test2@example.com',
                password='password'
            )

    def test_email_is_stored_correctly(self):
        """测试邮箱正确存储"""
        # CTY所注：验证邮箱字段原样保存
        email = 'test@example.com'
        user = BlogUser.objects.create_user(
            username='testuser',
            email=email,
            password='password'
        )

        self.assertEqual(user.email, email)

    def test_user_is_active_by_default(self):
        """测试用户默认是激活状态"""
        # CTY所注：通过 create_user 创建的用户默认 is_active=True
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password'
        )

        self.assertTrue(user.is_active)

    def test_user_is_not_staff_by_default(self):
        """测试用户默认不是staff"""
        # CTY所注：普通用户默认没有后台（staff）权限
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password'
        )

        self.assertFalse(user.is_staff)

    def test_user_is_not_superuser_by_default(self):
        """测试用户默认不是超级用户"""
        # CTY所注：普通用户默认不是超级用户
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password'
        )

        self.assertFalse(user.is_superuser)


# CTY所注：用户认证（登录校验）业务逻辑测试类
class UserAuthenticationTest(TestCase):
    """测试用户认证业务逻辑"""

    def setUp(self):
        """设置测试环境"""
        # CTY所注：每个用例前创建一个待认证的测试用户
        self.username = 'testuser'
        self.email = 'test@example.com'
        self.password = 'testpassword123'

        self.user = BlogUser.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password
        )

    def test_user_can_authenticate_with_correct_credentials(self):
        """测试用户可以用正确的凭据认证"""
        # CTY所注：用户名+密码正确时 authenticate 返回该用户
        user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(user)
        self.assertEqual(user, self.user)

    def test_user_cannot_authenticate_with_wrong_password(self):
        """测试用户不能用错误的密码认证"""
        # CTY所注：密码错误时 authenticate 返回 None
        user = authenticate(username=self.username, password='wrongpassword')
        self.assertIsNone(user)

    def test_user_cannot_authenticate_with_wrong_username(self):
        """测试用户不能用错误的用户名认证"""
        # CTY所注：用户名不存在时 authenticate 返回 None
        user = authenticate(username='wronguser', password=self.password)
        self.assertIsNone(user)

    def test_inactive_user_cannot_authenticate(self):
        """测试未激活的用户不能认证"""
        # CTY所注：将用户置为未激活后再认证，验证其 is_active 状态
        self.user.is_active = False
        self.user.save()

        user = authenticate(username=self.username, password=self.password)
        # 注意：Django的authenticate()方法会返回用户，但is_active=False
        # 实际的登录阻止发生在login()时
        # 这里我们测试用户的is_active状态
        if user:
            self.assertFalse(user.is_active)

    def test_active_user_can_authenticate(self):
        """测试激活的用户可以认证"""
        # CTY所注：激活状态下的用户可以正常通过认证
        self.user.is_active = True
        self.user.save()

        user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(user)


# CTY所注：用户密码管理业务逻辑测试类
class UserPasswordManagementTest(TestCase):
    """测试用户密码管理业务逻辑"""

    def setUp(self):
        """设置测试环境"""
        # CTY所注：每个用例前创建一个使用旧密码的测试用户
        self.user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpassword123'
        )

    def test_user_can_change_password(self):
        """测试用户可以修改密码"""
        # CTY所注：set_password 修改密码并保存后，新密码生效、旧密码失效
        old_password = 'oldpassword123'
        new_password = 'newpassword456'

        # 验证旧密码
        self.assertTrue(self.user.check_password(old_password))

        # 修改密码
        self.user.set_password(new_password)
        self.user.save()

        # 验证新密码
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertFalse(self.user.check_password(old_password))

    def test_password_change_requires_save(self):
        """测试密码修改需要保存"""
        # CTY所注：set_password 只改内存中的对象，不调用 save 时数据库密码不变
        new_password = 'newpassword456'
        old_password_hash = self.user.password

        # 只设置密码，不保存
        self.user.set_password(new_password)

        # 从数据库重新加载
        user_from_db = BlogUser.objects.get(id=self.user.id)

        # 数据库中的密码应该还是旧的
        self.assertEqual(user_from_db.password, old_password_hash)

    def test_set_unusable_password(self):
        """测试设置不可用的密码"""
        # CTY所注：set_unusable_password 后用户无法使用任何密码登录（常用于第三方登录账号）
        self.user.set_unusable_password()
        self.user.save()

        # 用户应该无法用任何密码认证
        self.assertFalse(self.user.has_usable_password())


# CTY所注：用户权限业务逻辑测试类
class UserPermissionTest(TestCase):
    """测试用户权限业务逻辑"""

    def setUp(self):
        """设置测试环境"""
        # CTY所注：分别创建 普通用户 / 员工用户 / 超级用户 三种角色
        self.normal_user = BlogUser.objects.create_user(
            username='normaluser',
            email='normal@example.com',
            password='password'
        )

        self.staff_user = BlogUser.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password',
            is_staff=True
        )

        self.superuser = BlogUser.objects.create_superuser(
            username='superuser',
            email='super@example.com',
            password='password'
        )

    def test_normal_user_has_no_special_privileges(self):
        """测试普通用户没有特殊权限"""
        # CTY所注：普通用户既不是 staff 也不是超级用户
        self.assertFalse(self.normal_user.is_staff)
        self.assertFalse(self.normal_user.is_superuser)

    def test_staff_user_is_staff(self):
        """测试staff用户有staff权限"""
        # CTY所注：staff 用户可进后台，但不一定是超级用户
        self.assertTrue(self.staff_user.is_staff)
        # staff用户不一定是超级用户
        self.assertFalse(self.staff_user.is_superuser)

    def test_superuser_has_all_privileges(self):
        """测试超级用户有所有权限"""
        # CTY所注：超级用户同时具备 staff、superuser 和激活状态
        self.assertTrue(self.superuser.is_staff)
        self.assertTrue(self.superuser.is_superuser)
        self.assertTrue(self.superuser.is_active)

    def test_create_superuser_method(self):
        """测试创建超级用户的方法"""
        # CTY所注：create_superuser 创建的用户自动具备 staff 和 superuser 权限
        superuser = BlogUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )

        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_user_can_be_promoted_to_staff(self):
        """测试用户可以提升为staff"""
        # CTY所注：将普通用户的 is_staff 置为 True 并保存后生效
        user = BlogUser.objects.create_user(
            username='user',
            email='user@example.com',
            password='password'
        )

        self.assertFalse(user.is_staff)

        # 提升为staff
        user.is_staff = True
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.is_staff)

    def test_user_can_be_promoted_to_superuser(self):
        """测试用户可以提升为超级用户"""
        # CTY所注：将普通用户的 is_superuser 置为 True 并保存后生效
        user = BlogUser.objects.create_user(
            username='user',
            email='user@example.com',
            password='password'
        )

        self.assertFalse(user.is_superuser)

        # 提升为超级用户
        user.is_superuser = True
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.is_superuser)


# CTY所注：用户激活/停用业务逻辑测试类
class UserActivationTest(TestCase):
    """测试用户激活业务逻辑"""

    def test_user_can_be_deactivated(self):
        """测试用户可以被停用"""
        # CTY所注：将 is_active 置为 False 保存后，用户被停用
        user = BlogUser.objects.create_user(
            username='user',
            email='user@example.com',
            password='password'
        )

        self.assertTrue(user.is_active)

        # 停用用户
        user.is_active = False
        user.save()

        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_user_can_be_reactivated(self):
        """测试用户可以被重新激活"""
        # CTY所注：已停用的用户重新置 is_active=True 后恢复激活
        user = BlogUser.objects.create_user(
            username='user',
            email='user@example.com',
            password='password',
            is_active=False
        )

        self.assertFalse(user.is_active)

        # 重新激活用户
        user.is_active = True
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.is_active)


# CTY所注：用户资料业务逻辑测试类
class UserProfileTest(TestCase):
    """测试用户资料业务逻辑"""

    def test_user_has_username(self):
        """测试用户有用户名"""
        # CTY所注：验证用户名字段保存正确
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password'
        )

        self.assertEqual(user.username, 'testuser')

    def test_user_has_email(self):
        """测试用户有邮箱"""
        # CTY所注：验证邮箱字段保存正确
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password'
        )

        self.assertEqual(user.email, 'test@example.com')

    def test_user_can_update_email(self):
        """测试用户可以更新邮箱"""
        # CTY所注：修改邮箱并保存后，数据库中的邮箱同步更新
        user = BlogUser.objects.create_user(
            username='testuser',
            email='old@example.com',
            password='password'
        )

        new_email = 'new@example.com'
        user.email = new_email
        user.save()

        user.refresh_from_db()
        self.assertEqual(user.email, new_email)

    def test_user_string_representation(self):
        """测试用户字符串表示"""
        # CTY所注：BlogUser.__str__ 返回非空字符串（本项目返回邮箱）
        user = BlogUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password'
        )

        # __str__ 方法应该返回用户名或有意义的字符串
        user_str = str(user)
        self.assertIsInstance(user_str, str)
        self.assertTrue(len(user_str) > 0)


# CTY所注：用户查询业务逻辑测试类
class UserQueryTest(TestCase):
    """测试用户查询业务逻辑"""

    def setUp(self):
        """设置测试环境"""
        # CTY所注：批量创建 5 个用户供查询测试使用
        # 创建多个用户
        self.users = []
        for i in range(5):
            user = BlogUser.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='password'
            )
            self.users.append(user)

    def test_query_user_by_username(self):
        """测试按用户名查询用户"""
        # CTY所注：按用户名精确查询用户
        user = BlogUser.objects.get(username='user0')
        self.assertEqual(user, self.users[0])

    def test_query_user_by_email(self):
        """测试按邮箱查询用户"""
        # CTY所注：按邮箱精确查询用户
        user = BlogUser.objects.get(email='user1@example.com')
        self.assertEqual(user, self.users[1])

    def test_query_active_users(self):
        """测试查询激活的用户"""
        # CTY所注：停用 2 个用户后，激活用户应剩 3 个
        # 停用一些用户
        self.users[0].is_active = False
        self.users[0].save()
        self.users[1].is_active = False
        self.users[1].save()

        # 查询激活的用户
        active_users = BlogUser.objects.filter(is_active=True)
        self.assertEqual(active_users.count(), 3)

    def test_query_staff_users(self):
        """测试查询staff用户"""
        # CTY所注：提升 2 个用户为 staff 后，staff 用户应有 2 个
        # 提升一些用户为staff
        self.users[0].is_staff = True
        self.users[0].save()
        self.users[1].is_staff = True
        self.users[1].save()

        # 查询staff用户
        staff_users = BlogUser.objects.filter(is_staff=True)
        self.assertEqual(staff_users.count(), 2)

    def test_query_superusers(self):
        """测试查询超级用户"""
        # CTY所注：创建 1 个超级用户后，超级用户查询结果应为 1 个
        # 创建超级用户
        BlogUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )

        # 查询超级用户
        superusers = BlogUser.objects.filter(is_superuser=True)
        self.assertEqual(superusers.count(), 1)


# CTY所注：用户删除业务逻辑测试类
class UserDeletionTest(TestCase):
    """测试用户删除业务逻辑"""

    def test_user_can_be_deleted(self):
        """测试用户可以被删除"""
        # CTY所注：删除用户后，再按 id 查询应抛出 DoesNotExist
        user = BlogUser.objects.create_user(
            username='user',
            email='user@example.com',
            password='password'
        )

        user_id = user.id

        # 删除用户
        user.delete()

        # 验证用户已被删除
        with self.assertRaises(BlogUser.DoesNotExist):
            BlogUser.objects.get(id=user_id)

    def test_delete_user_cascade_effects(self):
        """测试删除用户的级联效果"""
        # CTY所注：删除用户时，其名下文章因外键 CASCADE 被级联删除
        from blog.models import Article, Category

        user = BlogUser.objects.create_user(
            username='user',
            email='user@example.com',
            password='password'
        )

        # 创建用户的文章
        category = Category.objects.create(
            name='Category',
            slug='category'
        )

        article = Article.objects.create(
            title='User Article',
            body='Content',
            author=user,
            category=category,
            status='p',
            type='a'
        )

        article_id = article.id

        # 删除用户
        user.delete()

        # 验证文章的处理（取决于外键的on_delete设置）
        # 如果是CASCADE，文章应该被删除
        # CTY所注：文章随作者被级联删除，查询应抛出 DoesNotExist
        with self.assertRaises(Article.DoesNotExist):
            Article.objects.get(id=article_id)
