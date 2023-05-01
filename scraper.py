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
    # fingerprint = simhash(soup.get_text())

    # Check if the fingerprint is similar to any previously seen fingerprint
    # is_similar = any(similarity(fingerprint, fp) >= .8 for fp in SEEN_FINGERPRINTS)
    text_content = soup.get_text()
    # if similarityCheck(text_content, url):
    #     return []
    # If count words is greater than current max then update the longest file URL
    if count_words(text_content):
        stat.set_longest(url)

    links = extract_next_links(url, resp)
    # print(f"URL: {url}")
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

    # return [link for link in links if is_valid(link)]

    valid_links = [link for link in links if is_valid(link)]
    # Update subdomain information
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
            # u = (normalize_url(defragment_url(urljoin(url, a['href']))))
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

        # if len(url) > 2083:
        #     return False

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


# def defragment_url(url):
#     # Parse the URL
#     parsed_url = urlparse(url)
#     # Set the fragment part to an empty string
#     parsed_url = parsed_url._replace(fragment='')
#     # Convert the parsed URL back to a string
#     defragmented_url = urlunparse(parsed_url)
#     return defragmented_url


# def normalize_url(url):
#     # Parse the URL
#     parsed_url = urlparse(url)
#     # Sort the query parameters alphabetically
#     sorted_query_params = sorted(parse_qsl(parsed_url.query))
#     # Reconstruct the URL with the sorted query parameters
#     normalized_url = parsed_url._replace(query=urlencode(sorted_query_params))
#     # Convert the parsed URL back to a string
#     return urlunparse(normalized_url)


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
    # # Step 1: Tokenize the text and calculate word frequencies (weights)
    # tokens = text.split()
    # token_weights = Counter(tokens)

    # # Step 2: Generate b-bit hash values for each token
    # # Converts the resulting hash (which is in hexadecimal format) to an integer using base 16.
    # # Calculates the modulo of the integer hash value with 2 ** 64 to limit the hash value to 64 bits.
    # hash_values = {token: int(sha256(token.encode()).hexdigest(), 16) % (2 ** 64) for token in token_weights}

    # # Step 3: Create a b-dimensional vector V and update its components
    # V = [0] * 64
    # for token, weight in token_weights.items():
    #     hash_value = hash_values[token]
    #     for i in range(64):
    #         bit = (hash_value >> i) & 1
    #         V[i] += weight if bit == 1 else -weight

    # # Step 4: Generate the b-bit fingerprint
    # fingerprint = 0
    # for i, value in enumerate(V):
    #     if value > 0:
    #         fingerprint |= (1 << i)

    # return fingerprint
    # Step 1: Tokenize the text and calculate word frequencies (weights)
    tokens = text.split()
    token_weights = Counter(tokens)

    # Step 2: Generate b-bit hash values for each token
    # Converts the resulting hash (which is in hexadecimal format) to an integer using base 16.
    hash_values = {token: int(blake2b(token.encode(), digest_size=8).hexdigest(), 16) for token in token_weights}

    # Step 3: Create a b-dimensional vector V and update its components
    V = [0] * 64
    for token, weight in token_weights.items():
        hash_value = hash_values[token]
        for i in range(64):
            bit = (hash_value >> i) & 1
            V[i] += weight if bit == 1 else -weight

    # Step 4: Generate the b-bit fingerprint
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


# def similarityCheck(url_content: str, url) -> bool:
#     global stat
#     h = hashlib.sha1()
#     h1 = hashlib.sha1()
#     for resp in stat.get_responses():
#         # Check to see if same page
#         if resp.url != url:
#             content = resp.raw_response.content if resp.raw_response else None
#             if not content:
#                 return False
#             # Create soup and update word counter
#             soup = BeautifulSoup(content, 'html.parser')
#             p_content = soup.get_text()
#             h.update(p_content.encode('utf-8'))
#             hash_page = h.hexdigest()
#             h1.update(url_content.encode('utf-8'))
#             hash_current = h1.hexdigest()
#             # threshold to compare and calculate similarity between the two
#             threshold = int(len(hash_page) * 0.2)
#             # Check if hash values are within threshold
#             if abs(int(hash_current, 16) - int(hash_page, 16)) <= threshold:
#                 # Less than threshold means similar
#                 return True
#     # None are similar
#     return False
