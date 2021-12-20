import setuptools

# Reads the content of your README.md into a variable to be used in the setup below
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

version_number = "0.1.0"

setuptools.setup(
    name='cythonbuilder',
    packages=['cythonbuilder'],
    version=f'{version_number}',
    license='MIT',
    description='CythonBuilder; automated compiling and packaging of Cython code',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Mike Huls',
    author_email='mikehuls42@gmail.com',
    url='https://github.com/mike-huls/cythonbuilder',
    project_urls={
        "Source": "https://github.com/mike-huls/cythonbuilder/",
        "Bug Tracker": "https://github.com/mike-huls/cythonbuilder/issues",
        "Documentation": "https://github.com/mike-huls/cythonbuilder/blob/main/README.md/",
    },
    entry_points={
        'console_scripts': [
            'cythonbuilder=cythonbuilder.cythonbuilder:main',
            'cybuilder=cythonbuilder.cythonbuilder:main'
        ],
    },
    install_requires=['Cython'],  # list all packages that your package uses
    python_requires='>=3',
    keywords=["pypi", "Cython", "setup", "packaging", "compilation"],  # descriptive meta-data
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Compilers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    download_url=f"https://github.com/mike-huls/cythonbuilder/archive/refs/tags/v{version_number}.tar.gz",
)