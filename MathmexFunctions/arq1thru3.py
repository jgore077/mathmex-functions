
MODEL_URL="https://cs.usm.maine.edu/~behrooz.mansouri/arq1thru3-finetuned-all-mpnet-jul-27/"
MODEL_NAME="arq1thru3-finetuned-all-mpnet-jul-27"

from .download_utils import downloadFilesAndCreateDirectorys
from sentence_transformers import SentenceTransformer
import os

class ArqMathSentenceTransformer():
    def __init__(self) -> None:
        self.model_path=os.path.join(os.path.dirname(__file__),MODEL_NAME)
        try:
            downloadFilesAndCreateDirectorys(self.model_path,MODEL_URL)
        except:
            raise ConnectionError(f"Could not connect to {MODEL_URL}") 
        self.model=SentenceTransformer(self.model_path)

    def encode(self,query):
        "encodes the query into a vector"
        return self.model.encode(query)