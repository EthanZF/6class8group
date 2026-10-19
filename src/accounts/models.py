# CTY所注：导入 Django 自带的用户模型基类 AbstractUser，本项目用户模型在此基础上扩展
from django.contrib.auth.models import AbstractUser
from django.db import models
# CTY所注：reverse 用于根据路由名称反向解析出 URL
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
# CTY所注：导入项目工具函数，获取当前站点信息
from djangoblog.utils import get_current_site


# Create your models here.

# CTY所注：自定义用户模型 BlogUser，继承 AbstractUser（已含 username/email/password 等字段），在此基础上扩展博客所需字段
class BlogUser(AbstractUser):
    # CTY所注：用户昵称，允许为空
    nickname = models.CharField(_('nick name'), max_length=100, blank=True)
    # CTY所注：账号创建时间，默认取当前时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    # CTY所注：资料最后修改时间，默认取当前时间
    last_modify_time = models.DateTimeField(_('last modify time'), default=now)
    # CTY所注：账号来源（如注册页 Register、后台 adminsite、第三方 OAuth 等），允许为空
    source = models.CharField(_('create source'), max_length=100, blank=True)

    def get_absolute_url(self):
        # CTY所注：返回该用户的作者详情页相对 URL（/author/<username>）
        return reverse(
            'blog:author_detail', kwargs={
                'author_name': self.username})

    def __str__(self):
        # CTY所注：对象的字符串表示，后台和 shell 中显示为邮箱
        return self.email

    def get_full_url(self):
        # CTY所注：在相对 URL 前拼接站点域名，得到完整的可访问地址（用于邮件、站点地图等场景）
        site = get_current_site().domain
        url = "https://{site}{path}".format(site=site,
                                            path=self.get_absolute_url())
        return url

    class Meta:
        # CTY所注：默认按 id 倒序排列（最新注册的用户排在前面）
        ordering = ['-id']
        # CTY所注：后台显示的模型中文名称（单数与复数相同）
        verbose_name = _('user')
        verbose_name_plural = verbose_name
        # CTY所注：latest() 查询时按 id 字段取最新记录
        get_latest_by = 'id'
