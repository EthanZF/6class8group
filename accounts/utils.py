import typing
from datetime import timedelta

# CTY所注：导入 Django 缓存框架，验证码保存在缓存中
from django.core.cache import cache
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# CTY所注：导入项目的发送邮件工具函数
from djangoblog.utils import send_email

# CTY所注：验证码有效期，5 分钟
_code_ttl = timedelta(minutes=5)


# CTY所注：发送重置密码验证码邮件
def send_verify_email(to_mail: str, code: str, subject: str = _("Verify Email")):
    """发送重设密码验证码
    Args:
        to_mail: 接受邮箱
        subject: 邮件主题
        code: 验证码
    """
    # CTY所注：拼接邮件正文（包含验证码及有效期说明），并调用项目邮件工具发送
    html_content = _(
        "You are resetting the password, the verification code is：%(code)s, valid within 5 minutes, please keep it "
        "properly") % {'code': code}
    send_email([to_mail], subject, html_content)


# CTY所注：校验用户提交的验证码是否与缓存中保存的一致，不一致返回错误信息字符串
def verify(email: str, code: str) -> typing.Optional[str]:
    """验证code是否有效
    Args:
        email: 请求邮箱
        code: 验证码
    Return:
        如果有错误就返回错误str
    Node:
        这里的错误处理不太合理，应该采用raise抛出
        否测调用方也需要对error进行处理
    """
    # CTY所注：以邮箱为 key 从缓存取出验证码进行比对
    cache_code = get_code(email)
    if cache_code != code:
        return gettext("Verification code error")


# CTY所注：将验证码写入缓存，key 为邮箱，有效期 5 分钟
def set_code(email: str, code: str):
    """设置code"""
    cache.set(email, code, _code_ttl.seconds)


# CTY所注：从缓存中读取邮箱对应的验证码，不存在或已过期返回 None
def get_code(email: str) -> typing.Optional[str]:
    """获取code"""
    return cache.get(email)
