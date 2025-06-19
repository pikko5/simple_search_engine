import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import math
from collections import defaultdict, Counter

class FeedScraper:
    """
    Read a text file of RSS/Atom feed URLs and extract channel & item metadata.
    Output: pandas.DataFrame with columns ['Feed URL','Channel Title','Channel Description',
                                         'Item Title','Item Description']
    """
    def __init__(self, feeds_file):
        self.feeds_file = feeds_file
        self.urls = self._load_urls()

    def _load_urls(self):
        with open(self.feeds_file, 'r', encoding='utf-8') as f:
            return [u.strip() for u in f if u.strip()]

    def _fetch_items(self, url):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return []
        soup = BeautifulSoup(resp.text, 'xml')
        channel = soup.find('channel')
        if channel:
            ch_title = channel.title.get_text(strip=True) if channel.title else ''
            ch_desc = channel.description.get_text(strip=True) if channel.description else ''
            entries = channel.find_all('item')
        else:
            ch_title = soup.find('title').get_text(strip=True) if soup.find('title') else ''
            ch_desc = ''
            entries = soup.find_all('entry')
        rows = []
        for e in entries:
            it_title = e.find('title').get_text(strip=True) if e.find('title') else ''
            desc_tag = e.find('description') or e.find('summary') or e.find('content:encoded') or e.find('content')
            it_desc = desc_tag.get_text(strip=True) if desc_tag else ''
            rows.append({
                'Feed URL': url,
                'Channel Title': ch_title,
                'Channel Description': ch_desc,
                'Item Title': it_title,
                'Item Description': it_desc
            })
        if not rows:
            rows = [{
                'Feed URL': url,
                'Channel Title': ch_title,
                'Channel Description': ch_desc,
                'Item Title': '',
                'Item Description': ''
            }]
        return rows

    def scrape_all(self):
        data = []
        for u in self.urls:
            print(f"Fetching feed: {u}")
            data.extend(self._fetch_items(u))
        return pd.DataFrame(data)

class InvertedIndex:
    """
    Build an inverted index and store document lengths for BM25.
    """
    def __init__(self):
        self.index = defaultdict(dict)
        self.doc_lens = {}
        self.N = 0
        self.avg_dl = 0.0

    def tokenize(self, text):
        return re.findall(r"\w+", text.lower())

    def build(self, docs):
        """
        docs: list of strings (the text to index)
        """
        self.N = len(docs)
        for i, text in enumerate(docs):
            toks = self.tokenize(text)
            self.doc_lens[i] = len(toks)
            freqs = Counter(toks)
            for term, cnt in freqs.items():
                self.index[term][i] = cnt
        self.avg_dl = sum(self.doc_lens.values()) / self.N if self.N else 0

class BM25Ranker:
    def __init__(self, index: InvertedIndex, k1=1.5, b=0.75):
        self.idx = index
        self.k1 = k1
        self.b = b

    def idf(self, term):
        df = len(self.idx.index.get(term, {}))
        return math.log((self.idx.N - df + 0.5) / (df + 0.5) + 1)

    def score(self, query, top_k=10):
        q_toks = Counter(self.idx.tokenize(query))
        scores = defaultdict(float)
        for term in q_toks:
            postings = self.idx.index.get(term, {})
            if not postings:
                continue
            idf = self.idf(term)
            for doc_id, f in postings.items():
                dl = self.idx.doc_lens[doc_id]
                denom = f + self.k1 * (1 - self.b + self.b * dl / self.idx.avg_dl)
                scores[doc_id] += idf * (f * (self.k1 + 1)) / denom
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return ranked

class SearchEngine:
    """
    Given a DataFrame of documents, build an index and perform search,
    returning absolute BM25 scores and percentage relevance.
    """
    def __init__(self, df: pd.DataFrame, text_col='Item Description'):
        self.df = df.reset_index(drop=True)
        texts = df[text_col].fillna('').tolist()
        self.index = InvertedIndex()
        self.index.build(texts)
        self.ranker = BM25Ranker(self.index)

    def search(self, query, top_k=10):
        hits = self.ranker.score(query, top_k)
        results = []
        for doc_id, score in hits:
            row = self.df.iloc[doc_id].to_dict()
            row['score'] = score
            results.append(row)
        res_df = pd.DataFrame(results)
        # Compute relative percentage relevance based on max score
        if not res_df.empty and 'score' in res_df:
            max_score = res_df['score'].max()
            res_df['pct_relevance'] = res_df['score'] / max_score * 100
        return res_df