from notion_client import Client
from datetime import datetime
from notion_client.helpers import iterate_paginated_api, get_url
import inspect
from abc import ABCMeta, abstractmethod
import os
from notion_helper import _convert_data, _block_to_text

class IntegrityError(Exception):
    """
    数据完整性错误
    """
    pass

class Property(metaclass=ABCMeta):
    """
    属性基类
    """
    format = None

    def __init__(self, name=None):
        self.name = name

    @abstractmethod
    def dump_value(self, value):
        pass

    def dump(self, value):
        return {
            self.format: self.dump_value(value)
        }

    def load(self, data):
        return _convert_data(data)

    def filter_value(self, value, operator='='):
        if operator == '=':
            operator_key = 'equals'
        return {
            'property': self.name,
            self.format: {
                operator_key: value
            }
        }

class RawProperty(Property):
    """
    原始属性，不进行任何处理，value需要包括format在内完整的数据结构
    """
    def load(self, data):
        self.format = data['type']
        return data[self.format]

    def dump_value(self, value):
        return value
    
    def dump(self, value):
        return self.dump_value(value)

class ReadOnlyProperty(Property):
    """
    只读属性，包括：
    Created time, Files, Formula, Last edited time, Rollup, Unique ID
    """
    def dump_value(self, value):
        return None

class TitleProperty(Property):
    format = 'title'

    def dump_value(self, value:str):
        return [
            {
                'text': {
                    'content': value
                }
            }
        ]

class RichTextProperty(Property):
    format = 'rich_text'

    def dump_value(self, value:str):
        return [
            {
                'text': {
                    'content': value
                }
            }
        ]

class DateProperty(Property):
    format = 'date'

    def __date_text(self, date):
        return date.strftime('%Y-%m-%dT%H:%M:%S.000%z') if isinstance(date, datetime) else date.strftime('%Y-%m-%d')

    def dump_value(self, value):
        if isinstance(value, datetime):
            date_property = {'start': self.__date_text(value)}
        elif isinstance(value, list):
            date_property = {'start': self.__date_text(value[0])}
            if len(value) > 1:
                date_property['end'] = self.__date_text(value[1])
        else:
            raise ValueError('Invalid date type:', value)
        return date_property

    def filter_value(self, value, operator='='):
        return super().filter_value(self.__date_text(value[0]), operator=operator)

class UrlProperty(Property):
    format = 'url'

    def dump_value(self, value):
        return value

class EmailProperty(Property):
    format = 'email'

    def dump_value(self, value):
        return value

class PhoneNumberProperty(Property):
    format = 'phone_number'

    def dump_value(self, value):
        return value

class CheckboxProperty(Property):
    format = 'checkbox'

    def dump_value(self, value:bool):
        return value

class NumberProperty(Property):
    format = 'number'

    def dump_value(self, value):
        return value

class StatusProperty(Property):
    format = 'status'

    def dump_value(self, value:str):
        return {
            'name': value
        }

class SelectProperty(Property):
    format = 'select'

    def dump_value(self, value:str):
        return {
            'name': value
        }

class MultiSelectProperty(Property):
    format = 'multi_select'

    def dump_value(self, value:list):
        return [ {'name': item} for item in value ]

class RelationProperty(Property):
    format = 'relation'

    def __init__(self, related_model, name=None):
        super().__init__(name)
        self.related_model = related_model

    def dump_value(self, value):
        return [ {'id': id} for id in value ]

    def load(self, data):
        related_ids = _convert_data(data)
        return { related_id: str(self.related_model.objects.get(related_id)) for related_id in related_ids }


class Manager:
    def __init__(self, model):
        self.model = model
        self.client = Client(auth=os.environ.get('NOTION_SECRET'))
        self.query_filter = None
        self.query_order_by = None

    def get(self, id):
        """
        获取单个记录
        参考: https://developers.notion.com/reference/retrieve-a-page
        """
        response = self.client.pages.retrieve(page_id=id)
        properties = self.model._load_properties(response['properties'])
        return self.model(id=response['id'], **properties)

    def query(self):
        """
        返回所有记录
        参考: https://developers.notion.com/reference/post-database-query
        """
        query = {
            'database_id': self.model.__database_id__,
        }
        if self.query_filter:
            query['filter'] = self.query_filter
        if self.query_order_by:
            query['sorts'] = self.query_order_by
        results = []
        for page in iterate_paginated_api(
            self.client.databases.query, **query
        ):
            properties = self.model._load_properties(page['properties'])
            results.append(self.model(id=page['id'], **properties))
        return results

    def filter(self, filter):
        """
        筛选查询结果
        参考: https://developers.notion.com/reference/post-database-query-filter
        """
        self.query_filter = filter
        return self

    def order_by(self, *args):
        """
        对查询结果进行排序
        参考: https://developers.notion.com/reference/post-database-query-sort
        """
        self.query_order_by = args
        return self

