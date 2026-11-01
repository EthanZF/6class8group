import requests
from django.core.management.base import BaseCommand
from django.templatetags.static import static

from djangoblog.utils import save_user_avatar
from oauth.models import OAuthUser
from oauth.oauthmanager import get_manager_by_type


# ZFH: 同步用户头像命令：遍历 OAuth 用户，校验并本地化其头像图片地址
# ZFH: 用法：python manage.py sync_user_avatar，用于修复第三方头像失效或未本地化的问题
class Command(BaseCommand):
    help = 'sync user avatar'

    def test_picture(self, url):
        # ZFH: 测试图片 URL 是否可访问，200 表示有效
        try:
            if requests.get(url, timeout=2).status_code == 200:
                return True
        # ZFH: 捕获请求超时、连接失败等异常，视为图片不可用，交由后续逻辑兜底
        except:
            pass

    def handle(self, *args, **options):
        # ZFH: 静态资源根路径前缀，用于判断头像是否已是本地静态文件
        static_url = static("../")
        # ZFH: 获取全部 OAuth 用户
        users = OAuthUser.objects.all()
        # ZFH: 输出待同步用户数量
        self.stdout.write(f'开始同步{len(users)}个用户头像')
        # ZFH: 逐个处理用户头像同步
        for u in users:
            self.stdout.write(f'开始同步:{u.nickname}')
            # ZFH: 读取用户当前头像地址
            url = u.picture
            if url:
                # ZFH: 头像已是本地静态文件时，先校验图片是否仍有效
                if url.startswith(static_url):
                    # ZFH: 本地静态头像有效则跳过，保持不变
                    if self.test_picture(url):
                        continue
                    else:
                        # ZFH: 本地头像失效时，尝试从第三方平台重新获取
                        if u.metadata:
                            # ZFH: 根据用户类型获取对应的 OAuth 管理器
                            manage = get_manager_by_type(u.type)
                            # ZFH: 通过元数据重新拉取头像并保存到本地
                            url = manage.get_picture(u.metadata)
                            url = save_user_avatar(url)
                        else:
                            # ZFH: 无元数据可获取时，回退为默认头像
                            url = static('blog/img/avatar.png')
                else:
                    # ZFH: 非本地头像时，直接下载并保存到本地
                    url = save_user_avatar(url)
            else:
                # ZFH: 用户无头像时，设置为默认头像
                url = static('blog/img/avatar.png')
            # ZFH: 头像处理完成后更新并保存用户记录
            if url:
                self.stdout.write(
                    f'结束同步:{u.nickname}.url:{url}')
                u.picture = url
                u.save()
        # ZFH: 输出同步完成提示
        self.stdout.write('结束同步')
