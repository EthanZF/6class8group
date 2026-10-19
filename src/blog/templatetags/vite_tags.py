"""
Vite资源加载Django模板标签
用于在Django模板中加载Vite构建的前端资源

使用方法：
    {% load vite_tags %}
    {% vite_js 'src/main.js' %}
    {% vite_css 'src/styles/main.css' %}
"""

import glob
import json
import os
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.templatetags.static import static
import logging

register = template.Library()
logger = logging.getLogger(__name__)

# 缓存manifest内容
_manifest_cache = None


def load_manifest():
    """
    加载Vite生成的manifest.json文件
    包含所有构建资源的映射关系
    """
    global _manifest_cache

    # 开发模式下不使用缓存，每次都重新读取
    # 生产模式下使用缓存提高性能
    if not settings.DEBUG and _manifest_cache is not None:
        return _manifest_cache

    # manifest文件路径
    manifest_path = os.path.join(
        settings.BASE_DIR,
        'blog/static/blog/dist/.vite/manifest.json'
    )

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            # 仅在生产模式下缓存
            if not settings.DEBUG:
                _manifest_cache = manifest
            logger.info(f'✅ Vite manifest loaded from: {manifest_path}')
            return manifest
    except FileNotFoundError:
        # 开发模式下manifest可能不存在
        logger.warning(f'⚠️  Vite manifest not found: {manifest_path}')
        logger.warning('🔧 Running in development mode. Make sure Vite dev server is running.')
        return {}
    except json.JSONDecodeError as e:
        logger.error(f'❌ Failed to parse manifest.json: {e}')
        return {}


def _find_built_assets():
    """
    manifest 缺失时，扫描 dist 目录查找已构建的 main-* 产物
    返回 (js_url, css_url)，找不到的项为 None
    """
    dist_dir = os.path.join(settings.BASE_DIR, 'blog/static/blog/dist')
    js_files = glob.glob(os.path.join(dist_dir, 'js', 'main-*.js'))
    css_files = glob.glob(os.path.join(dist_dir, 'css', 'main-*.css'))
    js_url = static(f'blog/dist/js/{os.path.basename(js_files[0])}') if js_files else None
    css_url = static(f'blog/dist/css/{os.path.basename(css_files[0])}') if css_files else None
    return js_url, css_url


@register.simple_tag
def vite_asset(entry_name):
    """
    获取Vite构建资源的URL

    Args:
        entry_name: 入口文件名，如 'src/main.js'

    Returns:
        资源URL

    用法：
        {% vite_asset 'src/main.js' %}
    """
    manifest = load_manifest()

    if entry_name in manifest:
        file_path = manifest[entry_name]['file']
        return static(f'blog/dist/{file_path}')

    # 开发模式回退到Vite开发服务器
    vite_dev_server = getattr(settings, 'VITE_DEV_SERVER_URL', 'http://localhost:5173')
    return f'{vite_dev_server}/{entry_name}'


@register.simple_tag
def vite_js(entry_name='src/main.js'):
    """
    加载Vite构建的JavaScript资源

    在开发模式下，会加载Vite开发服务器的资源（带HMR）
    在生产模式下，会加载构建后的资源

    Args:
        entry_name: 入口文件名，默认 'src/main.js'

    Returns:
        HTML script标签

    用法：
        {% vite_js 'src/main.js' %}
    """
    manifest = load_manifest()

    # 开发模式：使用Vite开发服务器
    if not manifest:
        # manifest 缺失但构建产物存在时，直接使用构建产物
        js_url, css_url = _find_built_assets()
        if js_url:
            css_html = f'    <link rel="stylesheet" href="{css_url}">\n' if css_url else ''
            logger.info(f'✅ Vite manifest missing, using built assets: {js_url}')
            return mark_safe(f'''
    <!-- Vite构建产物（manifest缺失，目录扫描回退） -->
{css_html}    <script type="module" crossorigin src="{js_url}"></script>
''')

        vite_dev_server = getattr(settings, 'VITE_DEV_SERVER_URL', 'http://localhost:5173')
        return mark_safe(f'''
            <!-- Vite开发模式 -->
            <script type="module" src="{vite_dev_server}/@vite/client"></script>
            <script type="module" src="{vite_dev_server}/{entry_name}"></script>
        ''')

    # 生产模式：使用构建后的文件
    if entry_name not in manifest:
        logger.error(f'❌ Entry "{entry_name}" not found in manifest')
        return ''

    entry_data = manifest[entry_name]
    file_path = entry_data['file']
    js_url = static(f'blog/dist/{file_path}')

    # 收集所有CSS文件
    css_html = ''
    if 'css' in entry_data:
        for css_file in entry_data['css']:
            css_url = static(f'blog/dist/{css_file}')
            css_html += f'    <link rel="stylesheet" href="{css_url}">\n'

    return mark_safe(f'''
    <!-- Vite生产模式 -->
{css_html}    <script type="module" crossorigin src="{js_url}"></script>
''')


@register.simple_tag
def vite_css(entry_name='src/styles/main.css'):
    """
    加载Vite构建的CSS资源

    注意：在开发模式下，CSS通过JS注入，不需要单独加载

    Args:
        entry_name: 入口文件名，默认 'src/styles/main.css'

    Returns:
        HTML link标签

    用法：
        {% vite_css 'src/styles/main.css' %}
    """
    manifest = load_manifest()

    # 开发模式：CSS通过Vite的HMR自动注入
    if not manifest:
        return ''

    # 生产模式：加载构建后的CSS
    if entry_name not in manifest:
        logger.error(f'❌ Entry "{entry_name}" not found in manifest')
        return ''

    file_path = manifest[entry_name]['file']
    css_url = static(f'blog/dist/{file_path}')
    return mark_safe(f'<link rel="stylesheet" href="{css_url}">')


@register.simple_tag
def vite_preload(entry_name):
    """
    预加载Vite资源

    用于优化关键资源的加载速度

    Args:
        entry_name: 入口文件名

    Returns:
        HTML link preload标签

    用法：
        {% vite_preload 'src/main.js' %}
    """
    manifest = load_manifest()

    if not manifest or entry_name not in manifest:
        return ''

    file_path = manifest[entry_name]['file']
    url = static(f'blog/dist/{file_path}')

    # 根据文件类型决定预加载方式
    if file_path.endswith('.js'):
        return mark_safe(f'<link rel="modulepreload" crossorigin href="{url}">')
    elif file_path.endswith('.css'):
        return mark_safe(f'<link rel="preload" href="{url}" as="style">')
    else:
        return mark_safe(f'<link rel="preload" href="{url}">')


@register.simple_tag
def is_vite_dev_mode():
    """
    判断是否处于Vite开发模式

    Returns:
        True/False

    用法：
        {% is_vite_dev_mode as dev_mode %}
        {% if dev_mode %}
            <div class="dev-banner">开发模式</div>
        {% endif %}
    """
    manifest = load_manifest()
    return not bool(manifest)


@register.simple_tag
def vite_dev_server_url():
    """
    获取Vite开发服务器URL

    Returns:
        开发服务器URL

    用法：
        {% vite_dev_server_url %}
    """
    return getattr(settings, 'VITE_DEV_SERVER_URL', 'http://localhost:5173')