class ModelBase(type):
    @property
    def objects(cls):
        return Manager(cls)

class Model(metaclass=ModelBase):
    """
    以Notion为数据库
    每一个Notion Database为一个表

    __database_id__: Notion的database_id
    """

    unique_keys = []

    def __init__(self, **kwargs):
        assert(self.__database_id__)
        self.client = Client(auth=os.environ.get('NOTION_SECRET'))
        self.id = None
        self.__properties = { attr: value for attr, value in inspect.getmembers(self.__class__) if isinstance(value, Property) }
        for property_name in self.__properties:
            setattr(self, property_name, None)
        for key, value in kwargs.items():
            if key in self.__properties:
                setattr(self, key, value)
            elif key == 'id':
                self.id = kwargs['id']
            else:
                raise Exception(f'Invalid property: {key}')

    def __dump_properties(self, exclude_unique_keys=False):
        """
        将对象导出为Notion API的格式
        """
        properties_define = { attr: value for attr, value in inspect.getmembers(self.__class__) if isinstance(value, Property) and not isinstance(value, ReadOnlyProperty)}
        data = {}
        for key, define in properties_define.items():
            if exclude_unique_keys and key in self.unique_keys:
                continue
            if getattr(self, key) is not None:
                name = define.name if define.name else key
                data[name] = define.dump(getattr(self, key))
        return data

    @classmethod
    def truncate(cls):
        for p in cls.objects.query():
            p.delete()

    @classmethod
    def _load_properties(cls, data):
        """
        将Notion API的返回数据加载为对象初始化字典
        """
        properties_define = { attr: value for attr, value in inspect.getmembers(cls) if isinstance(value, Property) }
        properties = {}
        for key, define in properties_define.items():
            name = define.name if define.name else key
            if name in data:
                properties[key] = define.load(data[name])
        return properties

    def save(self):
        """
        新建或保存对象
        没有指定id时，会新建一个对象
        有id时，会保存到原有对象
        """
        # 如果有id，则修改
        if self.id:
            return self.update()
        # 检查唯一性
        if self.unique_keys:
            if len(self.unique_keys) == 1:
                filter = getattr(self.__class__, self.unique_keys[0]).filter_value(getattr(self, self.unique_keys[0]))
            elif len(self.unique_keys) > 1:
                filter = {
                    'and': [ getattr(self.__class__, key).filter_value(getattr(self, key)) for key in self.unique_keys ]
                }
            objs = self.__class__.objects.filter(filter).query()
            if len(objs) > 0:
                raise IntegrityError('Unique constraint failed.')
        response = self.client.pages.create(
            parent={'database_id': self.__database_id__},
            properties=self.__dump_properties(),
            children=[],
        )
        self.id = response['id']
        return self

    def update(self):
        """
        保存对象的修改，必须要有id
        """
        if self.id:
            response = self.client.pages.update(page_id=self.id, properties=self.__dump_properties(exclude_unique_keys=True))
            return self
        else:
            raise ValueError('Object id is None.')

    def delete(self):
        """
        删除对象，必须要有id
        """
        if self.id:
            response = self.client.blocks.delete(block_id=self.id)
            self.id = None
        else:
            raise ValueError('Object id is None.')

    def upsert(self):
        """
        对象存在则修改，不存在则新建
        unique_keys: list或str，对象唯一条件，仅支持Checkbox、Date(不能包含结束日期时间)、Number、Rich text、Select、Status、ID
        """
        if len(self.unique_keys) == 1:
            filter = getattr(self.__class__, self.unique_keys[0]).filter_value(getattr(self, self.unique_keys[0]))
        elif len(self.unique_keys) > 1:
            filter = {
                'and': [ getattr(self.__class__, key).filter_value(getattr(self, key)) for key in self.unique_keys ]
            }
        else:
            return self.save()
        objs = self.__class__.objects.filter(filter).query()
        if len(objs) == 0:
            return self.save()
        elif len(objs) == 1:
            self.id = objs[0].id
            return self.update()
        else:
            raise ValueError('There are more than one object that meets the filtering criteria.')

    @property
    def detail(self):
        """
        以文本方式返回Page Blocks
        注意：这个方法每次都会实时从Notion API拉取数据
        """
        return self.__list_blocks(self.id).strip()

    def __list_blocks(self, parent_id, child_level=0):
        blocks = ''
        table = None
        for block in iterate_paginated_api(
            self.client.blocks.children.list, block_id=parent_id
        ):
            block_text, table, indentation = _block_to_text(block, table)
            if block_text:
                if not indentation and not table:
                    blocks += '\n'
                blocks += '\n' + child_level*indentation + block_text
            if block['has_children']:
                blocks += self.__list_blocks(block['id'], child_level+1)
        return blocks

    def __repr__(self):
        return self.id