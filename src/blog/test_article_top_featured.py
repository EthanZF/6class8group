# 文章置顶与精选功能测试
# 覆盖：字段默认值、列表排序、精选筛选、后台批量操作、页面上的标记显示
from django.test import TestCase
from django.utils import timezone

from blog.admin import (set_article_top, unset_article_top,
                        set_article_featured, unset_article_featured)
from blog.models import Article
from djangoblog.test_base import BaseTestCase


class ArticleTopFeaturedModelTest(BaseTestCase):
    """模型层：字段与排序"""

    def setUp(self):
        super().setUp()
        from djangoblog.utils import cache
        cache.clear()

    def test_new_article_flags_default_false(self):
        """新建文章默认既不是置顶也不是精选"""
        article = self.create_article(title='普通文章')
        self.assertFalse(article.is_top)
        self.assertFalse(article.is_featured)

    def test_top_article_sorts_first(self):
        """置顶文章应排在列表最前面（依赖 Meta.ordering）"""
        old = self.create_article(title='较早的文章')
        new = self.create_article(title='较新的文章')
        # 把发布时间拉开，确保默认顺序是「新的在前」
        Article.objects.filter(pk=old.pk).update(
            pub_time=timezone.now() - timezone.timedelta(days=5))
        Article.objects.filter(pk=new.pk).update(pub_time=timezone.now())

        titles = list(Article.objects.filter(status='p')
                      .values_list('title', flat=True))
        self.assertEqual(titles[0], '较新的文章')

        # 把较早的那篇设为置顶，它应当跑到第一位
        Article.objects.filter(pk=old.pk).update(is_top=True)
        titles = list(Article.objects.filter(status='p')
                      .values_list('title', flat=True))
        self.assertEqual(titles[0], '较早的文章')

    def test_featured_query_only_returns_featured(self):
        """精选查询只返回标记为精选的已发布文章"""
        self.create_article(title='普通文章')
        featured = self.create_article(title='精选文章')
        featured.is_featured = True
        featured.save()

        # 草稿即使标了精选也不该出现
        draft = self.create_article(title='精选草稿', status='d')
        draft.is_featured = True
        draft.save()

        qs = Article.objects.filter(type='a', status='p', is_featured=True)
        titles = list(qs.values_list('title', flat=True))
        self.assertIn('精选文章', titles)
        self.assertNotIn('普通文章', titles)
        self.assertNotIn('精选草稿', titles)


class ArticleTopFeaturedAdminActionTest(BaseTestCase):
    """后台批量操作"""

    def setUp(self):
        super().setUp()
        from djangoblog.utils import cache
        cache.clear()
        self.a1 = self.create_article(title='文章一')
        self.a2 = self.create_article(title='文章二')

    def test_set_and_unset_top(self):
        """批量设为置顶 / 取消置顶"""
        qs = Article.objects.filter(pk__in=[self.a1.pk, self.a2.pk])
        set_article_top(None, None, qs)
        self.assertEqual(Article.objects.filter(is_top=True).count(), 2)

        unset_article_top(None, None, Article.objects.filter(is_top=True))
        self.assertEqual(Article.objects.filter(is_top=True).count(), 0)

    def test_set_and_unset_featured(self):
        """批量设为精选 / 取消精选"""
        qs = Article.objects.filter(pk=self.a1.pk)
        set_article_featured(None, None, qs)
        self.assertTrue(Article.objects.get(pk=self.a1.pk).is_featured)
        self.assertFalse(Article.objects.get(pk=self.a2.pk).is_featured)

        unset_article_featured(None, None, Article.objects.filter(is_featured=True))
        self.assertFalse(Article.objects.get(pk=self.a1.pk).is_featured)


class ArticleTopFeaturedDisplayTest(BaseTestCase):
    """页面显示：首页精选区、列表标记、详情页标记"""

    def setUp(self):
        super().setUp()
        from djangoblog.utils import cache
        cache.clear()
        self.top = self.create_article(title='一篇置顶的文章')
        self.top.is_top = True
        self.top.is_featured = True
        self.top.save()

    def test_index_lists_top_article_first(self):
        """首页列表里置顶文章排第一"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        article_list = response.context['article_list']
        self.assertEqual(article_list[0].pk, self.top.pk)

    def test_index_has_featured_section(self):
        """首页出现精选区域，并含有精选文章的标题"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('featured_articles', response.context)
        self.assertEqual(len(response.context['featured_articles']), 1)
        self.assertContains(response, '精选')

    def test_list_shows_top_badge(self):
        """列表页显示「置顶」标记"""
        response = self.client.get('/')
        self.assertContains(response, '置顶')

    def test_detail_shows_badges(self):
        """详情页显示置顶与精选标记"""
        response = self.client.get(self.top.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '置顶')
        self.assertContains(response, '精选')

    def test_normal_article_has_no_badge(self):
        """普通文章本身不带置顶/精选标记

        注意：详情页的侧边栏也会渲染文章列表，若页面里有别的置顶文章，
        整页文本仍可能包含「置顶」二字，所以这里校验的是本篇文章的字段。
        """
        plain = self.create_article(title='一篇普通文章')
        response = self.client.get(plain.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['article'].is_top)
        self.assertFalse(response.context['article'].is_featured)
