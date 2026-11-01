"""
oauth 应用的模板标签模块。

本模块只提供一个 inclusion_tag：把"当前启用的第三方平台"整理成模板可直接遍历的
(平台标识, 登录链接) 二元组列表，并渲染 oauth/oauth_applications.html 片段。
登录页底部的第三方登录按钮就是靠这个标签渲染出来的。

SJQ: 模块级注释，说明本模块只有一个标签、它的输入输出以及被哪个模板使用。
"""
# SJQ: template 提供 Library 注册机制
from django import template
# SJQ: reverse 反解登录入口地址，避免把 /oauth/oauthlogin 写死
from django.urls import reverse

# SJQ: 取启用平台列表（内部带 100 分钟缓存）
from oauth.oauthmanager import get_oauth_apps

# SJQ: 注册标签库；文件名必须是 oauth_tags.py，模板中 load oauth_tags 才能找到
register = template.Library()


@register.inclusion_tag('oauth/oauth_applications.html')
def load_oauth_applications(request):
    """
    渲染第三方登录按钮片段。

    入参 request 用于取当前页面路径，拼成 next_url，实现"登录后回到原页面"。
    返回 {'apps': [(平台标识, 完整登录链接), ...]}，没有启用平台时返回空列表。
    """
    # SJQ: 取启用平台；为空说明管理员没配任何平台，前台不显示第三方登录区
    applications = get_oauth_apps()
    if applications:
        # SJQ: 登录入口的基地址
        baseurl = reverse('oauth:oauthlogin')
        # SJQ: 当前页面完整路径，作为登录成功后的回跳目标
        path = request.get_full_path()

        # SJQ: 逐个平台拼出 ?type=xxx&next_url=当前页 的链接
        apps = list(map(lambda x: (x.ICON_NAME, '{baseurl}?type={type}&next_url={next}'.format(
            baseurl=baseurl, type=x.ICON_NAME, next=path)), applications))
    else:
        # SJQ: 没有可用平台时给空列表，模板侧无需判空
        apps = []
    # SJQ: inclusion_tag 的返回值即片段模板的上下文
    return {
        'apps': apps
    }
