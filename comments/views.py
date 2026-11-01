#psj: 【模块】comments.views —— 评论应用的视图层
#psj: 本模块对外提供两个视图类：
#psj:   CommentPostView     —— 接收文章页提交的评论表单，校验后存库并跳回文章页；
#psj:   CommentReactionView —— 评论表情条的接口，GET 取统计、POST 切换表情。
#psj: 两者职责不同：前者是"表单提交 + 页面跳转"的传统流程，
#psj: 后者是给前端脚本调用的 JSON 接口，所以一个继承表单视图基类，一个直接继承 View。
#psj: 具体的字段校验在 forms.py，表结构和统计方法在 models.py，这里只做流程编排。
# Create your views here.
#psj: ValidationError 用来在"文章已关闭评论"时中断提交流程并给出提示。
from django.core.exceptions import ValidationError
#psj: HttpResponseRedirect 用于提交成功后跳回文章页；JsonResponse 用于接口返回 JSON。
from django.http import HttpResponseRedirect, JsonResponse
#psj: get_object_or_404：按条件查对象，查不到直接返回 404 页面，省掉手写 try/except。
from django.shortcuts import get_object_or_404
#psj: View 是 Django 最基础的类视图，自己写 get/post 方法的分支。
from django.views import View

#psj: BlogUser 用来按主键重新取一次完整的用户对象。
from accounts.models import BlogUser
#psj: Article 用于按 URL 里的 article_id 取文章。
from blog.models import Article
#psj: AuthenticatedFormView 是项目自定义的表单视图基类，
#psj: 它在 dispatch 阶段统一加了"必须登录"和"CSRF 校验"两道保护，
#psj: 所以下面的 CommentPostView 里不用再写登录判断。
from djangoblog.base_views import AuthenticatedFormView
#psj: CommentForm 只开放了正文一个字段，另外带一个隐藏字段 parent_comment_id。
from .forms import CommentForm
#psj: Comment 用于查父评论，CommentReaction 用于读取合法的表情取值列表。
from .models import Comment, CommentReaction


#psj: 【类】评论提交视图。URL 是 /article/<article_id>/postcomment（见 urls.py）。
#psj: 没有登录的用户进不来：基类的 dispatch 会先把他重定向到登录页。
class CommentPostView(AuthenticatedFormView):
    """
    评论提交视图

    使用 AuthenticatedFormView 基类，自动提供：
    - 登录验证（未登录用户会被重定向）
    - CSRF 保护
    """
    #psj: 指定使用的表单类，Django 会用它来校验 POST 上来的数据。
    form_class = CommentForm
    #psj: 表单校验失败时用哪个模板重新渲染。这里直接复用文章详情页，
    #psj: 因为评论框本来就嵌在文章详情页里。
    template_name = 'blog/article_detail.html'

    #psj: 【方法】处理 GET 请求。
    #psj: 这个地址本来只应该被表单 POST 过来，如果用 GET 直接访问，
    #psj: 就把它当成"打开这篇文章的评论锚点"，重定向回文章页，避免出现空白页。
    def get(self, request, *args, **kwargs):
        #psj: 从 URL 的命名捕获组里取出文章编号。
        article_id = self.kwargs['article_id']
        #psj: 按编号取文章；文章不存在时直接 404，不往下走。
        article = get_object_or_404(Article, pk=article_id)
        #psj: get_absolute_url() 是 Article 上定义的方法，返回文章详情页地址。
        url = article.get_absolute_url()
        #psj: 拼上 #comments 锚点，浏览器打开后会自动滚动到评论区。
        return HttpResponseRedirect(url + "#comments")

    #psj: 【方法】表单校验不通过时走这里（比如正文为空）。
    #psj: 处理方式是：把带错误信息的表单和文章对象一起交回模板，
    #psj: 让文章详情页重新渲染，并在评论框下面显示错误提示。
    def form_invalid(self, form):
        #psj: 同样先取到文章，模板渲染需要它。
        article_id = self.kwargs['article_id']
        article = get_object_or_404(Article, pk=article_id)

        #psj: render_to_response 会把 context 交给 template_name 指定的模板渲染成响应。
        return self.render_to_response({
            'form': form,
            'article': article
        })

    #psj: 【方法】表单校验通过后走这里，是整个评论功能的核心。
    #psj: 顺序是：取作者 → 取文章 → 判断能否评论 → 构造评论对象 → 补外键 → 落库 → 跳转。
    def form_valid(self, form):
        """提交的数据验证合法后的逻辑"""
        #psj: 当前登录用户，由基类的登录保护保证一定不是匿名用户。
        user = self.request.user
        #psj: 按主键再取一次用户对象。这里取的是 accounts.BlogUser 实例，
        #psj: 因为后面要赋给 comment.author 这个外键。
        author = BlogUser.objects.get(pk=user.pk)
        #psj: 文章编号来自 URL，不是来自表单，避免用户伪造。
        article_id = self.kwargs['article_id']
        article = get_object_or_404(Article, pk=article_id)

        #psj: 【核心判断】文章关闭评论时不再接受新评论。
        #psj: comment_status 是文章自己的评论开关（'c'=关闭），
        #psj: status 是文章状态，这里一并判断，兼容早期用文章状态表示关闭的写法。
        if article.comment_status == 'c' or article.status == 'c':
            #psj: 抛异常中断流程，页面上会显示这句提示。
            raise ValidationError("该文章评论已关闭.")
        #psj: form.save(False) 里的 False 表示"只构造对象、先别写数据库"。
        #psj: 因为此刻评论还缺 article 和 author 两个必填外键，直接存会报错。
        comment = form.save(False)
        #psj: 补上所属文章。
        comment.article = article
        #psj: 读站点配置，判断评论是否需要审核。
        #psj: 放函数内导入是为了避免 views 模块加载时就依赖 djangoblog.utils。
        from djangoblog.utils import get_blog_setting
        settings = get_blog_setting()
        #psj: 【核心逻辑】不需要审核时直接把 is_enable 置为 True，评论立刻可见；
        #psj: 需要审核时保持模型里 default=False 的初值，前台就看不到，等后台通过。
        if not settings.comment_need_review:
            comment.is_enable = True
        #psj: 补上作者。作者只能取当前登录用户，不能由表单传入。
        comment.author = author

        #psj: 【楼中楼】表单里的 parent_comment_id 是隐藏字段。
        #psj: 有值说明这次是"回复别人的评论"，取出父评论挂上去；
        #psj: 没值就是普通顶层评论，parent_comment 保持为空。
        if form.cleaned_data['parent_comment_id']:
            parent_comment = Comment.objects.get(
                pk=form.cleaned_data['parent_comment_id'])
            comment.parent_comment = parent_comment

        #psj: 到这里外键都补齐了，真正写库。参数 True 表示强制走插入。
        comment.save(True)
        #psj: 提交成功后跳回文章页，并带上新评论的锚点，
        #psj: 页面打开后会自动定位并高亮到刚才那条评论。
        return HttpResponseRedirect(
            "%s#div-comment-%d" %
            (article.get_absolute_url(), comment.pk))


