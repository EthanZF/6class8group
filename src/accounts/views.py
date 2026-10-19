# CTY所注：导入日志模块，用于记录运行信息
import logging
from django.utils.translation import gettext_lazy as _
from django.conf import settings
# CTY所注：导入 Django 认证模块（登录/登出等）
from django.contrib import auth
# CTY所注：登录跳转参数名常量（默认为 "next"）
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import get_user_model
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
# CTY所注：make_password 用于将明文密码哈希后入库
from django.contrib.auth.hashers import make_password
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse
# CTY所注：校验跳转 URL 是否属于本站，防止开放重定向攻击
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

# CTY所注：导入项目工具函数（发邮件、生成签名、获取站点、生成验证码、清除侧边栏缓存）
from djangoblog.utils import send_email, get_sha256, get_current_site, generate_code, delete_sidebar_cache
# CTY所注：导入项目封装的视图基类（自带 CSRF 保护、禁用缓存等安全特性）
from djangoblog.base_views import SecureFormView, LoginFormView, LogoutRedirectView
from . import utils
from .forms import RegisterForm, LoginForm, ForgetPasswordForm, ForgetPasswordCodeForm
from .models import BlogUser

# CTY所注：获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# Create your views here.

# CTY所注：用户注册视图（基于类的视图），处理注册表单的展示与提交
class RegisterView(SecureFormView):
    """
    用户注册视图（重构版）

    使用 SecureFormView 基类，自动提供 CSRF 保护
    """
    # CTY所注：指定使用的表单类与渲染模板
    form_class = RegisterForm
    template_name = 'account/registration_form.html'

    def form_valid(self, form):
        # CTY所注：表单验证通过后的处理：保存用户（未激活）→ 发送验证邮件 → 跳转结果页
        if form.is_valid():
            # CTY所注：保存用户但标记为未激活，需邮箱验证后才能登录；来源标记为 Register
            user = form.save(False)
            user.is_active = False
            user.source = 'Register'
            user.save(True)
            site = get_current_site().domain
            # CTY所注：用 SECRET_KEY + 用户id 做两次 sha256 生成签名，防止验证链接被伪造
            sign = get_sha256(get_sha256(settings.SECRET_KEY + str(user.id)))

            # CTY所注：开发环境下验证链接中的站点地址固定为本地
            if settings.DEBUG:
                site = '127.0.0.1:8000'
            path = reverse('account:result')
            # CTY所注：拼接邮箱验证链接（type=validation 表示邮箱验证）
            url = "http://{site}{path}?type=validation&id={id}&sign={sign}".format(
                site=site, path=path, id=user.id, sign=sign)

            # CTY所注：组装验证邮件的 HTML 正文
            content = """
                            <p>请点击下面链接验证您的邮箱</p>

                            <a href="{url}" rel="bookmark">{url}</a>

                            再次感谢您！
                            <br />
                            如果上面链接无法打开，请将此链接复制至浏览器。
                            {url}
                            """.format(url=url)
            # CTY所注：向用户邮箱发送验证邮件
            send_email(
                emailto=[
                    user.email,
                ],
                title='验证您的电子邮箱',
                content=content)

            # CTY所注：跳转到"注册成功"提示页（type=register）
            url = reverse('accounts:result') + \
                  '?type=register&id=' + str(user.id)
            return HttpResponseRedirect(url)
        else:
            # CTY所注：表单验证失败，回显表单和错误信息
            return self.render_to_response({
                'form': form
            })


# CTY所注：用户登出视图，处理退出登录
class LogoutView(LogoutRedirectView):
    """
    用户登出视图（重构版）

    使用 LogoutRedirectView 基类，自动禁用缓存
    """
    # CTY所注：登出后跳转到登录页
    url = '/login/'

    def get(self, request, *args, **kwargs):
        # CTY所注：调用 Django logout 清除 session 登录状态，并清除侧边栏缓存
        logout(request)
        delete_sidebar_cache()
        # 获取响应对象并删除登录标记 cookie
        response = super(LogoutView, self).get(request, *args, **kwargs)
        # CTY所注：删除前端用于判断登录状态的 logged_user cookie
        response.delete_cookie('logged_user')
        return response


