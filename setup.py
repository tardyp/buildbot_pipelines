from __future__ import absolute_import, division, print_function

from setuptools import find_packages, setup

setup(
    name='buildbot_pipelines',
    description="Pipelines DSL for Buildbot",
    long_description=open("README.rst").read(),
    version="0.1.0",
    keywords="buildbot pipeline ci",
    url="http://github.com/buildbot/buildbot_pipelines",
    author="Buildbot community",
    author_email="buildbot-devel@lists.sourceforge.net",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'buildbot>=0.9.8',  # for virtual builders features and renderable codebase
        'buildbot-www',
        'buildbot-console-view',
        'buildbot-worker',
        'klein',
        'PyYAML',
        'txrequests',
        'txgithub',
        'ldap3',
        'hyper_sh',
        'future'
    ],
)
