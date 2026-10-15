# zfh: 导入底层线程模块，用于异步发送邮件
import _thread
# zfh: 导入日志模块
import logging

# zfh: 导入 Django 信号模块
import django.dispatch
# zfh: 导入 Django 配置，读取 settings 中的全局设置
from django.conf import settings
# zfh: 导入后台操作日志模型，用于跳过其保存信号
from django.contrib.admin.models import LogEntry
# zfh: 导入用户登录、登出信号
from django.contrib.auth.signals import user_logged_in, user_logged_out
# zfh: 导入可发送多格式正文的邮件类
from django.core.mail import EmailMultiAlternatives
# zfh: 导入模型保存后触发的信号
from django.db.models.signals import post_save
# zfh: 导入信号接收器装饰器
from django.dispatch import receiver

# zfh: 导入评论模型
from comments.models import Comment
# zfh: 导入评论邮件通知发送函数
from comments.utils import send_comment_email
# zfh: 导入搜索引擎主动推送工具类
from djangoblog.spider_notify import SpiderNotify
# zfh: 导入缓存与缓存清理相关工具函数
from djangoblog.utils import cache, expire_view_cache, delete_sidebar_cache, delete_view_cache
# zfh: 导入获取当前站点的工具函数
from djangoblog.utils import get_current_site
# zfh: 导入第三方登录用户模型
from oauth.models import OAuthUser

# zfh: 创建本模块的日志记录器
logger = logging.getLogger(__name__)

# zfh: 定义第三方登录信号，携带用户id参数
oauth_user_login_signal = django.dispatch.Signal(['id'])
# zfh: 定义发送邮件信号，携带收件人、标题、内容参数
send_email_signal = django.dispatch.Signal(
    ['emailto', 'title', 'content'])


# zfh: 注册发送邮件信号的接收器
@receiver(send_email_signal)
# zfh: 发送邮件信号处理函数，从kwargs取出邮件信息并发送
def send_email_signal_handler(sender, **kwargs):
    # zfh: 取出收件人列表
    emailto = kwargs['emailto']
    # zfh: 取出邮件标题
    title = kwargs['title']
    # zfh: 取出邮件内容
    content = kwargs['content']

    # zfh: 构造多格式邮件对象
    msg = EmailMultiAlternatives(
        title,
        content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=emailto)
    # zfh: 将正文内容类型设为html
    msg.content_subtype = "html"

    # zfh: 延迟导入邮件发送日志模型
    from servermanager.models import EmailSendLog
    # zfh: 创建一条邮件发送日志记录
    log = EmailSendLog()
    # zfh: 记录邮件标题
    log.title = title
    # zfh: 记录邮件内容
    log.content = content
    # zfh: 记录收件人，多个地址用逗号拼接
    log.emailto = ','.join(emailto)

    # zfh: 捕获发送过程中的异常，避免中断流程
    try:
        # zfh: 发送邮件并取得成功发送的收件人数
        result = msg.send()
        # zfh: 根据发送数量判断发送是否成功
        log.send_result = result > 0
    # zfh: 发送异常时记录错误日志
    except Exception as e:
        # zfh: 记录失败邮箱号与异常信息
        logger.error(f"失败邮箱号: {emailto}, {e}")
        # zfh: 标记本次发送失败
        log.send_result = False
    # zfh: 保存邮件发送日志
    log.save()


# zfh: 注册第三方登录信号的接收器
@receiver(oauth_user_login_signal)
# zfh: 第三方登录信号处理函数，处理头像本地化与缓存清理
def oauth_user_login_signal_handler(sender, **kwargs):
    # zfh: 取出第三方用户id
    id = kwargs['id']
    # zfh: 按id查询第三方登录用户
    oauthuser = OAuthUser.objects.get(id=id)
    # zfh: 获取当前站点域名
    site = get_current_site().domain
    # zfh: 若头像存在且不包含本站域名，说明是外链头像
    if oauthuser.picture and not oauthuser.picture.find(site) >= 0:
        # zfh: 延迟导入头像保存函数
        from djangoblog.utils import save_user_avatar
        # zfh: 下载并保存头像到本地，回写新的头像地址
        oauthuser.picture = save_user_avatar(oauthuser.picture)
        # zfh: 保存更新后的用户信息
        oauthuser.save()

    # zfh: 清理侧边栏缓存
    delete_sidebar_cache()


