# ZFH: 开发模式回退到 Vite 开发服务器（支持 HMR），生产模式读取 manifest.json 输出带哈希的构建产物
"""
Vite资源加载Django模板标签
用于在Django模板中加载Vite构建的前端资源

使用方法：
    {% load vite_tags %}
    {% vite_js 'src/main.js' %}
    {% vite_css 'src/styles/main.css' %}
"""

# ZFH: 标准库导入：json 解析 manifest，os 拼接磁盘路径，logging 输出加载状态
import json
import os
# ZFH: Django 导入：template 注册标签库，settings 读取 DEBUG 与路径，static 生成静态资源 URL
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.templatetags.static import static
import logging

# ZFH: 模板标签库实例，供模板通过 {% load vite_tags %} 使用
register = template.Library()
logger = logging.getLogger(__name__)

# 缓存manifest内容
# ZFH: 进程级 manifest 缓存，仅生产模式启用，避免每次渲染都读磁盘并解析 JSON
_manifest_cache = None


def load_manifest():
    """
    加载Vite生成的manifest.json文件
    包含所有构建资源的映射关系
    """
    # ZFH: 声明使用模块级缓存变量，读取并可能写入 _manifest_cache
    global _manifest_cache

    # 开发模式下不使用缓存，每次都重新读取
    # 生产模式下使用缓存提高性能
    # ZFH: 生产模式命中缓存直接返回，开发模式每次重新读取以获取最新的文件哈希
    if not settings.DEBUG and _manifest_cache is not None:
        return _manifest_cache

    # manifest文件路径
    # ZFH: manifest 固定位于 blog/static/blog/dist/.vite/manifest.json
    manifest_path = os.path.join(
        settings.BASE_DIR,
        'blog/static/blog/dist/.vite/manifest.json'
    )

    # ZFH: 读取并解析 manifest，文件缺失或 JSON 非法时都退化为空字典
    try:
        # ZFH: 显式指定 UTF-8，避免中文文件名或注释导致解码失败
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            # 仅在生产模式下缓存
            # ZFH: 只在生产模式写入缓存，开发模式保持实时刷新
            if not settings.DEBUG:
                _manifest_cache = manifest
            logger.info(f'✅ Vite manifest loaded from: {manifest_path}')
            return manifest
    # ZFH: 开发环境通常还没构建，manifest 不存在属正常情况，回退到 Vite dev server
    except FileNotFoundError:
        # 开发模式下manifest可能不存在
        logger.warning(f'⚠️  Vite manifest not found: {manifest_path}')
        logger.warning('🔧 Running in development mode. Make sure Vite dev server is running.')
        return {}
    # ZFH: manifest 内容损坏时记录错误并返回空字典，避免整个页面 500
    except json.JSONDecodeError as e:
        logger.error(f'❌ Failed to parse manifest.json: {e}')
        return {}


# ZFH: simple_tag vite_asset：把入口名解析为构建后的静态文件 URL，缺失时回退到开发服务器
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

    # ZFH: 命中时取 file 字段（带内容哈希的文件名），再交给 static 生成最终 URL
    if entry_name in manifest:
        file_path = manifest[entry_name]['file']
        return static(f'blog/dist/{file_path}')

    # 开发模式回退到Vite开发服务器
    # ZFH: 未构建时退化为 Vite 开发服务器地址，可用 settings.VITE_DEV_SERVER_URL 覆盖
    vite_dev_server = getattr(settings, 'VITE_DEV_SERVER_URL', 'http://localhost:5173')
    return f'{vite_dev_server}/{entry_name}'


# ZFH: simple_tag vite_js：输出入口对应的 <script type="module"> 标签，并附带其拆分出的 CSS
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
    # ZFH: manifest 为空说明处于开发模式，注入 vite client 以启用热更新
    if not manifest:
        vite_dev_server = getattr(settings, 'VITE_DEV_SERVER_URL', 'http://localhost:5173')
        return mark_safe(f'''
            <!-- Vite开发模式 -->
            <script type="module" src="{vite_dev_server}/@vite/client"></script>
            <script type="module" src="{vite_dev_server}/{entry_name}"></script>
        ''')

    # 生产模式：使用构建后的文件
    # ZFH: 生产模式下找不到入口说明构建配置有问题，记录错误并返回空串
    if entry_name not in manifest:
        logger.error(f'❌ Entry "{entry_name}" not found in manifest')
        return ''

    # ZFH: 入口信息中 file 是构建产物路径，css 是拆分出的样式文件列表
    entry_data = manifest[entry_name]
    file_path = entry_data['file']
    js_url = static(f'blog/dist/{file_path}')

    # 收集所有CSS文件
    css_html = ''
    # ZFH: 逐个生成 link 标签，保证入口样式先于脚本加载，避免样式闪烁
    if 'css' in entry_data:
        for css_file in entry_data['css']:
            css_url = static(f'blog/dist/{css_file}')
            css_html += f'    <link rel="stylesheet" href="{css_url}">\n'

    # ZFH: 脚本加 crossorigin，匹配 Vite 产物按模块跨域加载的方式
    return mark_safe(f'''
    <!-- Vite生产模式 -->
{css_html}    <script type="module" crossorigin src="{js_url}"></script>
''')


# ZFH: simple_tag vite_css：单独输出入口对应的样式 link 标签，开发模式下由 JS 注入故返回空串
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
    # ZFH: 开发模式无需额外 link，Vite 的 HMR 会通过 JS 注入样式
    if not manifest:
        return ''

    # 生产模式：加载构建后的CSS
    # ZFH: 入口缺失时记录错误并返回空串，避免模板渲染报错
    if entry_name not in manifest:
        logger.error(f'❌ Entry "{entry_name}" not found in manifest')
        return ''

    file_path = manifest[entry_name]['file']
    css_url = static(f'blog/dist/{file_path}')
    return mark_safe(f'<link rel="stylesheet" href="{css_url}">')


# ZFH: simple_tag vite_preload：为关键资源生成 preload/modulepreload 提示，加速首屏加载
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

    # ZFH: 开发模式或入口缺失时不做预加载，直接返回空串
    if not manifest or entry_name not in manifest:
        return ''

    file_path = manifest[entry_name]['file']
    url = static(f'blog/dist/{file_path}')

    # 根据文件类型决定预加载方式
    # ZFH: JS 用 modulepreload，CSS 用 as="style" 的 preload，其他资源退化为普通 preload
    if file_path.endswith('.js'):
        return mark_safe(f'<link rel="modulepreload" crossorigin href="{url}">')
    elif file_path.endswith('.css'):
        return mark_safe(f'<link rel="preload" href="{url}" as="style">')
    else:
        return mark_safe(f'<link rel="preload" href="{url}">')


# ZFH: simple_tag is_vite_dev_mode：manifest 为空即视为开发模式，模板可据此显示调试提示
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


# ZFH: simple_tag vite_dev_server_url：返回 Vite 开发服务器地址，默认 http://localhost:5173
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
