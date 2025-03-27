# Notion ORM: Python Object-Relational Mapping for Notion Databases

## Overview

Notion ORM is a powerful Python library that provides an object-relational mapping (ORM) interface for interacting with Notion databases. It simplifies data management by allowing developers to work with Notion databases using Pythonic object-oriented programming paradigms.

## Key Features

### 1. Database Model Abstraction
- Define Notion databases as Python classes
- Easily map Notion database properties to Python object attributes
- Support for various property types (Title, Rich Text, Date, URL, Checkbox, etc.)

### 2. CRUD Operations
- Create, Read, Update, and Delete (CRUD) operations on Notion database records
- Simple method calls for saving, updating, and deleting objects
- Advanced querying with filtering and sorting capabilities

### 3. Property Types
Supports a wide range of Notion property types:
- Title
- Rich Text
- Date
- URL
- Email
- Phone Number
- Checkbox
- Number
- Status
- Select
- Multi-Select
- Relation

### 4. Advanced Querying
- Filter database records using complex conditions
- Sort records by multiple properties
- Support for unique key constraints

## Quick Example

```python
class Task(Model):
    __database_id__ = 'your-notion-database-id'
    
    title = TitleProperty()
    description = RichTextProperty()
    due_date = DateProperty()
    status = StatusProperty()
    
    unique_keys = ['title']

# Create a new task
task = Task(title='My First Task', description='Getting started with Notion ORM')
task.save()

# Query tasks
tasks = Task.objects.filter({'status': {'equals': 'In Progress'}}).query()
```

## Requirements
- Python 3.7+
- notion-client library
- Environment variable `NOTION_SECRET` with your Notion integration token

## Installation
```bash
pip install git+https://github.com/huangshirui/notion-helper.git
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
MIT license
