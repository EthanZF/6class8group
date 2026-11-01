#psj: 【模块】comments.utils —— 评论应用的邮件通知工具
#psj: 本模块只有一个发信函数，作用是评论提交成功后给相关人发一封提醒邮件：
#psj:   1）给评论作者本人发一封"感谢评论"，里面附文章链接；
#psj:   2）如果这条评论是回复，再给被回复的人发一封"你的评论收到回复"，附回复内容。
#psj: 真正的发信动作由 djangoblog.utils.send_email 完成，这里只负责拼标题和正文。
#psj: 邮件模板用 gettext_lazy 包起来，是为了支持多语言（项目里有 locale 目录）。
import logging

from django.utils.translation import gettext_lazy as _

#psj: get_current_site 取当前站点域名，用来拼邮件里的完整链接；
#psj: send_email 是项目里统一的发信封装，内部会记录发送日志。
from djangoblog.utils import get_current_site
from djangoblog.utils import send_email

#psj: 按模块名建 logger，发信失败时把错误记下来，不影响评论本身已经保存成功这件事。
logger = logging.getLogger(__name__)


#psj: 【函数】给评论相关人员发提醒邮件。
#psj: 参数 comment 是刚保存的评论对象，函数内部通过它的外键取文章和作者邮箱。
def send_comment_email(comment):
    #psj: 取站点域名（如 example.com），下面用它拼 https 完整地址。
    site = get_current_site().domain
    #psj: 邮件标题，两封信共用。
    subject = _('Thanks for your comment')
    #psj: 文章完整地址：协议 + 域名 + 文章详情页路径。
    article_url = f"https://{site}{comment.article.get_absolute_url()}"
    #psj: 第一封信的正文：感谢评论，并给出文章链接方便回看。
    #psj: 这里用 % 格式化把文章地址和标题填进模板，避免拼接字符串出错。
    html_content = _("""<p>Thank you very much for your comments on this site</p>
                    You can visit <a href="%(article_url)s" rel="bookmark">%(article_title)s</a>
                    to review your comments,
                    Thank you again!
                    <br />
                    If the link above cannot be opened, please copy this link to your browser.
                    %(article_url)s""") % {'article_url': article_url, 'article_title': comment.article.title}
    #psj: 收件人就是评论作者本人。
    tomail = comment.author.email
    #psj: 正式发出第一封。
    send_email([tomail], subject, html_content)
    #psj: 第二段用 try 包住：发信可能因为对方邮箱异常而失败，
    #psj: 这时只记日志，不能让评论提交本身报错。
    try:
        #psj: 【核心判断】只有回复别人的评论（parent_comment 不为空）才发第二封。
        if comment.parent_comment:
            #psj: 第二封信的正文：告诉被回复的人"你的评论收到回复"，并附上回复内容。
            html_content = _("""Your comment on <a href="%(article_url)s" rel="bookmark">%(article_title)s</a><br/> has 
                   received a reply. <br/> %(comment_body)s
                    <br/>   
                    go check it out!
                     <br/>
                     If the link above cannot be opened, please copy this link to your browser.
                     %(article_url)s
                    """) % {'article_url': article_url, 'article_title': comment.article.title,
                            'comment_body': comment.parent_comment.body}
            #psj: 收件人换成父评论的作者。
            tomail = comment.parent_comment.author.email
            #psj: 发出第二封。
            send_email([tomail], subject, html_content)
    #psj: 捕获发信过程中的任何异常，记一条错误日志即可，流程继续。
    except Exception as e:
        logger.error(e)
