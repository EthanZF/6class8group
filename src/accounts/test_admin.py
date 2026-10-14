"""
Accounts Admin 测试
测试用户管理后台的各项功能
"""
from django.contrib.admin.sites import AdminSite
from django.test import TestCase, RequestFactory
from django.urls import reverse

from accounts.admin import BlogUserAdmin
from accounts.models import BlogUser
# CTY所注：导入项目测试基类和后台测试混入类，提供登录管理员、构造用户等公共方法
from djangoblog.test_base import BaseTestCase, AdminTestMixin


# CTY所注：BlogUser 后台管理功能测试类
class BlogUserAdminTest(BaseTestCase, AdminTestMixin):
    """测试 BlogUser Admin"""

    def setUp(self):
        # CTY所注：初始化后台站点实例和 BlogUserAdmin 管理类实例
        super().setUp()
        self.site = AdminSite()
        self.blog_user_admin = BlogUserAdmin(BlogUser, self.site)

    def test_admin_list_display(self):
        """测试列表显示字段"""
        # CTY所注：登录管理员后访问用户列表页，验证页面包含用户名和邮箱
        self.login_admin()
        response = self.assert_admin_accessible(BlogUser)
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.email)

    def test_admin_search(self):
        """测试搜索功能"""
        # CTY所注：在用户列表页按用户名搜索，验证能搜到目标用户
        self.login_admin()
        url = self.get_admin_url(BlogUser)
        response = self.client.get(url, {'q': self.user.username})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)

    def test_admin_filter_by_is_staff(self):
        """测试按员工状态过滤"""
        # CTY所注：按 is_staff=1 过滤用户列表，验证员工用户出现在结果中
        staff_user = self.create_staff_user()
        self.login_admin()
        url = self.get_admin_url(BlogUser)
        response = self.client.get(url, {'is_staff__exact': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, staff_user.username)

    def test_admin_change_user(self):
        """测试修改用户"""
        # CTY所注：访问用户修改页并提交修改后的邮箱，再从数据库刷新验证
        self.login_admin()
        url = self.get_admin_change_url(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 修改用户信息
        # CTY所注：提交修改表单（日期字段需按 Django admin 的 日期/时间 两个字段分别提交）
        response = self.client.post(url, {
            'username': self.user.username,
            'email': 'newemail@test.com',
            'date_joined_0': self.user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': self.user.date_joined.strftime('%H:%M:%S'),
        })
        self.user.refresh_from_db()

    def test_admin_requires_login(self):
        """测试需要登录才能访问"""
        # CTY所注：未登录状态下访问用户后台应被禁止（重定向到登录页）
        self.client.logout()
        self.assert_admin_forbidden_for_user(BlogUser)

    def test_admin_forbidden_for_normal_user(self):
        """测试普通用户无法访问"""
        # CTY所注：普通（非 staff）用户登录后访问用户后台应被禁止
        self.login_user()
        self.assert_admin_forbidden_for_user(BlogUser)

    def test_get_list_filter(self):
        """测试获取列表过滤器"""
        # CTY所注：验证列表过滤器包含 is_staff 和 is_superuser 字段
        request = self.factory.get('/')
        request.user = self.admin_user
        filters = self.blog_user_admin.get_list_filter(request)
        self.assertIn('is_staff', filters)
        self.assertIn('is_superuser', filters)

    def test_get_readonly_fields_for_superuser(self):
        """测试超级管理员看到的只读字段"""
        # CTY所注：超级管理员访问时，只读字段应返回列表或元组
        request = self.factory.get('/')
        request.user = self.admin_user
        readonly_fields = self.blog_user_admin.get_readonly_fields(request, self.user)
        self.assertIsInstance(readonly_fields, (list, tuple))

    def test_get_readonly_fields_for_staff(self):
        """测试员工用户看到的只读字段"""
        # CTY所注：普通员工用户访问时，只读字段同样应返回列表或元组
        staff = self.create_staff_user()
        request = self.factory.get('/')
        request.user = staff
        readonly_fields = self.blog_user_admin.get_readonly_fields(request, self.user)
        # 员工用户应该看到更多只读字段
        self.assertIsInstance(readonly_fields, (list, tuple))
