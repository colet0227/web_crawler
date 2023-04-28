import re
import hashlib
import string
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import Counter, defaultdict

# HIGH_INFO_THRESHOLD = .10
SEEN_HASHES = set()
BASE_PATH_COUNTS = {}

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
    content_hash = hashlib.md5(content).hexdigest() if content else None

    if content_hash:
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
    if resp.status != 200:
        return []

    absolute_urls = []

    if resp.raw_response and resp.raw_response.content:
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

        # Extract all URLs
        urls = [a['href'] for a in soup.find_all('a', href=True)]

        for href in urls:
            abs_url = urljoin(url, href)
            # if is_valid(abs_url) and is_high_info(resp.raw_response.content) and abs_url not in SEEN_HASHES:
            if is_valid(abs_url) and abs_url not in SEEN_HASHES:
                parsed_url = urlparse(url)._replace(fragment='')  # remove the fragment part
                UNIQUE_URL.add(parsed_url.geturl())  # add the URL to a set
                
                absolute_urls.append(abs_url)
                SEEN_HASHES.add(abs_url)
    
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
    try:
        parsed = urlparse(url)

        # UPDATE COUNT FOR EVERY SINGLE BASE PATH SO WE DONT ACCESS IT MORE THAN ONCE
        base_path = parsed.path.rsplit("/", 1)[0]
        if base_path not in BASE_PATH_COUNTS:
            BASE_PATH_COUNTS[base_path] = 0
        else:
            BASE_PATH_COUNTS[base_path] += 1

            # Set a limit for the number of times the same base path can be visited
            if BASE_PATH_COUNTS[base_path] > 10:
                return False


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
    
# Ensure that the content from the webpage provides a reasonable amount of information
# Should prevent crawling large files that provide little textual info
# def is_high_info(content):
    # soup = BeautifulSoup(content, 'html.parser')
    # text_content = soup.get_text()
    # text_length = len(text_content)
    # html_length = len(content)

    # # If no information return False
    # if html_length == 0:
    #     return False

    # ratio = text_length / html_length
    # return True
    # return ratio > HIGH_INFO_THRESHOLD  # Adjust the threshold as needed

def count_words(text, stop_words):
    words = re.findall(r"\b[\w']+\b", text.lower())
    # Count words, ignoring stop words
    word_counts = Counter(word for word in words if len(word) > 1 and word not in STOPWORDS)
    return word_counts