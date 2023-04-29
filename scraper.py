import re
# import hashlib
import string
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode
from bs4 import BeautifulSoup
# from simhash import Simhash
from collections import Counter, defaultdict
from hashlib import sha256

###
# Set to store SimHash values of seen pages
SEEN_FINGERPRINTS = set()

# Threshold for similarity
SIMILARITY_THRESHOLD = .8
###

# HIGH_INFO_THRESHOLD = .10
# SEEN_HASHES = set()
# BASE_PATH_COUNTS = {}

# Longest page variables
MAX_COUNT = 0
LONGEST_PAGE = None

# Unique pages
UNIQUE_URL = set()

# Subdomains in ics.uci.edu domain
SUBDOMAINS = defaultdict(set)

# Word counts
WORD_COUNTS = Counter()
STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', "aren't", 'as', 'at',
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', "can't", 'cannot', 'could', "couldn't",
    'did', "didn't", 'do', 'does', "doesn't", 'doing', "don't", 'down', 'during', 'each', 'few', 'for', 'from', 'further',
    'had', "hadn't", 'has', "hasn't", 'have', "haven't", 'having', 'he', "he'd", "he'll", "he's", 'her', 'here', "here's",
    'hers', 'herself', 'him', 'himself', 'his', 'how', "how's", 'i', "i'd", "i'll", "i'm", "i've", 'if', 'in', 'into',
    'is', "isn't", 'it', "it's", 'its', 'itself', "let's", 'me', 'more', 'most', "mustn't", 'my', 'myself', 'no', 'nor',
    'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own',
    'same', "shan't", 'she', "she'd", "she'll", "she's", 'should', "shouldn't", 'so', 'some', 'such', 'than', 'that', "that's",
    'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', "there's", 'these', 'they', "they'd", "they'll", "they're",
    "they've", 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', "wasn't", 'we', "we'd", "we'll",
    "we're", "we've", 'were', "weren't", 'what', "what's", 'when', "when's", 'where', "where's", 'which', 'while', 'who', "who's",
    'whom', 'why', "why's", 'with', "won't", 'would', "wouldn't", 'you', "you'd", "you'll", "you're", "you've", 'your', 'yours',
    'yourself', 'yourselves'
}


def scraper(url, resp):
    # links = extract_next_links(url, resp)
    # return [link for link in links if is_valid(link)]
##INITIAL
    global MAX_COUNT
    global LONGEST_PAGE
    global SUBDOMAINS

    # Check if the content type is PDF; if so, skip processing
    content_type = resp.raw_response.headers.get('Content-Type') if resp.raw_response else None
    if content_type and 'application/pdf' in content_type.lower():
        return []

    content = resp.raw_response.content if resp.raw_response else None

    if content:
        # Count words in the current page
        soup = BeautifulSoup(content, 'html.parser')
        text_content = soup.get_text()
        page_word_counts = count_words(text_content, STOPWORDS)

        # Update the global word counts
        WORD_COUNTS.update(page_word_counts)

        # Check if the current page has more words than the previous maximum
        if sum(page_word_counts.values()) > MAX_COUNT:
            MAX_COUNT = sum(page_word_counts.values())
            LONGEST_PAGE = url

        # Extract next links
        links = extract_next_links(url, resp)
        valid_links = [link for link in links if is_valid(link)]

        # Update subdomain information
        for abs_url in valid_links:
            parsed_url = urlparse(abs_url)
            if parsed_url.hostname.endswith(".ics.uci.edu"):
                subdomain = parsed_url.hostname
                SUBDOMAINS[subdomain].add(abs_url)

        return valid_links

    return []

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    # Ensure it's a 200 status
    if resp.status != 200:
        return []

    absolute_urls = []

    if resp.raw_response and resp.raw_response.content:
        content = resp.raw_response.content
        soup = BeautifulSoup(content, 'html.parser')

        # Calculate the SimHash fingerprint for the current page's content
        fingerprint = simhash(soup.get_text())

        # Check if the fingerprint is similar to any previously seen fingerprint
        is_similar = any(similarity(fingerprint, fp) >= SIMILARITY_THRESHOLD for fp in SEEN_FINGERPRINTS)

        # If the fingerprint is not similar to any seen fingerprint, process the page
        if not is_similar:
            # Add the fingerprint to the set of seen fingerprints
            SEEN_FINGERPRINTS.add(fingerprint)

            # Extract all URLs
            urls = [a['href'] for a in soup.find_all('a', href=True)]

            for href in urls:
                abs_url = urljoin(url, href)
                abs_url = defragment_url(abs_url)  # Defragment the URL
                if is_valid(abs_url):
                    absolute_urls.append(abs_url)
    
    # Printing
    print(len(UNIQUE_URL))
    print()
    print(WORD_COUNTS.most_common(50))
    print()
    print(f"The longest page is '{LONGEST_PAGE}' with {MAX_COUNT} words.")
    print()
    for subdomain, pages in sorted(SUBDOMAINS.items()):
        print(f"{subdomain}, {len(pages)}")
    return absolute_urls

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    # Make sure the length of a url isn't too long
    if len(url) >= 2000:
            return False

    try:
        parsed = urlparse(url)

        if parsed.scheme not in set(["http", "https"]):
            return False

        # Ensure they are apart of the allowed domains
        if not(parsed.hostname.lower().endswith("ics.uci.edu") or parsed.hostname.lower().endswith("cs.uci.edu") or parsed.hostname.lower().endswith("informatics.uci.edu") or parsed.hostname.lower().endswith("stat.uci.edu")):
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print("TypeError for ", parsed)
        raise
    
def count_words(text, stop_words):
    words = re.findall(r"\b[\w']+\b", text.lower())
    # Count words, ignoring stop words
    word_counts = Counter(word for word in words if len(word) > 1 and word not in STOPWORDS)
    return word_counts

def defragment_url(url):
    # Parse the URL
    parsed_url = urlparse(url)
    # Set the fragment part to an empty string
    parsed_url = parsed_url._replace(fragment='')
    # Convert the parsed URL back to a string
    defragmented_url = urlunparse(parsed_url)
    return defragmented_url

# def is_relevant(content):
#     # Generate the BLAKE2 hash value for the content
#     hash_value = hashlib.blake2b(content, digest_size=32).hexdigest()
    
#     # Check if the hash value is already in the set of seen hashes
#     if hash_value in SEEN_HASHES:
#         # Similar to an existing page, not relevant
#         return False
    
#     # Not similar to any existing page, add to set and consider relevant
#     SEEN_HASHES.add(hash_value)
#     return True

def tokenize(content):
    # Use a regular expression to extract alphanumeric tokens (words and numbers)
    pattern = re.compile(r'[a-zA-Z0-9]+')
    tokens = pattern.findall(content.lower())
    return tokens

def simhash(text):
    # Step 1: Tokenize the text and calculate word frequencies (weights)
    tokens = tokenize(text)
    token_weights = Counter(tokens)

    # Step 2: Generate b-bit hash values for each token
    hash_values = {token: int(sha256(token.encode()).hexdigest(), 16) % (2 ** 64) for token in token_weights}

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