#psj: 【类】评论表情接口。URL 是 /comment/<comment_id>/react（见 urls.py）。
#psj: 这个视图返回的是 JSON，不是页面，所以直接继承 View 而不是表单视图。
#psj: 同一个地址用 GET 取统计数据、用 POST 切换表情，符合 REST 的习惯。
class CommentReactionView(View):
    """
    评论 Emoji 反应 API
    GET /comment/<comment_id>/react - 获取 reactions（公开）
    POST /comment/<comment_id>/react - 切换 reaction（需要登录）
    """

    #psj: 【方法】GET：公开接口，任何人（包括未登录）都能读到某条评论的表情统计。
    #psj: 前端表情条初始渲染时调用它。
    def get(self, request, comment_id):
        """获取评论的 reactions 数据（公开访问）"""
        #psj: 只允许查已启用的评论：未审核通过的评论不该暴露表情数据。
        comment = get_object_or_404(Comment, id=comment_id, is_enable=True)

        # 传递用户信息，如果未登录则传递 None
        #psj: 已登录就传用户对象，未登录传 None，
        #psj: 这样 get_reactions_summary 就不会去查"当前用户点没点过"。
        user = request.user if request.user.is_authenticated else None
        #psj: 调用模型上的统计方法，逻辑都在 models.py 里。
        reactions_data = comment.get_reactions_summary(user)

        #psj: 统一包一层 success 字段，前端按 success 判断本次请求是否成功。
        return JsonResponse({
            'success': True,
            'reactions': reactions_data
        })

    #psj: 【方法】POST：切换表情。已点过就取消，没点过就点上。
    #psj: 与 GET 不同，这里要求登录，因为要记录是谁点的。
    def post(self, request, comment_id):
        # POST 需要登录验证
        #psj: 未登录直接返回 401（未授权），不去查库也不做任何修改。
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        # 获取评论（只有已启用的评论才能点赞）
        #psj: 同样只允许对已启用的评论表态。
        comment = get_object_or_404(Comment, id=comment_id, is_enable=True)

        # 获取 reaction 类型
        #psj: 表情类型由前端放在 POST 参数里传上来。
        reaction_type = request.POST.get('reaction_type')

        # 验证 reaction_type 是否合法
        #psj: 【核心校验】不能只信前端：取出模型的 choices，逐个比对，
        #psj: 不在允许范围内的值直接返回 400（请求参数错误）。
        valid_reactions = [choice[0] for choice in CommentReaction.REACTION_CHOICES]
        if reaction_type not in valid_reactions:
            return JsonResponse({
                'error': 'Invalid reaction type'
            }, status=400)

        # 切换 reaction（如果已存在则删除，否则创建）
        #psj: 【切换逻辑】get_or_create 依据 Meta 里的联合唯一约束，
        #psj: 找得到就返回已有记录（created=False），找不到就新建（created=True）。
        reaction, created = CommentReaction.objects.get_or_create(
            comment=comment,
            user=request.user,
            reaction_type=reaction_type
        )

        #psj: 已存在说明这次是"取消"，把记录删掉。
        if not created:
            # 已存在，删除它（取消点赞）
            reaction.delete()
            action = 'removed'
        else:
            #psj: 新建说明这次是"点上"，记录已经由 get_or_create 写好了。
            action = 'added'

        # 返回该评论的所有 reactions 统计
        #psj: 切换完把最新的统计一起返回，前端直接拿它刷新表情条，
        #psj: 不用再发一次请求。
        reactions_data = comment.get_reactions_summary(request.user)

        #psj: action 告诉前端这次到底是加上了还是取消了，前端据此做提示。
        return JsonResponse({
            'success': True,
            'action': action,
            'reactions': reactions_data
        })
