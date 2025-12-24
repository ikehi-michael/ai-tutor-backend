"""
YouTube Data API v3 service for finding educational videos
"""
import requests
from typing import Optional, Dict
from app.core.config import settings


class YouTubeService:
    """Service for searching YouTube videos using Data API v3"""
    
    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
        self.base_url = "https://www.googleapis.com/youtube/v3/search"
        
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY not found in environment variables")
    
    def search_educational_video(
        self, 
        subject: str, 
        topic: str, 
        max_results: int = 1
    ) -> Optional[Dict]:
        """
        Search for educational YouTube videos related to a subject and topic
        
        Args:
            subject: Subject name (e.g., "Mathematics")
            topic: Topic name (e.g., "Quadratic Equations")
            max_results: Maximum number of results (default: 1)
        
        Returns:
            Dictionary with video information or None if not found/error
            {
                "video_id": str,
                "video_url": str,
                "youtube_video_id": str,  # Same as video_id for consistency
                "youtube_video_url": str,  # Same as video_url for consistency
                "title": str,
                "channel": str
            }
        """
        # Build search query optimized for Nigerian WAEC/JAMB content
        query = f"{topic} {subject}"
        
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": self.api_key,
            "videoCategoryId": "27",  # Education category
            "order": "relevance",
            "safeSearch": "strict"  # Ensure safe content
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("items"):
                # Try without WAEC/JAMB keywords if no results
                return self._fallback_search(subject, topic, max_results)
            
            # Extract video information
            video = data["items"][0]
            video_id = video["id"]["videoId"]
            video_title = video["snippet"]["title"]
            channel_title = video["snippet"]["channelTitle"]
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            return {
                "video_id": video_id,
                "video_url": video_url,
                "youtube_video_id": video_id,  # For consistency with existing code
                "youtube_video_url": video_url,  # For consistency with existing code
                "title": video_title,
                "channel": channel_title
            }
            
        except requests.exceptions.RequestException as e:
            print(f"YouTube API error: {e}")
            return None
        except Exception as e:
            print(f"YouTube service error: {e}")
            return None
    
    def _fallback_search(
        self, 
        subject: str, 
        topic: str, 
        max_results: int = 1
    ) -> Optional[Dict]:
        """
        Fallback search without WAEC/JAMB keywords if initial search fails
        """
        query = f"{topic} {subject} tutorial"
        
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": self.api_key,
            "videoCategoryId": "27",  # Education category
            "order": "relevance",
            "safeSearch": "strict"
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("items"):
                return None
            
            video = data["items"][0]
            video_id = video["id"]["videoId"]
            video_title = video["snippet"]["title"]
            channel_title = video["snippet"]["channelTitle"]
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            return {
                "video_id": video_id,
                "video_url": video_url,
                "youtube_video_id": video_id,
                "youtube_video_url": video_url,
                "title": video_title,
                "channel": channel_title
            }
            
        except Exception as e:
            print(f"YouTube fallback search error: {e}")
            return None


# Create a singleton instance
youtube_service = YouTubeService()

