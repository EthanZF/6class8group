#psj: 【模块】comments.apps —— 评论应用的注册配置
#psj: Django 启动时会为每个应用生成一个 AppConfig，用来描述这个应用的身份信息。
#psj: 本模块只有一行实质内容：告诉 Django 这个应用的名字叫 comments。
#psj: 项目在 settings.py 的 INSTALLED_APPS 里加入 'comments' 后，Django 会自动找到这个类。
from django.apps import AppConfig


#psj: 【类】评论应用的配置类。
#psj: name 必须与应用所在包的路径一致，Django 靠它定位 models、views 等模块。
#psj: 本应用没有需要额外初始化的东西，所以不写 ready() 方法。
class CommentsConfig(AppConfig):
    name = 'comments'
