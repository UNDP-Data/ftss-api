import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..entities.signal import Signal

import worldnewsapi
from worldnewsapi.rest import ApiException
from worldnewsapi.models.search_news200_response import SearchNews200Response

# ------------------------------------------------------------------------------------------------- 
# Models for WorldNewsAPI responses
# ------------------------------------------------------------------------------------------------- 

class NewsSource(BaseModel):
    id: str | None = None
    name: str | None = None
    url: str | None = None
    language: str | None = None
    country: str | None = None

class NewsArticle(BaseModel):
    """Model for each news item in the WorldNewsAPI response"""
    id: int | None = None
    title: str
    text: str | None = None
    summary: str | None = None
    url: str
    image: str | None = None
    publish_date: str | None = None
    author: str | None = None
    language: str | None = None
    source_country: str | None = None
    sentiment: float | None = None

class WorldNewsResponse(BaseModel):
    """Response model matching WorldNewsAPI documentation"""
    news: List[NewsArticle]  # Changed from 'articles' to 'news'
    offset: int | None = None
    number: int | None = None
    available: int | None = None

# ------------------------------------------------------------------------------------------------- 
# API Client Configuration
# ------------------------------------------------------------------------------------------------- 

def client():
    """Initialize WorldNewsAPI client with API key."""
    newsapi_configuration = worldnewsapi.Configuration(api_key={'apiKey': os.getenv("WORLD_NEWS_API_KEY")})
    return worldnewsapi.NewsApi(worldnewsapi.ApiClient(newsapi_configuration))

    # return WorldNewsApi(api_key=os.getenv("WORLD_NEWS_API_KEY"))

# ------------------------------------------------------------------------------------------------- 
# API Methods
# ------------------------------------------------------------------------------------------------- 

def search_news(
    text: str,
    source_countries: str | None = None,
    language: str = "en",
    number: int = 5,
    offset: int = 0,
    **kwargs
) -> WorldNewsResponse:
    """
    Search worldwide news articles.
    """
    try:
        newsapi = client()
        response = newsapi.search_news(
            text=text,
            language=language,
            number=number,
            offset=offset,
            **kwargs
        )

        # Convert SearchNews200Response news items to dictionaries
        news_items = []
        for news_item in response.news:
            news_dict = {
                "id": news_item.id,
                "title": news_item.title,
                "text": news_item.text,
                "summary": news_item.summary,
                "url": news_item.url,
                "image": news_item.image,
                "publish_date": news_item.publish_date,
                "author": news_item.author,
                "language": news_item.language,
                "source_country": news_item.source_country,
                "sentiment": news_item.sentiment
            }
            news_items.append(news_dict)

        # Create response dictionary
        response_dict = {
            "news": news_items,
            "offset": response.offset,
            "number": response.number,
            "available": response.available
        }

        return WorldNewsResponse(**response_dict)
    except ApiException as e:
        print(f"API Exception: {e}")
        raise e

def get_latest_news(
    source_countries: str | None = None,
    language: str = "en",
    number: int = 5,
    offset: int = 0,
) -> WorldNewsResponse:
    """
    Get the latest news articles.
    
    Args:
        source_countries: Comma-separated list of ISO 3166 country codes
        language: Language code (default: en)
        number: Number of articles to return (default: 5)
        offset: Number of articles to skip (default: 0)
    """
    try:
        newsapi = client()
        response = newsapi.get_latest_news(
            source_countries=source_countries,
            language=language,
            number=number,
            offset=offset
        )

        # Convert SearchNews200Response to dict
        response_dict = {
            "news": response.news,
            "offset": response.offset,
            "number": response.number,
            "available": response.available
        }

        return WorldNewsResponse(**response_dict)
    except ApiException as e:
        print(f"API Exception: {e}")
        raise e

def extract_news(
    url: str,
    analyze: bool = True
) -> NewsArticle:
    """
    Extract news from a specific URL.
    
    Args:
        url: URL of the news article to extract
        analyze: Whether to analyze the article for sentiment (default: True)
    """
    newsapi = client()
    response = newsapi.extract_news(
        url=url,
        analyze=analyze
    )
    
    return NewsArticle(**response)

def convert_to_signals(response: WorldNewsResponse) -> list[dict]:
    """
    Convert WorldNewsAPI articles to simplified signal dictionaries.
    """    
    signals = []
    try:
        for article in response.news:
            # Extract keywords from title
            keywords = []
            if article.source_country:
                keywords.append(article.source_country.upper())
                
            # Add keywords from title
            title_words = [word.strip('.,!?-:;"\'').lower() for word in article.title.split()]
            title_words = [w for w in title_words if len(w) > 3 and w not in {
                'the', 'and', 'for', 'after', 'from', 'with', 'has', 'have',
                'that', 'this', 'were', 'what'
            }]
            keywords.extend(title_words[:2])
            
            # Create relevance text
            if article.summary:
                description = article.summary
            elif article.text:
                description = article.text
            
            # Create signal dictionary with core fields
            signal = {
                "headline": article.title,
                "url": article.url,
                "description": description,
                "relevance": None,
                "keywords": list(dict.fromkeys(keywords))[:3],  # Remove duplicates and limit to 3
                "location": article.source_country.upper() if article.source_country else "Global",
                "created_unit": None,
                "score": {"sentiment": article.sentiment} if article.sentiment else None,
                "connected_trends": None
            }
            signals.append(signal)
    except Exception as e:
        print(f"Error converting to signals: {str(e)}")
        raise e
        
    return signals

def autocomplete(query: str) -> list[dict]:
    """
    Returns article suggestions converted to simplified signal dictionaries.
    """
    if not query or len(query) < 2:  # Require at least 2 characters
        return []
        
    try:
        response = search_news(
            text=query,
            number=5,
            language="en"
        )
        return convert_to_signals(response)
    except Exception as e:
        print(f"Error in autocomplete: {str(e)}")
        return []