import unittest

import httpx

from database.session import init_db, session_scope
from main import app
from repositories.campaign_repository import CampaignRepository
from repositories.job_repository import JobRepository
from tests.fixtures import sample_campaign


class PersistenceApiTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    @classmethod
    def tearDownClass(cls):
        import asyncio

        asyncio.run(cls.client.aclose())

    async def test_campaign_history_and_job_endpoints(self):
        with session_scope() as db:
            campaign = CampaignRepository(db).create(sample_campaign(product_name="Persistence Test Product"))
            campaign_id = campaign.campaign_id
            JobRepository(db).create("persistence-test-task", campaign_id, status="PENDING")

        list_response = await self.client.get("/api/v1/campaigns")
        self.assertEqual(list_response.status_code, 200)
        self.assertTrue(
            any(item["campaign_id"] == campaign_id for item in list_response.json()["items"])
        )

        detail_response = await self.client.get(f"/api/v1/campaigns/{campaign_id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["campaign"]["campaign_id"], campaign_id)

        job_response = await self.client.get("/api/v1/jobs/persistence-test-task")
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_response.json()["campaign_id"], campaign_id)
