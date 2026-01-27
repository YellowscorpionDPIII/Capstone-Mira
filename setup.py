"""Setup script for Mira platform."""
from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mira',
    version='1.0.0',
    author='Mira Team',
    description='Modular multi-agent AI workflow system for technical program management',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/YellowscorpionDPIII/Capstone-Mira',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.8',
    install_requires=[
        'Flask>=3.0.0',
        'Werkzeug>=3.0.1',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-benchmark>=4.0.0',
            'locust>=2.0.0',
        ],
        'vault': [
            'hvac>=1.2.1',
        ],
        'kubernetes': [
            'kubernetes>=28.1.0',
        ],
        'monitoring': [
            'watchdog>=3.0.0',
        ],
        'all': [
            'hvac>=1.2.1',
            'kubernetes>=28.1.0',
            'watchdog>=3.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'mira=mira.app:main',
        ],
    },
)
