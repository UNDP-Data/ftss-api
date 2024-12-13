import os
import json
from newsapi import NewsApiClient
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..entities.signal import Signal

# ------------------------------------------------------------------------------------------------- 
# Sources that are preferred for autocomplete suggestions.
# LINK TO LIST: https://newsapi.org/v1/sources
# -------------------------------------------------------------------------------------------------  

PREFFERED_SOURCES = [
    "bbc-news",
    "reuters",
    "bloomberg",
    "the-washington-post",
    "economistgroup",
    "forbes",
    "cnbc",
    # "theguardian.com",
    # "ft.com",
    # "nytimes",
]

class Source(BaseModel):
    id: str | None = None
    name: str | None = None

class Article(BaseModel):
    source: Source
    title: str
    description: str | None = None
    url: str
    author: str | None = None
    urlToImage: str | None = None
    publishedAt: str | None = None
    content: str | None = None

class NewsAPIResponse(BaseModel):
    articles: List[Article]

def client() -> NewsApiClient:
    return NewsApiClient(api_key=os.getenv("NEWS_API_KEY"))

def get_top_headlines(query: str, sources: str, category: str, language: str, country: str) -> NewsAPIResponse:
    newsapi = client()
    response = newsapi.get_top_headlines(q=query,
                                     sources=sources,
                                     category=category,
                                     language=language,
                                     country=country)
    
    return NewsAPIResponse(**response)

def get_everything(query: str, **kwargs) -> NewsAPIResponse:
    """
    Search all articles using the /everything endpoint.
    Returns a simplified response with only title, source, and image.
    """
    newsapi = client()
    response = newsapi.get_everything(
        q=query,
        sort_by='relevancy',
        page_size=5,  # Limit results for autocomplete suggestions
        **kwargs
    )
    
    # Properly structure the response for NewsAPIResponse
    formatted_response = {
        "articles": response["articles"] if "articles" in response else []
    }
    
    # format json response print for debugging
    print(json.dumps(formatted_response["articles"], indent=4))
    
    return NewsAPIResponse(**formatted_response)

def extract_keywords(title: str, query: str) -> List[str]:
    """
    Extract relevant keywords from a title that match the query.
    """
    words = set()
    query = query.lower()
    for word in title.lower().split():
        # Remove common punctuation
        word = word.strip('.,!?-:;"\'')
        if word.startswith(query) and len(word) > 2:  # Avoid too short words
            words.add(word)
    return list(words)

def convert_to_signals(response: NewsAPIResponse) -> list[dict]:
    """
    Convert NewsAPI articles to simplified signal dictionaries with only core fields.
    """    
    signals = []
    for article in response.articles:
        # Extract meaningful keywords from title
        keywords = []
        if article.source and article.source.name:
            keywords.append(article.source.name)
            
        # Add keywords from title words (excluding common words)
        title_words = [word.strip('.,!?-:;"\'').lower() for word in article.title.split()]
        title_words = [w for w in title_words if len(w) > 3 and w not in {
            'the', 'and', 'for', 'after', 'from', 'with', 'has', 'have'
        }]
        keywords.extend(title_words[:2])  # Add up to 2 words from title
        
        # Create a more informative relevance text
        relevance = article.title
        if article.description:
            relevance = f"{article.title}\n\n{article.description}"
        
        # Determine location from content if possible
        location = "Global"  # Default to Global
        if article.description and "in " in article.description:
            location_parts = article.description.split("in ")
            if len(location_parts) > 1:
                potential_location = location_parts[1].split(".")[0].split(",")[0].strip()
                if len(potential_location) < 50:  # Sanity check on length
                    location = potential_location

        # Only include the core fields needed for signal creation
        signal = {
            "url": article.url,
            "relevance": relevance,
            "keywords": list(dict.fromkeys(keywords))[:3],  # Remove duplicates and limit to 3
            "location": location,
            "created_unit": None,  # Include required fields with None
            "score": None,
            "connected_trends": None
        }
        signals.append(signal)
    return signals

def autocomplete(query: str) -> list[Signal]:
    """
    Returns article suggestions converted to Signal objects.
    """
    if not query or len(query) < 2:  # Require at least 2 characters
        return []
        
    try:
        response = get_everything(query)
        return convert_to_signals(response)
    except Exception as e:
        print(f"Error in autocomplete: {str(e)}")
        return []