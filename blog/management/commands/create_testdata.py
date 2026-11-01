from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from blog.models import Article, Tag, Category, Links, SideBar
from comments.models import Comment


# ZFH: 生成测试数据命令：批量创建用户、分类、标签、文章、友链、侧边栏与评论
# ZFH: 用法：python manage.py create_testdata，适用于本地开发环境快速准备演示数据
class Command(BaseCommand):
    help = 'create test datas'

    def handle(self, *args, **options):
        # ZFH: 创建或获取测试用户（邮箱登录，密码已哈希）
        user, _ = get_user_model().objects.get_or_create(
            email='test@test.com',
            defaults={'username': '测试用户', 'password': make_password('test!q@w#eTYU')})

        # ZFH: 创建父类目
        pcategory = Category.objects.get_or_create(
            name='我是父类目', parent_category=None)[0]

        # ZFH: 在父类目下创建子类目
        category = Category.objects.get_or_create(
            name='子类目', parent_category=pcategory)[0]

        # ZFH: 保存子类目，确保类目记录写入数据库
        category.save()
        # ZFH: 创建公共基础标签，后续文章都会附带
        basetag = Tag()
        basetag.name = "标签"
        basetag.save()
        # ZFH: 循环生成 19 篇文章，并为每篇添加独立标签与公共标签
        for i in range(1, 20):
            article = Article.objects.get_or_create(
                category=category,
                title='nice title ' + str(i),
                body='nice content ' + str(i),
                author=user)[0]
            tag = Tag()
            tag.name = "标签" + str(i)
            tag.save()
            article.tags.add(tag)
            article.tags.add(basetag)
            article.save()

        # ZFH: 定义友情链接列表
        links = [
            ('友情链接', 'https://www.example.com', 1),
            ('Django官网', 'https://www.djangoproject.com', 2),
            ('GitHub', 'https://github.com', 3),
        ]
        # ZFH: 批量创建友情链接
        for name, link, seq in links:
            Links.objects.get_or_create(
                name=name, link=link, sequence=seq,
                defaults={'is_enable': True})

        # ZFH: 定义侧边栏内容列表
        sidebars = [
            ('关于本站', '# 关于本站\n这是一个 DjangoBlog 演示博客。', 1),
            ('公告', '欢迎访问，内容持续更新中！', 2),
        ]
        # ZFH: 批量创建侧边栏
        for name, content, seq in sidebars:
            SideBar.objects.get_or_create(
                name=name, content=content, sequence=seq,
                defaults={'is_enable': True})

        # ZFH: 为前 5 篇文章各创建一条测试评论
        for i, article in enumerate(Article.objects.all()[:5]):
            Comment.objects.get_or_create(
                article=article,
                author=user,
                body='这是第 %d 条测试评论内容，支持 Markdown。' % (i + 1),
                defaults={'is_enable': True})

        # ZFH: 数据生成完成后清空缓存，避免脏数据
        from djangoblog.utils import cache
        cache.clear()
        self.stdout.write(self.style.SUCCESS('created test datas \n'))
