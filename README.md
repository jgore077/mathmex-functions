# mathmex-functions
This is a python package that allows you to easily work with our OpenSearch interface and our fine-tuned sentence transformer.

## `opensearch`
This our personal interface to the OpenSearch search engine. It provides many functions that can manipulate the OpenSearch instance and fulfill queries.
```python
from MathmexFunctions import ElasticSearchInterFace 
dir(ElasticSearchInterFace)
```
It provides all these functions
```
['autocomplete', 'create_index', 'delete_index', 'format_results', 'get_all_indices', 'insert_data', 'insert_session', 'perform_autocomplete', 'perform_autocorrect', 'read_top_k_index', 'retrieve_entry', 'single_index_search', 'vector_search']
```
Instantiate a `ElasticSearchInterFace` object like this.
```
CONFIG_PATH="/path/to/config.ini"

# setting model=True will attach a `ArqMathSentenceTransformer` object to interface, this is required for vector querys
# if you use the config_path variable all the default parameters will be set to the contents of the config file

interface=ElasticSearchInterFace(host='localhost',port=9200,username='myOpenSearchUsername',password='myOpenSearchPassword',model=True,config_path=CONFIG_PATH)
```
Here is an example of what your config file should look like
```ini
[OpenSearch]
host = yourhost
port = yourport
username = yourusername
password = yourpassword
```

## `ArqMathSentenceTransformer`
This is our fine-tuned sentence transformer which is fine-tuned for mathematical querys and designed to deal with LaTeX.
<br/>

```python
from MathmexFunctions import ArqMathSentenceTransformer

transformer=ArqMathSentenceTransformer()

# The only function provided by this class is encode
# It returns a vector which is the encoded string
transformer.encode("What is an affine transform")
```