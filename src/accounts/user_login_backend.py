from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


# CTY所注：自定义认证后端，允许用户使用"用户名"或"邮箱"两种方式登录
class EmailOrUsernameModelBackend(ModelBackend):
    """
    允许使用用户名或邮箱登录
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # CTY所注：输入内容中包含 @ 则按邮箱查询用户，否则按用户名查询
        if '@' in username:
            kwargs = {'email': username}
        else:
            kwargs = {'username': username}
        try:
            # CTY所注：查出用户后校验密码，密码正确则返回该用户
            user = get_user_model().objects.get(**kwargs)
            if user.check_password(password):
                return user
        except get_user_model().DoesNotExist:
            # CTY所注：用户不存在时返回 None，表示认证失败
            return None

    def get_user(self, username):
        # CTY所注：根据主键（用户id）获取用户，供 Django 从 session 恢复登录状态时使用
        try:
            return get_user_model().objects.get(pk=username)
        except get_user_model().DoesNotExist:
            return None