# zfh: 注册所有模型保存后的信号接收器
@receiver(post_save)
# zfh: 模型保存后回调，按模型类型清理相关缓存并通知搜索引擎
def model_post_save_callback(
        sender,
        instance,
        created,
        raw,
        using,
        update_fields,
        **kwargs):
    # zfh: 后台操作日志不处理，直接返回
    if isinstance(instance, LogEntry):
        return

    # 检查是否只更新了浏览量
    # zfh: 判断本次保存是否仅更新了views字段
    is_update_views = update_fields == {'views'}
    # zfh: 仅更新浏览量时无需清理缓存
    if is_update_views:
        return  # 浏览量更新不需要清理缓存

    # 搜索引擎通知
    # zfh: 若该模型带有get_full_url方法，则具备可推送的详情页地址
    if 'get_full_url' in dir(instance):
        # zfh: 测试环境下不推送，避免打扰搜索引擎
        if not settings.TESTING:
            # zfh: 捕获推送异常，避免影响保存流程
            try:
                # zfh: 获取实例的完整访问地址
                notify_url = instance.get_full_url()
                # zfh: 通过百度推送接口提交该地址
                SpiderNotify.baidu_notify([notify_url])
            # zfh: 推送失败时记录错误日志
            except Exception as ex:
                # zfh: 记录搜索引擎通知失败的异常
                logger.error("notify sipder", ex)

    # 评论相关的缓存清理
    # zfh: 若保存的是评论对象，走评论的缓存清理逻辑
    if isinstance(instance, Comment):
        # zfh: 仅对已通过审核的评论做缓存清理与邮件通知
        if instance.is_enable:
            # zfh: 获取评论所属文章的访问路径
            path = instance.article.get_absolute_url()
            # zfh: 获取当前站点域名
            site = get_current_site().domain
            # zfh: 域名中带端口时，截取端口前的部分
            if site.find(':') > 0:
                # zfh: 去掉域名中的端口号
                site = site[0:site.find(':')]

            # zfh: 清除该文章详情页的整页缓存
            expire_view_cache(
                path,
                servername=site,
                serverport=80,
                key_prefix='blogdetail')

            # 清理评论相关缓存
            # zfh: 拼装该文章的评论缓存键
            comment_cache_key = 'article_comments_{id}'.format(
                id=instance.article.id)
            # zfh: 删除该文章的评论缓存
            cache.delete(comment_cache_key)
            # zfh: 按文章主键删除评论视图缓存
            delete_view_cache('article_comments', [str(instance.article.pk)])
            # zfh: 清理侧边栏缓存
            delete_sidebar_cache()
            # zfh: 清理SEO上下文处理器缓存
            cache.delete('seo_processor')

            # zfh: 新开线程异步发送评论邮件通知
            _thread.start_new_thread(send_comment_email, (instance,))

    # 文章相关的精细化缓存清理
    # zfh: 其他带get_full_url的模型，按具体类型精细化清理缓存
    elif 'get_full_url' in dir(instance):
        # zfh: 延迟导入文章、分类、标签模型
        from blog.models import Article, Category, Tag

        # zfh: 若保存的是文章对象
        if isinstance(instance, Article):
            # 清理文章列表首页缓存
            # zfh: 删除首页第一页缓存
            cache.delete('index_1')

            # 清理文章详情缓存
            # zfh: 拼装该文章的评论缓存键
            article_cache_key = f'article_comments_{instance.id}'
            # zfh: 删除该文章的评论缓存
            cache.delete(article_cache_key)

            # 清理分类相关缓存
            # zfh: 文章有分类时清理对应分类列表缓存
            if instance.category:
                # zfh: 取出分类名称
                category_name = instance.category.name
                # zfh: 删除该分类第一页的列表缓存
                cache.delete(f'category_list_{category_name}_1')

            # 清理标签相关缓存
            # zfh: 捕获标签查询异常，避免影响保存流程
            try:
                # zfh: 遍历文章的所有标签
                for tag in instance.tags.all():
                    # zfh: 删除该标签第一页的列表缓存
                    cache.delete(f'tag_{tag.name}_1')
            # zfh: 忽略标签尚未关联时的异常
            except Exception:
                pass  # 可能在创建时tags还未关联

            # 清理作者相关缓存
            # zfh: 文章有作者时清理对应作者列表缓存
            if instance.author:
                # zfh: 延迟导入slug生成函数
                from uuslug import slugify
                # zfh: 由作者用户名生成slug
                author_slug = slugify(instance.author.username)
                # zfh: 删除该作者第一页的列表缓存
                cache.delete(f'author_{author_slug}_1')

            # 清理归档缓存
            # zfh: 删除归档页缓存
            cache.delete('archives')

            # 清理侧边栏和上下文处理器缓存
            # zfh: 清理侧边栏缓存
            delete_sidebar_cache()
            # zfh: 清理SEO上下文处理器缓存
            cache.delete('seo_processor')

        # zfh: 若保存的是分类对象
        elif isinstance(instance, Category):
            # 清理分类相关缓存
            # zfh: 删除该分类第一页的列表缓存
            cache.delete(f'category_list_{instance.name}_1')
            # zfh: 清理侧边栏缓存
            delete_sidebar_cache()
            # zfh: 清理SEO上下文处理器缓存
            cache.delete('seo_processor')

        # zfh: 若保存的是标签对象
        elif isinstance(instance, Tag):
            # 清理标签相关缓存
            # zfh: 删除该标签第一页的列表缓存
            cache.delete(f'tag_{instance.name}_1')
            # zfh: 清理侧边栏缓存
            delete_sidebar_cache()

        # 其他模型的缓存清理
        # zfh: 其他带get_full_url的模型只做基础缓存清理
        else:
            # 对于其他有get_full_url的模型，清理基础缓存
            # zfh: 清理侧边栏缓存
            delete_sidebar_cache()
            # zfh: 清理SEO上下文处理器缓存
            cache.delete('seo_processor')


# zfh: 注册用户登录信号接收器
@receiver(user_logged_in)
# zfh: 注册用户登出信号接收器
@receiver(user_logged_out)
# zfh: 用户登录登出回调，清理侧边栏缓存
def user_auth_callback(sender, request, user, **kwargs):
    # zfh: 用户及其用户名有效时执行缓存清理
    if user and user.username:
        # zfh: 记录登录登出用户日志
        logger.info(user)
        # zfh: 清理侧边栏缓存
        delete_sidebar_cache()
        # cache.clear()
