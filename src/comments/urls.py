#psj: 【模块】comments.urls —— 评论应用的 URL 路由表
#psj: 本模块把两个地址分派给 views.py 里对应的视图类：
#psj:   /article/<文章编号>/postcomment  -> CommentPostView，提交评论
#psj:   /comment/<评论编号>/react        -> CommentReactionView，读取/切换表情
#psj: 这个文件会被 djangoblog/urls.py 用 include 引入，所以路径前缀是空字符串，
#psj: 最终地址就是上面写的样子。app_name 用于模板里 {% url 'comments:xxx' %} 的命名空间。
from django.urls import path

from . import views

#psj: 命名空间。模板里写 {% url 'comments:postcomment' 文章id %} 时靠它定位到本文件。
app_name = "comments"
#psj: urlpatterns 是 Django 约定的路由列表，从上到下逐条匹配。
urlpatterns = [
    #psj: 提交评论。地址里带文章编号，视图从 self.kwargs['article_id'] 取用。
    path(
        'article/<int:article_id>/postcomment',
        views.CommentPostView.as_view(),
        name='postcomment'),
    #psj: 评论表情接口。同一个地址用 GET 取统计、用 POST 切换表情。
    path(
        'comment/<int:comment_id>/react',
        views.CommentReactionView.as_view(),
        name='comment_react'),
]
