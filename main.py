from fastapi import FastAPI, HTTPException
from typing import List
from engine import FeedScraper, SearchEngine
import pandas as pd

app = FastAPI(title="Feed Search API")

# Global objects
scraper: FeedScraper
engine: SearchEngine
feed_df: pd.DataFrame

@app.on_event("startup")
def startup_event():
    global scraper, engine, feed_df
    # Initialize scraper and index at app startup
    scraper = FeedScraper("feeds.txt")
    feed_df = scraper.scrape_all()
    engine = SearchEngine(feed_df, text_col="Item Description")

@app.get("/feeds", response_model=List[dict])
def get_feeds():
    """Return all scraped feed items."""
    if feed_df is None:
        raise HTTPException(status_code=500, detail="Feeds not loaded.")
    return feed_df.to_dict(orient="records")

@app.get("/search", response_model=List[dict])
def search(query: str, top_k: int = 5):
    """Search feed items via BM25 and return the top_k results."""
    if engine is None:
        raise HTTPException(status_code=500, detail="Search engine not initialized.")
    results_df = engine.search(query, top_k)
    return results_df.to_dict(orient="records")

@app.post("/reload")
def reload_feeds():
    """Re-fetch feeds and rebuild the search index."""
    global scraper, engine, feed_df
    scraper = FeedScraper("feeds.txt")
    feed_df = scraper.scrape_all()
    engine = SearchEngine(feed_df, text_col="Item Description")
    return {"status": "reloaded", "count": len(feed_df)}