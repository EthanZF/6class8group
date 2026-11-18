# -*- coding: utf-8 -*-
"""初始内容迁移：软件工程主题的分类、标签与 7 篇文章。

目的：任何人 clone 本项目、配置好数据库并执行 `python manage.py migrate` 之后，
打开站点即可看到这批文章，不需要额外导入 SQL 或执行其他命令。

内容定义在同目录的 `_seed_se_articles.py` 中；本迁移只是调用它。
全部操作使用 get_or_create，重复执行安全。
"""
from django.db import migrations

from blog.migrations import _seed_se_articles


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0010_article_is_top_featured'),
        ('accounts', '0002_alter_bloguser_options_remove_bloguser_created_time_and_more'),
    ]

    operations = [
        migrations.RunPython(
            code=_seed_se_articles.apply,
            reverse_code=_seed_se_articles.revert,
        ),
    ]
