import os

from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), "README.md")) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="djinsight",
    version="0.3.3",
    packages=find_packages(),
    include_package_data=True,
    license="MIT",
    description="MCP-first analytics for Django/Wagtail package for tracking page view statistics with Redis and async processing",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/krystianmagdziarz/djinsight",
    author="MDigital",
    author_email="kontakt@mdigital.com.pl",
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Wagtail",
        "Framework :: Wagtail :: 3",
        "Framework :: Wagtail :: 4",
        "Framework :: Wagtail :: 5",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[
        "Django>=3.2",
        "wagtail>=3.0",
        "redis>=4.0.0",
        "celery>=5.0.0",
        "django-redis>=5.0.0",
        "django-environ>=0.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-django>=4.0",
            "black>=22.0",
            "flake8>=4.0",
        ],
    },
    python_requires=">=3.8",
    keywords="django wagtail analytics statistics page views redis celery",
)
