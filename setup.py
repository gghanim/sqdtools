from setuptools import setup, find_packages

setup(
    name='sqdtools',
    version='0.1.0',
    author='George Ghanim',
    author_email='gghanim@princeton.edu',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'starfile',
        'pandas',
        'numpy',
        'healpy',
        'matplotlib'],
    entry_points={
        'console_scripts': [
            'sqdt_cs2star = sqdtools.scripts.cs2star:cli',
            'sqdt_histogram = sqdtools.scripts.histogram:cli',
            'sqdt_histogram2d = sqdtools.scripts.histogram2D:cli',
            'sqdt_plotAssign = sqdtools.scripts.plot_assign:cli',
            'sqdt_rebalance = sqdtools.scripts.rebalance:cli',
        ],
    },
    python_requires='>=3.9'
)
