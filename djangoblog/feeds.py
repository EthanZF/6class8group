# zfh: 导入获取用户模型的函数
from django.contrib.auth import get_user_model
# zfh: 导入 Django 的 Feed 基类
from django.contrib.syndication.views import Feed
# zfh: 导入时区工具，用于取当前时间
from django.utils import timezone
# zfh: 导入 RSS 2.0 格式的 Feed 生成器
from django.utils.feedgenerator import Rss201rev2Feed

# zfh: 导入文章模型
from blog.models import Article
# zfh: 导入 Markdown 渲染工具
from djangoblog.utils import CommonMarkdown


# zfh: 博客 RSS Feed 类，输出最新的文章条目
class DjangoBlogFeed(Feed):
    # zfh: 指定使用 RSS 2.0 格式生成 Feed
    feed_type = Rss201rev2Feed

    # zfh: Feed 的描述信息
    description = '大巧无工,重剑无锋.'
    # zfh: Feed 的标题
    title = "且听风吟 大巧无工,重剑无锋. "
    # zfh: Feed 对应的页面链接
    link = "/feed/"

    # zfh: 返回 Feed 作者名称
    def author_name(self):
        # zfh: 取第一个用户的昵称作为作者名
        return get_user_model().objects.first().nickname

    # zfh: 返回 Feed 作者的链接
    def author_link(self):
        # zfh: 取第一个用户的个人主页地址作为作者链接
        return get_user_model().objects.first().get_absolute_url()

    # zfh: 返回 Feed 中包含的文章条目
    def items(self):
        # zfh: 取最新的 5 篇已发布原创文章，按发布时间倒序
        return Article.objects.filter(type='a', status='p').order_by('-pub_time')[:5]

    # zfh: 返回条目标题
    def item_title(self, item):
        # zfh: 返回文章标题
        return item.title

    # zfh: 返回条目描述
    def item_description(self, item):
        # zfh: 把文章正文渲染成 Markdown HTML
        return CommonMarkdown.get_markdown(item.body)

    # zfh: 返回 Feed 的版权信息
    def feed_copyright(self):
        # zfh: 获取当前时间
        now = timezone.now()
        # zfh: 用当前年份拼接版权字符串
        return "Copyright© {year} 且听风吟".format(year=now.year)

    # zfh: 返回条目的链接
    def item_link(self, item):
        # zfh: 返回文章自身的 URL
        return item.get_absolute_url()

    # zfh: 返回条目的唯一标识
    def item_guid(self, item):
        # zfh: 直接返回空值，不设置 guid
        return
