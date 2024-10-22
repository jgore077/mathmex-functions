from bs4 import BeautifulSoup
from tqdm import tqdm
import re
import requests
import urllib3
import os

# Suppress only the single warning from urllib3.
urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

SORT_REGEX="\?[a-zA-Z=]{3}\;[a-zA-Z=]{3}"
PARENT="Parent Directory"
def isDirectory(url):
    if(url.endswith('/')):
        return True
    else:
        return False

def findLinks(url,links=[]):
    page = requests.get(url,verify=False).content
    bsObj = BeautifulSoup(page, 'html.parser')
    maybe_directories = bsObj.findAll('a', href=True)
    directorys=[]
    for link in maybe_directories:
        href=link['href']
        text=link.text
        # We want to ignore the sorting hrefs and the parent href
        if re.match(SORT_REGEX,href) or text==PARENT:
            continue

        if(isDirectory(href)):
            newUrl = url + href  
            directorys.append(newUrl)
            continue
        links.append(url+href)
        # part of the initial
        # findLinks(newUrl) #recursion happening here
        
    for directory in directorys:
        findLinks(directory,links)
        
    return links

def download(link:str,file_path):
    response=requests.get(link,verify=False,stream=True)
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024

    with tqdm(total=total_size, unit="B", unit_scale=True) as progress_bar:
        progress_bar.set_description(file_path)
        with open(file_path, "wb") as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
                
def downloadFilesAndCreateDirectorys(base_dir,base_url):
    # int used to determine where to trim
    chop=len(base_url)
    
    links=findLinks(base_url)
    
    # make base directory
    if not os.path.exists(base_dir):
        os.mkdir(base_dir)
        
    for link in links:
        file_path=os.path.join(base_dir,link[chop:])
        dir_path=os.path.split(file_path)[0]
        # Make dir
        if not os.path.exists(dir_path):
            os.makedirs(dir_path,exist_ok=True)
        # Get file
        if not os.path.exists(file_path):
            download(link,file_path)