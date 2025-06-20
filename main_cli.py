from engine import FeedScraper, SearchEngine

import argparse

def main():
    parser = argparse.ArgumentParser(description='Feed scraper & search engine combined')
    parser.add_argument('--feeds', help='Text file of feed URLs')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--top_k', type=int, default=5)
    args = parser.parse_args()

    if args.feeds:
        scraper = FeedScraper(args.feeds)
        df = scraper.scrape_all()
    else:
        print("Provide --feeds to build documents.")
        return

    if args.query:
        engine = SearchEngine(df)
        res = engine.search(args.query, args.top_k)
        print(res)
    else:
        print(df)

if __name__ == '__main__':
    main()
