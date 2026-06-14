import unittest
from unittest.mock import MagicMock, patch

from core.campaign_matcher import CampaignMatcher
from core.progress import STAGE_COMPLETED, STAGE_FETCHING, STAGE_INDEXING, STAGE_SCORING, progress_payload
from core.providers import MockInfluencerProvider
from tasks.campaign_pipeline import run_campaign_matching
from tests.fixtures import sample_campaign


class AsyncPipelineTest(unittest.TestCase):
    def test_progress_payload_structure(self):
        payload = progress_payload(60, STAGE_SCORING, "正在计算匹配评分...")
        self.assertEqual(payload["progress"], 60)
        self.assertEqual(payload["stage"], STAGE_SCORING)
        self.assertIn("正在计算", payload["message"])

    def test_campaign_matcher_emits_pipeline_stages(self):
        matcher = CampaignMatcher(provider=MockInfluencerProvider(size=40))
        stages: list[str] = []

        def callback(progress, stage, message):
            stages.append(stage)

        campaign = sample_campaign(
            detailed_marketing_requirements="温柔护肤、小众洗面奶、18-30岁女性受众",
        )
        matcher.match(campaign, progress_callback=callback)
        self.assertIn(STAGE_FETCHING, stages)
        self.assertIn(STAGE_INDEXING, stages)
        self.assertIn(STAGE_SCORING, stages)
        self.assertIn(STAGE_COMPLETED, stages)

    @patch("tasks.campaign_pipeline.get_search_meta")
    def test_celery_task_returns_success_payload(self, mock_meta):
        mock_meta.return_value = {"data_source": "mock", "fallback_message": None}
        task = MagicMock()
        task.request.id = "task-test-001"
        states = []

        def _update_state(*, state=None, meta=None):
            states.append((state, meta))

        task.update_state = _update_state
        task.matcher = CampaignMatcher(provider=MockInfluencerProvider(size=40))
        campaign = sample_campaign(detailed_marketing_requirements="美妆测评博主")
        result = run_campaign_matching.run.__func__(task, campaign.model_dump(mode="json"))

        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("data", result)
        stage_names = [meta.get("stage") for _, meta in states if meta]
        self.assertIn(STAGE_FETCHING, stage_names)

    @patch("tasks.campaign_pipeline.celery_app.send_task")
    def test_async_endpoint_submission(self, mock_send_task):
        from httpx import ASGITransport, AsyncClient
        import asyncio
        from main import app

        fake_task = MagicMock()
        fake_task.id = "async-task-id"
        mock_send_task.return_value = fake_task

        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.post(
                    "/api/v1/campaign/match/async",
                    json=sample_campaign().model_dump(mode="json"),
                )

        response = asyncio.run(_run())
        self.assertEqual(response.status_code, 202)
