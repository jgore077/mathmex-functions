from distutils.core import setup
import setuptools
setup(name='mathmex-functions',
      version='1.0',
      long_description=open('README.md').read(),
      long_description_content_type="text/markdown",
      description='Provides the vector search functionality for the mathmex system',
      author='James Gore',
      author_email='james.gore@maine.edu',
      url='https://github.com/jgore077/mathmex-functions',
      install_requires=[
        'numpy==1.26.4',
        'opensearch_py==2.2.0',
        'sentence_transformers==2.2.2',
        'tqdm==2.2.3'
      ],
      packages=setuptools.find_packages(),
     )