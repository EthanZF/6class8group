# CTY所注：导入 Django 测试工具（模拟客户端、请求工厂、测试用例基类）
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import BlogUser
from blog.models import Article, Category
from djangoblog.utils import *
from . import utils


# Create your tests here.

# CTY所注：accounts 应用功能测试类，覆盖登录、注册、验证码、忘记密码等完整流程
class AccountTest(TestCase):
    def setUp(self):
        # CTY所注：每个测试方法执行前的初始化：创建模拟客户端、请求工厂和一个测试用户
        self.client = Client()
        self.factory = RequestFactory()
        self.blog_user = BlogUser.objects.create_user(
            username="test",
            email="admin@admin.com",
            password="12345678"
        )
        # CTY所注：重置密码测试中使用的新密码
        self.new_test = "xxx123--="

    def test_validate_account(self):
        # CTY所注：测试超级管理员登录后台并访问文章管理页
        site = get_current_site().domain
        user = BlogUser.objects.create_superuser(
            email="liangliangyy1@gmail.com",
            username="liangliangyy1",
            password="qwer!@#$ggg")
        testuser = BlogUser.objects.get(username='liangliangyy1')

        # CTY所注：验证超级用户可以登录成功
        loginresult = self.client.login(
            username='liangliangyy1',
            password='qwer!@#$ggg')
        self.assertEqual(loginresult, True)
        # CTY所注：验证登录后可以正常访问后台首页
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

        # CTY所注：创建一个测试分类
        category = Category()
        category.name = "categoryaaa"
        category.creation_time = timezone.now()
        category.last_modify_time = timezone.now()
        category.save()

        # CTY所注：创建一篇已发布的测试文章
        article = Article()
        article.title = "nicetitleaaa"
        article.body = "nicecontentaaa"
        article.author = user
        article.category = category
        article.type = 'a'
        article.status = 'p'
        article.save()

        # CTY所注：验证可以访问该文章的后台编辑页
        response = self.client.get(article.get_admin_url())
        self.assertEqual(response.status_code, 200)

    def test_validate_register(self):
        # CTY所注：测试完整的注册 → 邮箱验证 → 登录 → 登出流程
        # CTY所注：注册前确认该邮箱不存在
        self.assertEquals(
            0, len(
                BlogUser.objects.filter(
                    email='user123@user.com')))
        # CTY所注：提交注册表单
        response = self.client.post(reverse('account:register'), {
            'username': 'user1233',
            'email': 'user123@user.com',
            'password1': 'password123!q@wE#R$T',
            'password2': 'password123!q@wE#R$T',
        })
        # CTY所注：注册后确认用户已写入数据库
        self.assertEquals(
            1, len(
                BlogUser.objects.filter(
                    email='user123@user.com')))
        # CTY所注：模拟点击邮件中的验证链接（用同样的算法生成签名）
        user = BlogUser.objects.filter(email='user123@user.com')[0]
        sign = get_sha256(get_sha256(settings.SECRET_KEY + str(user.id)))
        path = reverse('accounts:result')
        url = '{path}?type=validation&id={id}&sign={sign}'.format(
            path=path, id=user.id, sign=sign)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # CTY所注：登录并把用户提升为管理员，便于测试后台访问
        self.client.login(username='user1233', password='password123!q@wE#R$T')
        user = BlogUser.objects.filter(email='user123@user.com')[0]
        user.is_superuser = True
        user.is_staff = True
        user.save()
        delete_sidebar_cache()
        # CTY所注：创建测试分类和文章
        category = Category()
        category.name = "categoryaaa"
        category.creation_time = timezone.now()
        category.last_modify_time = timezone.now()
        category.save()

        article = Article()
        article.category = category
        article.title = "nicetitle333"
        article.body = "nicecontentttt"
        article.author = user

        article.type = 'a'
        article.status = 'p'
        article.save()

        # CTY所注：验证登录状态下可以访问文章后台编辑页
        response = self.client.get(article.get_admin_url())
        self.assertEqual(response.status_code, 200)

        # CTY所注：测试登出（允许重定向或正常返回）
        response = self.client.get(reverse('account:logout'))
        self.assertIn(response.status_code, [301, 302, 200])

        # CTY所注：登出后访问后台应被重定向
        response = self.client.get(article.get_admin_url())
        self.assertIn(response.status_code, [301, 302, 200])

        # CTY所注：使用错误密码登录，验证登录失败后的响应
        response = self.client.post(reverse('account:login'), {
            'username': 'user1233',
            'password': 'password123'
        })
        self.assertIn(response.status_code, [301, 302, 200])

        # CTY所注：再次访问文章后台编辑页，验证响应状态
        response = self.client.get(article.get_admin_url())
        self.assertIn(response.status_code, [301, 302, 200])

    def test_verify_email_code(self):
        # CTY所注：测试邮箱验证码的发送与校验
        to_email = "admin@admin.com"
        code = generate_code()
        utils.set_code(to_email, code)
        utils.send_verify_email(to_email, code)

        # CTY所注：验证码正确时 verify 返回 None（无错误）
        err = utils.verify("admin@admin.com", code)
        self.assertEqual(err, None)

        # CTY所注：邮箱不匹配时返回错误信息字符串
        err = utils.verify("admin@123.com", code)
        self.assertEqual(type(err), str)

    def test_forget_password_email_code_success(self):
        # CTY所注：测试正确提交邮箱时，发送验证码接口返回 ok
        resp = self.client.post(
            path=reverse("account:forget_password_code"),
            data=dict(email="admin@admin.com")
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode("utf-8"), "ok")

    def test_forget_password_email_code_fail(self):
        # CTY所注：测试邮箱缺失或格式错误时，接口返回"错误的邮箱"
        resp = self.client.post(
            path=reverse("account:forget_password_code"),
            data=dict()
        )
        self.assertEqual(resp.content.decode("utf-8"), "错误的邮箱")

        resp = self.client.post(
            path=reverse("account:forget_password_code"),
            data=dict(email="admin@com")
        )
        self.assertEqual(resp.content.decode("utf-8"), "错误的邮箱")

    def test_forget_password_email_success(self):
        # CTY所注：测试验证码正确时，忘记密码可以成功重置密码
        code = generate_code()
        utils.set_code(self.blog_user.email, code)
        data = dict(
            new_password1=self.new_test,
            new_password2=self.new_test,
            email=self.blog_user.email,
            code=code,
        )
        resp = self.client.post(
            path=reverse("account:forget_password"),
            data=data
        )
        # CTY所注：重置成功会 302 跳转到登录页
        self.assertEqual(resp.status_code, 302)

        # 验证用户密码是否修改成功
        # CTY所注：从数据库重新取出用户，验证新密码已生效
        blog_user = BlogUser.objects.filter(
            email=self.blog_user.email,
        ).first()  # type: BlogUser
        self.assertNotEqual(blog_user, None)
        self.assertEqual(blog_user.check_password(data["new_password1"]), True)

    def test_forget_password_email_not_user(self):
        # CTY所注：测试邮箱未注册时，重置密码失败（返回 200 并回显错误，而非跳转）
        data = dict(
            new_password1=self.new_test,
            new_password2=self.new_test,
            email="123@123.com",
            code="123456",
        )
        resp = self.client.post(
            path=reverse("account:forget_password"),
            data=data
        )

        self.assertEqual(resp.status_code, 200)


    def test_forget_password_email_code_error(self):
        # CTY所注：测试验证码错误时，重置密码失败（返回 200 并回显错误）
        code = generate_code()
        utils.set_code(self.blog_user.email, code)
        data = dict(
            new_password1=self.new_test,
            new_password2=self.new_test,
            email=self.blog_user.email,
            code="111111",
        )
        resp = self.client.post(
            path=reverse("account:forget_password"),
            data=data
        )

        self.assertEqual(resp.status_code, 200)
