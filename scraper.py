import re
import hashlib
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HIGH_INFO_THRESHOLD = .10

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

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
    absolute_urls = []

    if resp.raw_response and resp.raw_response.content:
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

        # Extract all URLs
        urls = [a['href'] for a in soup.find_all('a', href=True)]

        seen_hashes = set()

        for href in urls:
            abs_url = urljoin(url, href)
            if is_valid(abs_url):
                content = resp.raw_response.content
                content_hash = hashlib.md5(content).hexdigest()

                if content_hash not in seen_hashes and is_high_info(content):
                    absolute_urls.append(abs_url)
                    seen_hashes.add(content_hash)

    return absolute_urls

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
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
    
# Ensure that the content from the webpage provides a reasonable amount of information
# Should prevent crawling large files that provide little textual info
def is_high_info(content):
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text()
    text_length = len(text_content)
    html_length = len(content)

    # If no information return False
    if html_length == 0:
        return False

    ratio = text_length / html_length
    return ratio > HIGH_INFO_THRESHOLD  # Adjust the threshold as needed
