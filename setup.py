from setuptools import setup, find_packages
import os

version = '1.0.5.dev0'

setup(name='slc.mail2news',
      version=version,
      description="Transfers emails to Plone news items",
      long_description=open("README.md").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Framework :: Plone :: 4.3",
        "Framework :: Plone :: 5.2",
        ],
      keywords='mail news rpc',
      author='Syslab.com',
      author_email='info@syslab.com',
      url='http://syslab.com/',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['slc'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'slc.zopescript',
      ],
      extras_require={
          'test': [
              'plone.app.testing',
              'plone.api',
          ],
      },
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone

      [console_scripts]
      mail_handler = slc.mail2news.scripts:mail_handler
      """,
      )
