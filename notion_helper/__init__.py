from functools import lru_cache
from notion_client.helpers import iterate_paginated_api
from datetime import datetime
from zoneinfo import ZoneInfo
import os

local_timezone = ZoneInfo(os.environ.get('TZ', 'Asia/Shanghai'))
enable_link = True

@lru_cache(maxsize=1)
def get_bot_id(client):
    """
    获取当前bot的ID
    """
    bot = client.users.me()
    return bot['id']

def last_edited_by_bot(client, page_or_block):
    """
    判断一个Page或Block是否由当前bot修改
    返回True或False
    page_or_block: Page或Block的Notion API返回数据
    """
    bot_id = get_bot_id(client)
    return page_or_block['last_edited_by']['id'] == bot_id

def _str_to_datetime(str):
    """
    将Notion返回的日期或日期时间字符串转换为datetime对象（包含本地时区）
    """
    try:
        datetime_obj = datetime.strptime(str, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(local_timezone)
    except ValueError:
        try:
            datetime_obj = datetime.strptime(str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError('Invalid date or datetime format')
    return datetime_obj

def _convert_data(data):
    """
    将Notion返回的数据转换为Python对象
    """
    output = None
    if 'checkbox' in data:
        output = data['checkbox']
    elif 'created_time' in data:
        output = _str_to_datetime(data['created_time'])
    elif 'date' in data:
        date = data['date']
        if date:
            output = [_str_to_datetime(date['start'])]
            if date['end']:
                output.append(_str_to_datetime(date['end']))
    elif 'email' in data:
        output = data['email']
    elif 'files' in data:
        output = []
        files = data['files']
        for file in files:
            output.append(_convert_data(file))
    elif 'file' in data:
        output = {}
        name = data.get('name')
        if name:
            output['name'] = name
        file = data['file']
        output['url'] = file['url']
    elif 'external' in data:
        output = {}
        name = data.get('name')
        if name:
            output['name'] = name
        file = data['external']
        output['url'] = file['url']
    elif 'formula' in data:
        formula = data['formula']
        output = _convert_data(formula)
    elif 'last_edited_time' in data:
        output = _str_to_datetime(data['last_edited_time'])
    elif 'multi_select' in data:
        output = [ select['name'] for select in data['multi_select'] ]
    elif 'number' in data:
        output = data['number']
    elif 'phone_number' in data:
        output = data['phone_number']
    elif 'relation' in data:
        relations = data['relation']
        return [ relation['id'] for relation in relations ]
    elif 'rollup' in data:
        rollup = data['rollup']
        output = _convert_data(rollup)
    elif 'rich_text' in data:
        output = ''
        for chunk in data['rich_text']:
            url = chunk.get('href')
            if url and enable_link:
                output += f'[{chunk["plain_text"]}]({url})'
            else:
                output += chunk['plain_text']
    elif 'select' in data:
        select = data['select']
        if select:
            output = select['name']
    elif 'status' in data:
        status = data['status']
        if status:
            output = status['name']
    elif 'title' in data:
        output = ''
        for chunk in data['title']:
            output += chunk['plain_text']
    elif 'url' in data:
        output = data['url']
    elif 'unique_id' in data:
        unique_id = data['unique_id']
        output = f"{unique_id['prefix']}-{unique_id['number']}" if unique_id['prefix'] else str(unique_id['number'])
    else:
        print(data)
        # return None
    return output

def _block_to_text(data, table=None):
    """
    将Notion返回的block转换为文本
    table: 是否是表格
    """
    output = ''
    indentation = ''
    # print(data)
    if 'bookmark' in data:
        bookmark = data['bookmark']
        caption = bookmark['caption']
        caption_text = ''
        for chunk in caption:
            caption_text += chunk['plain_text']
        url = bookmark['url'] if  enable_link else ''
        if caption:
            output = f'[{caption_text}]({url})'
        else:
            output = url
    elif 'bulleted_list_item' in data:
        bulleted_list_item = data['bulleted_list_item']
        output = '* ' + _convert_data(bulleted_list_item)
        indentation = '\t'
    elif 'callout' in data:
        callout = data['callout']
        output = _convert_data(callout)
    elif 'child_database' in data:
        child_database = data['child_database']
        output = f"[{child_database['title']}]({get_url(data['id'])})"
    elif 'child_page' in data:
        child_page = data['child_page']
        output = f"[{child_page['title']}]({get_url(data['id'])})"
    elif 'code' in data:
        code = data['code']
        language = code['language']
        caption = code['caption']
        caption_text = ''
        for chunk in caption:
            caption_text += chunk['plain_text']
        content = _convert_data(code)
        output = f'{caption_text}\n\n```{language}\n{content}\n```'
    elif 'divider' in data:
        output = '---'
    elif 'embed' in data:
        embed = data['embed']
        caption = embed['caption']
        caption_text = ''
        for chunk in caption:
            caption_text += chunk['plain_text']
        output = f"[{caption_text}]({embed['url']})"
    elif 'equation' in data:
        equation = data['equation']
        output = f'$${equation["expression"]}$$'
    elif 'file' in data:
        file = data['file']
        caption = file['caption']
        caption_text = ''
        for chunk in caption:
            caption_text += chunk['plain_text']
        file_data = _convert_data(file)
        output = f"{caption_text}\n\n[{file_data['name']}]({file_data['url']})"
    elif 'heading_1' in data:
        output = '# ' + _convert_data(data['heading_1'])
    elif 'heading_2' in data:
        output = '## ' + _convert_data(data['heading_2'])
    elif 'heading_3' in data:
        output = '### ' + _convert_data(data['heading_3'])
    elif 'image' in data:
        image = data['image']
        caption = image['caption']
        caption_text = ''
        for chunk in caption:
            caption_text += chunk['plain_text']
        file_data = _convert_data(image)
        output = f'![{caption_text}]({file_data["url"]} "{caption_text}")'
    elif 'numbered_list_item' in data:
        numbered_list_item = data['numbered_list_item']
        output = '1. ' + _convert_data(numbered_list_item)
        indentation = '\t'
    elif 'paragraph' in data:
        output = _convert_data(data['paragraph'])
        # mention也是paragraph的一部分
    elif 'pdf' in data:
        pdf = data['pdf']
        caption = pdf['caption']
        caption_text = ''
        for chunk in caption:
            caption_text += chunk['plain_text']
        file_data = _convert_data(pdf)
        output = f"[{caption_text}]({file_data['url']})"
    elif 'quote' in data:
        quote = data['quote']
        output = '> ' + _convert_data(quote)
    elif 'table_row' in data:
        table_row = data['table_row']
        cells = table_row['cells']
        cells_text = []
        for cell in cells:
            cell_text = ''
            for text in cell:
                cell_text += f'[{text["plain_text"]}({text["href"]})]' if text['href'] else text['plain_text']
            cells_text.append(cell_text)
        if table:
            output = "| " + " | ".join(cells_text) + " |"
        else:
            output = "| " + " | ".join(cells_text) + " |\n"
            # 构建表格分隔线
            output += "| " + " | ".join(["---" for _ in cells_text]) + " |"
            table = True
    elif 'to_do' in data:
        to_do = data['to_do']
        checked = to_do['checked']
        checked_text = '- [x] ' if checked else '- [ ] '
        to_do_text = _convert_data(to_do)
        output = checked_text + to_do_text
        indentation = '\t'
    elif 'toggle' in data:
        toggle = data['toggle']
        output = '+ ' + _convert_data(toggle)
        indentation = '\t'
    elif 'video' in data:
        video = data['video']
        caption = video['caption']
        caption_text = ''
        for chunk in caption:
            caption_text += chunk['plain_text']
        file_data = _convert_data(video)
        if not caption_text:
            caption_text = file_data['url']
        output = f"[{caption_text}]({file_data['url']})"
    elif 'link_to_page' in data:
        link_to_page = data['link_to_page']
        display_text = 'Database Link' if link_to_page['type'] == 'database_id' else 'Page Link'
        output = f"[{display_text}]({get_url(link_to_page[link_to_page['type']])})"
    else:
        """
        无需显示的block，包括Breadcrumb, Column list and column, Synced block, Table of contents
        和不支持的block，包括Link Preview
        都将显示为空
        """
        print(data['type'], data)
        # return None
    return output, table, indentation

def get_page_title(page):
    """
    获取page的title
    """
    return next(_convert_data(prop) for prop in page['properties'].values() if prop['type'] == 'title')

def is_database_record(page, database_id=None):
    """
    判断一个Page是否为数据库记录
    返回True或False
    page: Page或Block的Notion API返回数据
    database_id: str，数据库ID，可选
    """
    if database_id:
        return page['parent']['type'] == 'database_id' and page['parent']['database_id'].replace('-', '') == database_id.replace('-', '')
    else:
        return page['parent']['type'] == 'database_id'

def update_database_info(client, database_id, title=None, icon: str='', description: str=''):
    """
    更新数据库标题、图标和描述
    返回更新后的数据库信息
    client: Notion Client
    database_id: str，数据库ID
    title: str，数据库标题，可选
    icon: str，数据库图标，可选，支持emoji和http链接。None表示删除图标，''表示不修改
    description: str，数据库描述，可选，支持markdown。None表示删除描述，''表示不修改
    """
    kwargs = {
        'database_id': database_id,
    }
    if title:
        kwargs['title'] = [{'type': 'text', 'text': {'content': title}}]
    if icon is None:
        kwargs['icon'] = None
    else:
        if icon:
            if icon.startswith('http'):
                kwargs['icon'] = {'type': 'external', 'external': {'url': icon}}
            else:
                kwargs['icon'] = {'type': 'emoji', 'emoji': icon}
    if description is None:
        kwargs['description'] = []
    else:
        if description:
            kwargs['description'] = [{'type': 'text', 'text': {'content': description}}]
        
    return client.databases.update(**kwargs)

def list_recent_pages(client, cutoff_time=None, page_size=100):
    """
    查找最近更新的Page，结果以last_edited_time的倒序排列
    返回一个生成器，每次返回一个Page
    client: Notion Client
    cutoff_time: datetime.datetime，最近更新时间
    page_size: int，查询API的分页数量，默认100，最大100
    """
    payload = {
        'filter': {'value': 'page', 'property': 'object'},
        'sort': {'direction': 'descending', 'timestamp': 'last_edited_time'},
        'page_size': page_size,
    }
    for page in iterate_paginated_api(
        client.search, **payload
    ):
        if cutoff_time and _str_to_datetime(page['last_edited_time']) <= cutoff_time:
            return
        yield page

def list_page_blocks(client, page_id, exclude_synced_block=True, page_size=100):
    """
    列出页面内的所有block
    返回一个生成器，每次返回一个block
    client: Notion Client
    page_id: str，页面ID
    page_size: int，查询API的分页数量，默认100，最大100
    """
    for block in iterate_paginated_api(
        client.blocks.children.list, block_id=page_id, page_size=page_size
    ):
        if block['has_children'] and block['type'] != 'child_page':
            if exclude_synced_block and 'synced_block' in block and not block['synced_block']['synced_from']:
                # 跳过从其它页面同步过来的block，但不包括本页面的sync block
                continue
            for child_block in list_page_blocks(client, block['id'], page_size):
                yield child_block
        yield block