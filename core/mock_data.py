# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class MockDataLoader:
    def __init__(self, data_path: str = "data/mock_influencers.json"):
        self.data_path = Path(__file__).resolve().parents[1] / data_path

    def get_all_influencers(self) -> List[Dict[str, Any]]:
        if not self.data_path.exists():
            return []

        with self.data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Mock influencer data must be a list.")
        return data

    def get_filtered_influencers(
        self,
        category: Optional[str] = None,
        region: Optional[str] = None,
        min_followers: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        influencers = self.get_all_influencers()
        if region:
            influencers = [item for item in influencers if item.get("region") == region]
        if min_followers is not None:
            influencers = [item for item in influencers if item.get("follower_count", 0) >= min_followers]
        if category:
            terms = {part.lower() for part in category.split() if part.strip()}
            influencers = [
                item
                for item in influencers
                if terms.intersection(self._searchable_text(item).lower().split())
            ]
        return influencers

    @staticmethod
    def _searchable_text(influencer: Dict[str, Any]) -> str:
        pieces: List[str] = [
            str(influencer.get("username", "")),
            str(influencer.get("bio", "")),
            " ".join(influencer.get("style_tags", [])),
        ]
        for video in influencer.get("recent_videos", []):
            pieces.append(str(video.get("video_title", "")))
            pieces.append(str(video.get("script_text", "")))
            pieces.extend(str(comment) for comment in video.get("comments", []))
        return " ".join(pieces)
