"""
oauth 应用的路由表。

五个路由对应第三方登录的五个步骤，顺序上首尾相接：
oauthlogin（跳平台）→ 平台回调 /oauth/authorize（本表第一条）→
requireemail（补全邮箱，可选）→ emailconfirm（邮件确认）→ bindsuccess（结果页）。

注意前四条路由都以 oauth/ 开头且不带结尾斜杠，而项目总路由也把它挂在根路径下，
因此实际地址就是 /oauth/xxx；最后一条带 name，供模板与视图反解。

SJQ: 模块级注释，说明 5 条路由的流程顺序与路径拼接方式。
"""
# SJQ: path 用于注册 URL 规则
from django.urls import path

# SJQ: 引入本应用的视图模块
from . import views

# SJQ: 命名空间，模板里可用 {% url 'oauth:oauthlogin' %} 反解
app_name = "oauth"
urlpatterns = [
    # SJQ: 平台回调地址，必须与 OAuthConfig.callback_url 中登记的一致
    path(
        r'oauth/authorize',
        views.authorize),
    # SJQ: 补全邮箱页；<int:oauthid> 指定为整数转换器
    path(
        r'oauth/requireemail/<int:oauthid>.html',
        views.RequireEmailView.as_view(),
        name='require_email'),
    # SJQ: 邮件确认链接；<sign> 为 sha256 签名，防止伪造 id 绑定他人邮箱
    path(
        r'oauth/emailconfirm/<int:id>/<sign>.html',
        views.emailconfirm,
        name='email_confirm'),
    # SJQ: 绑定结果提示页
    path(
        r'oauth/bindsuccess/<int:oauthid>.html',
        views.bindsuccess,
        name='bindsuccess'),
    # SJQ: 第三方登录入口，前台按钮链接到这里
    path(
        r'oauth/oauthlogin',
        views.oauthlogin,
        name='oauthlogin')]
