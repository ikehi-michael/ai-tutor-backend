"""
Test script for YouTube Data API v3
Tests searching for educational videos related to a topic
"""
import os
import sys
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not YOUTUBE_API_KEY:
    print("❌ ERROR: YOUTUBE_API_KEY not found in .env file")
    sys.exit(1)

print(f"✅ Found YouTube API Key: {YOUTUBE_API_KEY[:10]}...")


def search_youtube_video(query: str, max_results: int = 1):
    """
    Search for YouTube videos using the Data API v3
    
    Args:
        query: Search query (e.g., "Quadratic Equations Mathematics WAEC")
        max_results: Maximum number of results to return (default: 1)
    
    Returns:
        Dictionary with video information or None if error
    """
    base_url = "https://www.googleapis.com/youtube/v3/search"
    
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
        "videoCategoryId": "27",  # Education category
        "order": "relevance"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("items"):
            print(f"⚠️  No videos found for query: {query}")
            return None
        
        # Extract video information
        video = data["items"][0]
        video_id = video["id"]["videoId"]
        video_title = video["snippet"]["title"]
        channel_title = video["snippet"]["channelTitle"]
        description = video["snippet"]["description"]
        published_at = video["snippet"]["publishedAt"]
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        
        return {
            "video_id": video_id,
            "video_url": video_url,
            "embed_url": embed_url,
            "title": video_title,
            "channel": channel_title,
            "description": description[:200] + "..." if len(description) > 200 else description,
            "published_at": published_at
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making API request: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def test_youtube_search():
    """Test YouTube API with sample queries"""
    print("\n" + "="*60)
    print("🧪 Testing YouTube Data API v3")
    print("="*60 + "\n")
    
    # Test cases
    test_queries = [
        {
            "subject": "Mathematics",
            "topic": "Quadratic Equations",
            "query": "Quadratic Equations Mathematics"
        },
        {
            "subject": "Physics",
            "topic": "Motion",
            "query": "Motion Physics"
        },
        {
            "subject": "Chemistry",
            "topic": "Chemical Bonding",
            "query": "Chemical Bonding Chemistry"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {test['subject']} - {test['topic']}")
        print(f"   Query: {test['query']}")
        print("-" * 60)
        
        result = search_youtube_video(test['query'])
        
        if result:
            print(f"✅ Success!")
            print(f"   Video ID: {result['video_id']}")
            print(f"   Title: {result['title']}")
            print(f"   Channel: {result['channel']}")
            print(f"   URL: {result['video_url']}")
            print(f"   Embed URL: {result['embed_url']}")
            print(f"   Published: {result['published_at']}")
        else:
            print(f"❌ Failed to find video")
    
    print("\n" + "="*60)
    print("✅ Test completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_youtube_search()

