#!/usr/bin/python
# -*- coding:Utf-8 -*-

from setuptools import setup

setup(name='ppub',
      version='0.3',
      description='A simple epub reader written with pygtk and pywebkit.',
      author='Thanasis Georgiou',
      long_description=open("README").read(),
      author_email='sakisds@gmx.com',
      url='https://github.com/sakisds/pPub',
      #install_requires=['pygtk>=0.9.9.1', 'pywebkitgtk'],
      license= 'gplv2',
      scripts=['ppub'],
      keywords='epub ebook reader gtk',
     )

# vim:set shiftwidth=4 tabstop=4 expandtab:
