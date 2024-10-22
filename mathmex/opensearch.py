from arq1thru3 import ArqMathSentenceTransformer
from opensearchpy import OpenSearch, helpers
from collections import OrderedDict
from collections import defaultdict
import configparser
import pprint
import re
import time
import string
import base64
import math
import os

# Get the absolute path to the configuration file
config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
model_path = os.path.join(os.path.dirname(__file__), 'arq1thru3-finetuned-all-mpnet-jul-27')




class ElasticSearchInterFace:
    """
    Provides commands needed to interact with ElasticSearch
    """

    def __init__(self,host='localhost',port=9200,username=None,password=None,model=None,config_path=None):
        # If a config path is defined read the variables from that file instead of the parameters
        if config_path:
            config = configparser.ConfigParser()
            config.read(config_path)
            username = config.get('OpenSearch', 'username')
            password = config.get('OpenSearch', 'password')
            
        auth = (username, password)
        self.es = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_compress=True,  # enables gzip compression for request bodies
            http_auth=auth,
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=60
        )
    
        if not self.es.ping():
            raise ValueError("Connection failed")

        self.model= ArqMathSentenceTransformer()

    def get_all_indices(self):
        return self.es.indices.get_alias("*")

    def create_index(self, index_name, mapping=None, settings=None):
        index_body = {"settings": {"index": {"number_of_shards": 4}}}

        if mapping is not None:
            index_body["mappings"] = mapping
        
        if settings is not None:
            index_body["settings"] = settings

        index = self.es.indices.create(index=index_name, body=index_body, ignore=400)
        print(index)
        return index

    def delete_index(self, index_name):
        try:
            return self.es.indices.delete(index=index_name, ignore=400)
        except Exception as inst:
            print(type(inst))
            print(inst.args)
            print(inst)
            return None

    # insert multiple sessions of data, list of dictionaries
    def insert_data(self, list_data, chunk_size=None):
        if chunk_size is None:
            response = helpers.bulk(self.es, list_data, refresh=True)
        else:
            response = helpers.bulk(self.es, list_data, chunk_size, refresh=True)
        return response

    # insert one session worth of data, data is a dictionary
    def insert_session(self, index_name, session_id, data):
        response = self.es.index(index=index_name, id=session_id, body=data)
        return response
        
    def read_top_k_index(self, index_name, k):
        res = self.es.search(
            index=index_name,
            body={"size": k, "query": {"match_all": {}}},
        )
        return res["hits"]["hits"]

    def autocomplete(self, index_names, query, k=5):
        if len(query) < 5:
            return ""

        words = re.split(r'\s+|-|_', query.lower())

        # get last token, the token we are completing
        prefix = words[-1]
        if len(prefix) < 3:
            return ""

        # new query is last 2 tokens, or the single token if it's the first word
        new_query = query if len(words) <= 1 else ' '.join(words[-2:])
        most_common_words = self.perform_autocomplete(index_names, prefix, k, query=new_query)

        if len(most_common_words) > 4:
            return list(most_common_words)[:k]

        most_common_words_prefix = self.perform_autocomplete(index_names, prefix, k, most_common_words=most_common_words)
        
        if len(most_common_words_prefix) > 4:
            return list(most_common_words_prefix)[:k]
            
        auto_correct_results = self.perform_autocorrect(index_names, prefix)

        for word in auto_correct_results:
            if word == prefix:
                continue
            most_common_words_prefix[word] = None
            if len(most_common_words_prefix) >= k:
                break
        
        return list(most_common_words_prefix)[:k]
    
    def perform_autocomplete(self, index_names, prefix, k, query=None, most_common_words=None):
        if query is None:
            query = prefix
        if most_common_words is None:
            most_common_words = OrderedDict()

        # Return highlighted body field to capture autocompleted word
        search_query = {
            'size': 0,  # Set size to 0 to exclude document hits
            'query': {
                'match_phrase_prefix': {
                    'body_text': {
                        'query': query
                    }
                }
            },
            'aggs': {
                'suggested_words': {
                    'terms': {
                        'field': 'body_text',
                        'include': f'{prefix}.*',  # Include only terms starting with the prefix
                        'size': k  # Adjust the size as needed
                    }
                }
            }
        }

        # Perform the search with aggregation
        response = self.es.search(index=index_names, body=search_query)
        suggested_words = response['aggregations']['suggested_words']['buckets']

        for bucket in suggested_words:
            word = bucket['key']
            if word == prefix or any(p in word for p in string.punctuation):
                continue
            most_common_words[word] = None
            if len(most_common_words) >= 5:
                break

        # Return the aggregation results
        return most_common_words

    def perform_autocorrect(self, index_names, token):
        # Perform a fuzzy search
        search_query = {
            "size": 6,  # In case it contains the token written
            "query": {
                "fuzzy": {
                    "body_text": {
                        "value": token,
                        "fuzziness": "AUTO"
                    }
                }
            },
            "highlight": {
                "fields": {
                    "body_text": {}
                }
            }
        }

        # Perform the search
        response = self.es.search(index=index_names, body=search_query)

        # Extract the matching terms from the hits
        corrected_tokens = {}
        for hit in response.get('hits', {}).get('hits', []):
            highlight_field = hit.get('highlight', {}).get('body_text', [])
            for highlight in highlight_field:
                # Extract the term(s) surrounded by <em> and </em> with regular expression
                matches = re.findall(r'<em>(.*?)</em>', highlight)
                for match in matches:
                    match = match.lower()
                    corrected_tokens[match] = corrected_tokens.get(match, 0) + 1


        # Sort by occurrence and keep the 5 most common unique tokens
        corrected_tokens = sorted(corrected_tokens.items(), key=lambda item: item[1], reverse=True)
        top_corrected_tokens = [token for token, _ in corrected_tokens][:6]

        # Return the list of corrected tokens
        return top_corrected_tokens
    
    def single_index_search(self, index_name, vector_query, query, n):
        knn_query = {}
        if index_name == 'images':
            knn_query = {
                "size": n,
                "query": {
                    "knn": {
                        "title_vector": {
                            "vector": vector_query,
                            "k": n
                        }
                    }
                }
            }
        else:   
            knn_query = {
                "size": n,
                "query": {
                    "knn": {
                        "body_vector": {
                            "vector": vector_query,
                            "k": n
                        }
                    }
                },
                # High lighting is temporarily disabled
                # "highlight": {
                #     "fields": {
                #         "body_text": {
                #             "type": "unified",
                #             "fragment_size": 1000000,  # Large enough to cover your text
                #             "number_of_fragments": 0
                #         }
                #     },
                #     "highlight_query": {
                #         "match": {
                #             "body_text": {
                #                 "query": query
                #             }
                #         }
                #     }
                # }
            }
        # Perform the search using execute_search
        response = self.es.search(index=index_name, body=knn_query)
        results = self.format_results(response)

        return results
    
    # Searches selected indices, sorts by score by comparing top elements from each results list
    # Returns the top 5 scored list
    def vector_search(self, index_names, query):
        start_time = time.time()
        vector_query = self.model.encode(query)

        num_indices = len(index_names)
        n = math.ceil(5 / num_indices)

        if num_indices == 0:
            return []
        elif num_indices == 1:
            return self.single_index_search(index_names[0], vector_query, query, n)

        all_results = []
        for index_name in index_names:
            all_results.append(self.single_index_search(index_name, vector_query, query, n))

        top_5_results = []
        indices = [0]*num_indices  # separate index for each list in all_results
        seen_definitions = set() # used to remove duplicates

        # run loop while we have less than 5 results and results left to go through
        while len(top_5_results) < 5 and min(indices) < n:
            tmp_results = []
            for i, index_lst in enumerate(all_results):
                # iterate index if duplicate, break if indice is less than n
                try:
                    while indices[i] < n and index_lst[indices[i]]['body'] in seen_definitions:
                        indices[i] += 1
                except Exception as e:
                    pass
                # continue to next list if current list is done
                if indices[i] >= n:
                    continue

                result = index_lst[indices[i]]
                body = result['body'] 

                seen_definitions.add(body)
                tmp_results.append(result)
                indices[i] += 1

            if tmp_results:
                tmp_results.sort(key=lambda x: x['score'], reverse=True)          
                top_5_results.extend(tmp_results)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Search completed in {elapsed_time:.2f} seconds")
        return top_5_results[:5]
    
    def format_results(self, response):      
        results = []

        # Find the maximum score to normalize the scores
        max_score = response["hits"]["max_score"]

        for hit in response["hits"]["hits"]:
            # Normalize the score from 0 to 1
            #normalized_score = hit["_score"] / max_score
            normalized_score = hit["_score"]

            resource = hit["_index"].replace("_", " ").title()
            if resource == 'Arxiv19To23':
                resource = 'arXiv'

            title = hit["_source"]["title"].title()

            body = None
            image_path=None

            if "image_path" in hit["_source"]:
                image_path = hit["_source"]["image_path"]
            else:
                body = hit["_source"]["body_text"]

            document = {
                "id": hit["_id"],
                "title": title,
                "link": hit["_source"]["link"],
                "body": body,
                "image_path":image_path,
                "resource": resource,
                "index":hit["_index"],
                "score": normalized_score
            }
            
            # Add the highlighted text to the document
            if "highlight" in hit:
                # Retrieve the highlighted text for the 'body_text' field
                highlighted_body_list = hit["highlight"]["body_text"]

                # Concatenate all the highlighted parts into a single string, separated by a space
                highlighted_body = "".join(highlighted_body_list)
                document["body"] = highlighted_body
            
            results.append(document)      

        return results
    
    def retrieve_entry(self,index,id):
        return self.format_results(self.es.search(
            index=index, 
            body={
                "query": {
                    "ids": {
                        "values": [id]
                        }
                    }
            }
        ))
if __name__=="__main__":
    es=ElasticSearchInterFace(config_path="C:\\Users\\James\\Projects\\mathmex-backend\\mathmex\\opensearch\\config.ini")