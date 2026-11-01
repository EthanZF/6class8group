"""
oauth 应用的表单模块。

本模块只有一个表单：补全邮箱表单。它是第三方登录流程中
"平台没有返回邮箱"时的中间环节，只收集邮箱，用户 id 通过隐藏域回传。

SJQ: 模块级注释，说明本模块的表单数量、字段构成以及它在登录流程中的位置。
"""
# SJQ: 从 django.contrib.auth.forms 间接拿到 forms 模块（更规范的写法是 from django import forms）
from django.contrib.auth.forms import forms
# SJQ: widgets 用于把邮箱输入框替换成带 placeholder 的控件
from django.forms import widgets


class RequireEmailForm(forms.Form):
    """
    补全邮箱表单。

    两个字段：email 供用户填写，oauthid 为隐藏域，用来告诉视图"这条邮箱要绑到哪条第三方记录"。
    """

    # SJQ: 邮箱必填，label 直接写中文
    email = forms.EmailField(label='电子邮箱', required=True)
    # SJQ: 隐藏域传递 oauthid；required=False 是因为它由服务端渲染时填入，不依赖用户输入
    oauthid = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        """初始化后替换邮箱控件的 widget，补上 placeholder 与 Bootstrap 样式类。"""
        # SJQ: 先走父类初始化，保证字段与初始值正常装配
        super(RequireEmailForm, self).__init__(*args, **kwargs)
        # SJQ: 替换成 EmailInput，type=email 让移动端弹出邮箱键盘
        self.fields['email'].widget = widgets.EmailInput(
            attrs={'placeholder': "email", "class": "form-control"})
