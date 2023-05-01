import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode, urldefrag
from stats import Stats
from collections import Counter
import hashlib
from hashlib import sha256, blake2b

stat = Stats()

def scraper(url, resp):
    # Means there was an error so stop execution of this file
    if resp.status != 200:
        return []

    global stat

    stat.set_allPages(url)
    stat.set_unique(urldefrag(url)[0])

    # Content of the page if there is content, else return empty list and stop execution
    content = resp.raw_response.content if resp.raw_response else None
    if not content:
        return []

    # Create soup and update word counter
    soup = BeautifulSoup(content, 'html.parser')

    # Check if the fingerprint is similar to any previously seen fingerprint
    text_content = soup.get_text()

    # If count words is greater than current max then update the longest file URL
    if count_words(text_content):
        stat.set_longest(url)

    links = extract_next_links(url, resp)
    print(len(stat.get_unique()))
    print()
    print(f"Longest File: {stat.get_longest()} with {stat.num} words")
    print()
    stat.print_top()
    for subdomain, pages in sorted(stat.get_subdomains().items()):
        print(f"{subdomain}, {len(pages)}")
    print()
    print()
    print()

    valid_links = [link for link in links if is_valid(link)]

    # Update subdomain information and return
    stat.add_subdomains(valid_links)
    return valid_links


def extract_next_links(url, resp) -> list:
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    if resp.status != 200:
        return []
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    text_info = soup.get_text()
    if not is_high_information_content(text_info):
            # If the page has low information content, skip further processing
            return []
    fingerprint = simhash(text_info)
    is_similar = any(similarity(fingerprint, fp) >= .85 for fp in stat.get_fingerprints())
    urls = []
    if not is_similar:
        stat.add_fingerprints(fingerprint)
        for a in soup.find_all('a', href=True):
            # Get the defragmented URL
            defrag_result = urldefrag(urljoin(url, a['href']))
            # Extract the URL string from the DefragResult object
            u = defrag_result.url
            if is_valid(u):
                urls.append(u)
    return urls


def is_valid(url):
    # Decide whether to crawl this url or not.
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        if not parsed.hostname:
            return False
            
        # Ensure they are apart of the allowed domains
        if not (parsed.hostname.lower().endswith("ics.uci.edu") or parsed.hostname.lower().endswith("cs.uci.edu") or parsed.hostname.lower().endswith("informatics.uci.edu") or parsed.hostname.lower().endswith("stat.uci.edu")):
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico|mpg|img|war|apk"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|ppsx"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print("TypeError for ", parsed)
        raise

def count_words(text: str) -> bool:
    global stat
    words = re.sub('[^0-9a-zA-Z]+', ' ', text).lower().split()
    temp = 0
    # Count words, ignoring stop words
    for word in words:
        temp += 1
        if len(word) > 1 and stat.is_valid(word):
            stat.add_words(word)

    if temp > stat.get_num():
        stat.set_num(temp)
        return True
    return False

def simhash(text):
    # Tokenize the text and calculate word frequencies (weights)
    tokens = text.split()
    token_weights = Counter(tokens)

    # Generate b-bit hash values for each token
    # Converts the resulting hash (which is in hexadecimal format) to an integer using base 16.
    hash_values = {token: int(blake2b(token.encode(), digest_size=8).hexdigest(), 16) for token in token_weights}

    # Create a b-dimensional vector V and update its components
    V = [0] * 64
    for token, weight in token_weights.items():
        hash_value = hash_values[token]
        for i in range(64):
            bit = (hash_value >> i) & 1
            V[i] += weight if bit == 1 else -weight

    # Generate the b-bit fingerprint
    fingerprint = 0
    for i, value in enumerate(V):
        if value > 0:
            fingerprint |= (1 << i)

    return fingerprint

def similarity(hash1, hash2):
    # Compute the similarity between two hash values (fingerprint)
    xor_result = hash1 ^ hash2
    different_bits = bin(xor_result).count('1')
    return 1 - (different_bits / 64)

def is_high_information_content(content):
    # Tokenize the content into words
    words = re.findall(r'[a-zA-Z0-9]+', content.lower())
    
    # Count the occurrences of each word
    word_counts = Counter(words)
    
    # Calculate the number of unique words
    num_unique_words = len(word_counts)
    
    # Calculate the total number of words
    total_words = len(words)
    
    # Calculate the information content ratio
    if total_words <= 50:
        return False  # Avoid division by zero and if there aren't very many tokens
    info_content_ratio = num_unique_words / total_words
    
    # Check if the ratio is above the threshold
    # return info_content_ratio >= .04
    return info_content_ratio >= .1
