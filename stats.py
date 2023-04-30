from collections import Counter, defaultdict
import urllib.parse

class Stats:
    def __init__(self) -> None:
        self.uniquePages = set()
        self.allPages = set()
        self.fingerprints = set()
        self.wordsHash = Counter()
        self.longestFile = ""
        self.num = 0
        self.subdomains = defaultdict(set)
        self.STOPWORDS = {
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
        self.responses = set()

    def get_unique(self) -> set:
        return self.uniquePages

    def set_unique(self, url: str) -> None:
        self.uniquePages.add(url)

    def get_allPages(self) -> set:
        return self.allPages

    def set_allPages(self, url: str) -> None:
        self.allPages.add(url)

    def get_top(self):
        return self.wordsHash.most_common(50)

    def get_longest(self) -> str:
        return self.longestFile

    def set_longest(self, file: str) -> None:
        self.longestFile = file

    def add_words(self, word: str) -> None:
        self.wordsHash[word] += 1

    def set_unique(self, url: str) -> None:
        self.uniquePages.add(url)

    def get_num(self) -> int:
        return self.num

    def set_num(self, num: int) -> None:
        self.num = num

    def get_stopWords(self) -> set:
        return self.STOPWORDS
    
    def get_responses(self) -> set:
        return self.responses

    def set_responses(self, resp) -> None:
        self.responses.add(resp)

    def is_valid(self, word: str) -> bool:
        return not (word in self.STOPWORDS)
    
    def get_icsDomain(self) -> int:
        temp = 0
        for page in self.allPages:
            domain_name = urllib.parse.urlparse(page).hostname
            if domain_name.endswith(".ics.uci.edu"):
                temp += 1
        return temp

    def print_top(self) -> None:
        # print(self.wordsHash.most_common(50))
        # Filter out stopwords from the Counter object
        filtered_wordsHash = Counter({word: count for word, count in self.wordsHash.items() if word not in self.STOPWORDS})

        # Get the top 50 words (excluding stopwords)
        top_50_words = filtered_wordsHash.most_common(50)

        # Print the top 50 words
        print(top_50_words)
    
    def get_subdomains(self):
        return self.subdomains
    
    def add_subdomains(self, links):
        for abs_url in links:
            parsed_url = urllib.parse.urlparse(abs_url)
            if parsed_url.hostname.endswith(".ics.uci.edu"):
                subdomain = parsed_url.hostname
                self.subdomains[subdomain].add(abs_url)
    
    def add_fingerprints(self, url):
        self.fingerprints.add(url)
    
    def get_fingerprints(self):
        return self.fingerprints
