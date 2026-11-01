#psj: 【模块】comments.forms —— 评论应用的表单层
#psj: 本模块只有一个 CommentForm，负责校验用户在评论框里提交的内容。
#psj: 它在文章详情页渲染评论框时使用，在 CommentPostView 里完成校验。
#psj: 之所以单独做一个表单类而不是手写校验，是因为 ModelForm 会按模型字段
#psj: 自动生成控件和校验规则（例如正文的 max_length=300）。
from django import forms
from django.forms import ModelForm

from .models import Comment


#psj: 【类】评论表单。
#psj: 表单只对用户开放"正文"一个字段，作者和文章由后端补，
#psj: 这样用户就没法通过改表单来冒充作者或把评论挂到别的文章下。
class CommentForm(ModelForm):
    #psj: 这个字段不在模型里，是额外加的隐藏字段，用来记录"回复的是哪条评论"。
    #psj: required=False 表示可空：顶层评论不填它；楼中楼回复时由前端写入父评论编号。
    #psj: 用 HiddenInput 是为了在页面上不显示输入框，只在提交时带过去。
    parent_comment_id = forms.IntegerField(
        widget=forms.HiddenInput, required=False)

    #psj: Meta 告诉 ModelForm 依据哪个模型、包含哪些字段。
    class Meta:
        model = Comment
        #psj: 只包含 body，所以表单里只有正文一个可见字段。
        fields = ['body']
