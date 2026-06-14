import unittest

from core.progress import (
    STAGE_COMPLETED,
    STAGE_FETCHING,
    STAGE_INDEXING,
    STAGE_OUTREACH,
    STAGE_SCORING,
    progress_payload,
)


class WebSocketProgressTest(unittest.TestCase):
    def test_progress_payload_for_websocket(self):
        payload = progress_payload(30, STAGE_INDEXING, "正在构建语义向量索引...")
        self.assertEqual(payload["progress"], 30)
        self.assertEqual(payload["stage"], STAGE_INDEXING)

    def test_progress_stages_sequence(self):
        stages = [
            progress_payload(10, STAGE_FETCHING, "正在检索海外红人..."),
            progress_payload(30, STAGE_INDEXING, "正在构建语义向量索引..."),
            progress_payload(60, STAGE_SCORING, "正在计算匹配评分..."),
            progress_payload(90, STAGE_OUTREACH, "正在生成邀约信..."),
            progress_payload(100, STAGE_COMPLETED, "任务完成"),
        ]
        self.assertEqual(stages[0]["progress"], 10)
        self.assertEqual(stages[0]["stage"], "fetching influencers")
        self.assertEqual(stages[-1]["progress"], 100)
        self.assertEqual(stages[-1]["stage"], "completed")
