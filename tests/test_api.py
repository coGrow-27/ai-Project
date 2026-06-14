import unittest
from unittest.mock import MagicMock, patch

import httpx

from main import app
from tasks.celery_app import celery_app
from tests.fixtures import sample_campaign


class ApiTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    @classmethod
    def tearDownClass(cls):
        import asyncio

        asyncio.run(cls.client.aclose())

    async def test_health_endpoint(self):
        response = await self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "正常")
        self.assertIn("runtime", data)

    async def test_runtime_endpoint(self):
        response = await self.client.get("/api/v1/runtime")

        self.assertEqual(response.status_code, 200)
        self.assertIn("rag", response.json())

    async def test_frontend_home(self):
        response = await self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("智选红人", response.text)
        self.assertIn("产品名称", response.text)

    async def test_match_rejects_short_requirement(self):
        response = await self.client.post("/api/v1/match", json={"requirement": "cat"})

        self.assertEqual(response.status_code, 422)

    async def test_demo_match(self):
        response = await self.client.post(
            "/api/v1/demo/match",
            json={"requirement": "为一款猫咪去毛梳匹配合适的美国宠物红人"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertIn("results", body["result"])

    async def test_campaign_match_endpoint(self):
        response = await self.client.post(
            "/api/v1/campaign/match",
            json=sample_campaign().model_dump(mode="json"),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["total_candidates"], 0)
        self.assertEqual(data["content_top_k"], 5)
        self.assertTrue(data["results"][0]["detail_generated"])
        self.assertIsNotNone(data["results"][0]["outreach"])
        if len(data["results"]) > 5:
            self.assertFalse(data["results"][5]["detail_generated"])

    async def test_campaign_match_rejects_invalid_follower_range(self):
        payload = sample_campaign().model_dump(mode="json")
        payload["min_followers"] = 90000
        payload["max_followers"] = 10000
        response = await self.client.post("/api/v1/campaign/match", json=payload)

        self.assertEqual(response.status_code, 422)

    async def test_campaign_match_async_accepts_request(self):
        fake_task = MagicMock()
        fake_task.id = "test-task-id"
        with patch.object(celery_app, "send_task", return_value=fake_task):
            response = await self.client.post(
                "/api/v1/campaign/match/async",
                json=sample_campaign().model_dump(mode="json"),
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["task_id"], "test-task-id")
