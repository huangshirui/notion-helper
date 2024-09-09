from setuptools import setup, find_packages

setup(
    name='notion_helper',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'notion_client==2.2.1',
    ],
    author='Shirui',
    author_email='huangshirui@gmail.com',
    description='An enhanced component library for Notion API.',
    url='https://github.com/huangshirui/notion-helper',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)
