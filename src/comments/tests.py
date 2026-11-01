#psj: 【模块】comments.tests —— 评论功能的主流程测试
#psj: 这个文件用一个完整场景把评论的主要流程串起来跑一遍：
#psj: 准备一个开启"评论需审核"的站点配置 → 登录 → 建分类和文章 → 发评论（因待审前台看不到）
#psj: → 手动审核通过后可见 → 再发一条 → 回复其中一条形成楼中楼
#psj: → 最后验证模板标签和发信函数能正常工作。
#psj: 用 TransactionTestCase 是因为流程里要多次提交并重新查库，希望每条用例后数据库真正回滚。
from django.test import Client, RequestFactory, TransactionTestCase
from django.urls import reverse

from accounts.models import BlogUser
from blog.models import Category, Article
from comments.models import Comment
from comments.templatetags.comments_tags import *
from djangoblog.utils import get_max_articleid_commentid


# Create your tests here.

#psj: 【类】评论主流程测试。包含三部分：setUp 准备环境、update_article_comment_status 辅助审核、
#psj: test_validate_comment 走完整流程。
class CommentsTest(TransactionTestCase):
    #psj: 【方法】准备测试环境：建 client（模拟浏览器）和 RequestFactory（模拟请求对象），
    #psj: 把站点配置里的"评论需要审核"打开，再建一个超级用户用于登录。
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        from blog.models import BlogSettings
        value = BlogSettings()
        value.comment_need_review = True
        value.save()

        self.user = BlogUser.objects.create_superuser(
            email="liangliangyy1@gmail.com",
            username="liangliangyy1",
            password="liangliangyy1")

    #psj: 【辅助方法】把某篇文章下的所有评论设为已启用。
    #psj: 因为站点配置开了"需审核"，新评论的 is_enable 默认是 False，
    #psj: 测试里用这个方法代替去后台逐个点"通过"。
    def update_article_comment_status(self, article):
        comments = article.comment_set.all()
        for comment in comments:
            comment.is_enable = True
            comment.save()

    #psj: 【用例】评论主流程。
    #psj: 依次验证：发评论后因待审核不显示 → 审核后显示 → 再发一条 → 审核后共两条
    #psj: → 回复第一条形成楼中楼 → 模板标签能正确取出子评论 → 发信函数不抛异常。
    def test_validate_comment(self):
        #psj: 用测试用户登录，后面的提交才会被视图放行（CommentPostView 要求必须登录）。
        self.client.login(username='liangliangyy1', password='liangliangyy1')

        #psj: 建一个分类和一篇已发表的文章，作为评论的挂载点。
        category = Category()
        category.name = "categoryccc"
        category.save()

        article = Article()
        article.title = "nicetitleccc"
        article.body = "nicecontentccc"
        article.author = self.user
        article.category = category
        article.type = 'a'
        article.status = 'p'
        article.save()

        #psj: 反查出提交评论的地址，形如 /article/<文章id>/postcomment。
        comment_url = reverse(
            'comments:postcomment', kwargs={
                'article_id': article.id})

        #psj: 第一次提交评论，只带正文。
        response = self.client.post(comment_url,
                                    {
                                        'body': '123ffffffffff'
                                    })

        #psj: 302 表示提交成功并跳转；如果表单校验失败会返回 200 重新渲染页面。
        self.assertEqual(response.status_code, 302)

        article = Article.objects.get(pk=article.pk)
        #psj: 站点配置要求审核，所以刚发的评论不在前台列表里，这里断言数量为 0。
        self.assertEqual(len(article.comment_list()), 0)
        #psj: 手动把评论改成已启用，相当于在后台点了"通过"。
        self.update_article_comment_status(article)

        #psj: 审核之后这条评论才出现在列表里。
        self.assertEqual(len(article.comment_list()), 1)

        response = self.client.post(comment_url,
                                    {
                                        'body': '123ffffffffff',
                                    })

        self.assertEqual(response.status_code, 302)

        article = Article.objects.get(pk=article.pk)
        self.update_article_comment_status(article)
        self.assertEqual(len(article.comment_list()), 2)
        parent_comment_id = article.comment_list()[0].id

        #psj: 第三次提交带上了 parent_comment_id，表示这是对第一条评论的回复。
        response = self.client.post(comment_url,
                                    {
                                        'body': '''
                                        # Title1

        ```python
        import os
        ```

        [url](https://www.lylinux.net/)

        [ddd](http://www.baidu.com)


        ''',
                                        'parent_comment_id': parent_comment_id
                                    })

        self.assertEqual(response.status_code, 302)
        self.update_article_comment_status(article)
        article = Article.objects.get(pk=article.pk)
        self.assertEqual(len(article.comment_list()), 3)
        comment = Comment.objects.get(id=parent_comment_id)
        #psj: 用模板标签取出这条评论的子评论，应该正好 1 条。
        tree = parse_commenttree(article.comment_list(), comment)
        self.assertEqual(len(tree), 1)
        #psj: 再调用渲染标签，确认能拿到非空的上下文（至少不会抛异常）。
        data = show_comment_item(comment, True)
        self.assertIsNotNone(data)
        s = get_max_articleid_commentid()
        self.assertIsNotNone(s)

        #psj: 最后调用一次发信函数，确认只有普通评论（非回复）的情况下也不会报错。
        from comments.utils import send_comment_email
        send_comment_email(comment)
