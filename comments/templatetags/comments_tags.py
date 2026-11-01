#psj: 【模块】comments.templatetags.comments_tags —— 评论应用的模板标签
#psj: 模板标签是把 Python 逻辑送进模板的通道。本模块提供两个：
#psj:   parse_commenttree  —— 递归取出一条评论下面所有的子评论（楼中楼展开用）；
#psj:   show_comment_item  —— 渲染单条评论的 HTML 片段（包含标签，会带模板和数据）。
#psj: 之所以不写在视图里，是因为评论列表要在模板里逐层渲染，
#psj: 用标签可以让模板自己控制展开层级，视图只负责把顶层评论查出来。
#psj: 注意目录名必须叫 templatetags，Django 只在这个名字的目录里自动发现标签库。
from django import template

#psj: register 是标签库的入口，后面用 @register.xxx 装饰器登记每个标签。
register = template.Library()


#psj: 【标签】取当前评论的所有子孙评论（展平成一层列表）。
#psj: 模板里的用法：{% parse_commenttree article_comments comment as childcomments %}
#psj: 参数 commentlist 是全部评论的查询集，comment 是当前这条评论。
#psj: 返回的 datas 是列表，不是查询集，因为递归结果没法用一条 SQL 表达。
@register.simple_tag
def parse_commenttree(commentlist, comment):
    """获得当前评论子评论的列表
        用法: {% parse_commenttree article_comments comment as childcomments %}
    """
    #psj: 收集结果的列表，递归过程中不断往里追加。
    datas = []

    #psj: 内部递归函数：找 c 的所有子评论，逐个收进 datas，再对每个子评论继续往下找。
    #psj: 它是个闭包，直接使用外层的 commentlist 和 datas。
    def parse(c):
        #psj: 从全量评论里筛出"父评论是 c 且已启用"的那些，即 c 的直接回复。
        #psj: 这里没有按层数限制，多层回复会一直递归下去。
        childs = commentlist.filter(parent_comment=c, is_enable=True)
        for child in childs:
            #psj: 先收下这个子评论，再以它为起点继续找它的回复。
            datas.append(child)
            parse(child)

    #psj: 从当前评论开始递归。
    parse(comment)
    #psj: 返回展平后的全部子孙评论。
    return datas


#psj: 【标签】渲染单条评论的片段。
#psj: 用的是 inclusion_tag：这个标签背后对应一个模板
#psj: comments/tags/comment_item.html，Django 会拿这里返回的字典去渲染它。
#psj: 参数 ischild 表示这条评论是顶层还是回复，用来决定缩进层级。
@register.inclusion_tag('comments/tags/comment_item.html')
def show_comment_item(comment, ischild):
    """评论"""
    #psj: 回复的缩进小一些（1 级），顶层评论缩进大一些（2 级），
    #psj: 这样视觉上能看出谁回复谁。
    depth = 1 if ischild else 2
    #psj: 返回的字典会成为该片段的上下文，模板里可以直接用 comment_item 和 depth。
    return {
        'comment_item': comment,
        'depth': depth
    }