# CTY所注：用户登录视图，处理登录表单的展示与提交
class LoginView(LoginFormView):
    """
    用户登录视图（重构版）

    使用 LoginFormView 基类，自动提供：
    - 敏感参数保护（password）
    - CSRF 保护
    - 禁用缓存
    """
    # CTY所注：指定登录表单类、模板及默认登录成功跳转地址
    form_class = LoginForm
    template_name = 'account/login.html'
    success_url = '/'
    redirect_field_name = REDIRECT_FIELD_NAME

    def get_context_data(self, **kwargs):
        # CTY所注：把 GET 参数中的跳转地址（next）传给模板，没有则默认跳首页
        redirect_to = self.request.GET.get(self.redirect_field_name)
        if redirect_to is None:
            redirect_to = '/'
        kwargs['redirect_to'] = redirect_to

        return super(LoginView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        # CTY所注：用 POST 数据重新构造认证表单进行校验
        form = AuthenticationForm(data=self.request.POST, request=self.request)

        if form.is_valid():
            # CTY所注：清除侧边栏缓存，避免登录前后缓存内容错乱
            delete_sidebar_cache()
            logger.info(self.redirect_field_name)

            # CTY所注：执行登录，将用户写入 session
            auth.login(self.request, form.get_user())
            # 设置登录有效期
            if self.request.POST.get("remember"):
                # CTY所注：勾选"记住我"时，使用较长的会话有效期
                self.request.session.set_expiry(settings.REMEMBER_ME_LOGIN_TTL)
                cookie_max_age = settings.REMEMBER_ME_LOGIN_TTL
            else:
                # 使用Django默认的2周
                # CTY所注：未勾选时使用 Django 默认会话有效期（2 周）
                self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                cookie_max_age = settings.SESSION_COOKIE_AGE

            # 获取响应对象并设置登录标记 cookie
            response = super(LoginView, self).form_valid(form)
            # CTY所注：写入 logged_user cookie，供前端 JS 判断登录状态（有效期与会话一致）
            response.set_cookie(
                'logged_user',
                'true',
                max_age=cookie_max_age,
                httponly=False,  # 允许 JavaScript 访问
                samesite='Lax'
            )
            return response
            # return HttpResponseRedirect('/')
        else:
            # CTY所注：认证失败，回显登录表单和错误信息
            return self.render_to_response({
                'form': form
            })

    def get_success_url(self):
        # CTY所注：确定登录成功后的跳转地址，优先取 POST 中的 next 参数
        redirect_to = self.request.POST.get(self.redirect_field_name)
        # CTY所注：校验跳转地址是否为本站地址，非法则回退到默认首页，防止开放重定向
        if not url_has_allowed_host_and_scheme(
                url=redirect_to, allowed_hosts=[
                    self.request.get_host()]):
            redirect_to = self.success_url
        return redirect_to


# CTY所注：操作结果视图，处理"注册成功提示"和"邮箱验证"两种场景
def account_result(request):
    # CTY所注：type 区分场景（register=注册成功提示，validation=邮箱验证），id 为用户id
    type = request.GET.get('type')
    id = request.GET.get('id')

    # CTY所注：取出目标用户，不存在则返回 404
    user = get_object_or_404(get_user_model(), id=id)
    logger.info(type)
    # CTY所注：用户已激活则直接跳回首页
    if user.is_active:
        return HttpResponseRedirect('/')
    if type and type in ['register', 'validation']:
        if type == 'register':
            # CTY所注：注册成功场景，仅展示提示信息
            content = '''
    恭喜您注册成功，一封验证邮件已经发送到您的邮箱，请验证您的邮箱后登录本站。
    '''
            title = '注册成功'
        else:
            # CTY所注：邮箱验证场景，重新计算签名并与 URL 中的签名比对
            c_sign = get_sha256(get_sha256(settings.SECRET_KEY + str(user.id)))
            sign = request.GET.get('sign')
            # CTY所注：签名不一致说明链接被篡改，返回 403 禁止访问
            if sign != c_sign:
                return HttpResponseForbidden()
            # CTY所注：签名正确则激活用户
            user.is_active = True
            user.save()
            content = '''
            恭喜您已经成功的完成邮箱验证，您现在可以使用您的账号来登录本站。
            '''
            title = '验证成功'
        return render(request, 'account/result.html', {
            'title': title,
            'content': content
        })
    else:
        # CTY所注：非法的 type 参数，直接跳回首页
        return HttpResponseRedirect('/')


# CTY所注：忘记密码视图，校验验证码通过后重置用户密码
class ForgetPasswordView(SecureFormView):
    """
    忘记密码视图（重构版）

    使用 SecureFormView 基类，自动提供 CSRF 保护
    """
    form_class = ForgetPasswordForm
    template_name = 'account/forget_password.html'

    def form_valid(self, form):
        if form.is_valid():
            # CTY所注：根据邮箱查出用户，将新密码哈希后保存，然后跳转登录页
            blog_user = BlogUser.objects.filter(email=form.cleaned_data.get("email")).get()
            blog_user.password = make_password(form.cleaned_data["new_password2"])
            blog_user.save()
            return HttpResponseRedirect('/login/')
        else:
            # CTY所注：表单校验失败（如验证码错误），回显错误信息
            return self.render_to_response({'form': form})


# CTY所注：发送"忘记密码"邮箱验证码的接口视图
class ForgetPasswordEmailCode(View):

    def post(self, request: HttpRequest):
        # CTY所注：校验邮箱格式，不合法直接返回错误提示
        form = ForgetPasswordCodeForm(request.POST)
        if not form.is_valid():
            return HttpResponse("错误的邮箱")
        to_email = form.cleaned_data["email"]

        # CTY所注：生成随机验证码，发送邮件并写入缓存（5 分钟有效）
        code = generate_code()
        utils.send_verify_email(to_email, code)
        utils.set_code(to_email, code)

        # CTY所注：返回 ok 表示验证码已发送
        return HttpResponse("ok")
