import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode, urldefrag
from stats import Stats
import hashlib

stat = Stats()


def scraper(url, resp):
    global stat

    stat.set_allPages(url)
    stat.set_unique(urldefrag(url)[0])
    stat.set_responses(resp)
    # Means there was an error so stop execution of this file
    if resp.status != 200:
        return []

    # Content of the page if there is content, else return empty list and stop execution
    content = resp.raw_response.content if resp.raw_response else None
    if not content:
        return []

    # Create soup and update word counter
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text()
    if similarityCheck(text_content, url):
        return []
    # If count words is greater than current max then update the longest file URL
    if count_words(text_content):
        stat.set_longest(url)

    links = extract_next_links(url, resp)
    print(f"URL: {url}")
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
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    urls = []
    for a in soup.find_all('a', href=True):
        u = (normalize_url(defragment_url(urljoin(url, a['href']))))
        if is_valid(u) and stat.is_valid(u):
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

        # Ensure they are apart of the allowed domains
        if not (parsed.hostname.lower().endswith("ics.uci.edu") or parsed.hostname.lower().endswith("cs.uci.edu") or parsed.hostname.lower().endswith("informatics.uci.edu") or parsed.hostname.lower().endswith("stat.uci.edu")):
            return False

        if len(url) > 2083:
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
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


def defragment_url(url):
    # Parse the URL
    parsed_url = urlparse(url)
    # Set the fragment part to an empty string
    parsed_url = parsed_url._replace(fragment='')
    # Convert the parsed URL back to a string
    defragmented_url = urlunparse(parsed_url)
    return defragmented_url


def normalize_url(url):
    # Parse the URL
    parsed_url = urlparse(url)
    # Sort the query parameters alphabetically
    sorted_query_params = sorted(parse_qsl(parsed_url.query))
    # Reconstruct the URL with the sorted query parameters
    normalized_url = parsed_url._replace(query=urlencode(sorted_query_params))
    # Convert the parsed URL back to a string
    return urlunparse(normalized_url)


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


def similarityCheck(url_content: str, url) -> bool:
    global stat
    h = hashlib.sha1()
    h1 = hashlib.sha1()
    for resp in stat.get_responses():
        # Check to see if same page
        if resp.url != url:
            content = resp.raw_response.content if resp.raw_response else None
            if not content:
                return False
            # Create soup and update word counter
            soup = BeautifulSoup(content, 'html.parser')
            p_content = soup.get_text()
            h.update(p_content.encode('utf-8'))
            hash_page = h.hexdigest()
            h1.update(url_content.encode('utf-8'))
            hash_current = h1.hexdigest()
            # threshold to compare and calculate similarity between the two
            threshold = int(len(hash_page) * 0.85)
            # Check if hash values are within threshold
            if abs(int(hash_current, 16) - int(hash_page, 16)) <= threshold:
                # Less than threshold means similar
                return True
    # None are similar
    return False
