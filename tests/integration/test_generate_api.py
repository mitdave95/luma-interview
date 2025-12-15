"""Integration tests for video generation endpoints."""

import pytest


class TestGenerateAPI:
    """Tests for /v1/generate endpoints."""

    def test_generate_video_developer(self, client, dev_user_headers, sample_generation_request):
        """Test video generation with developer tier."""
        response = client.post(
            "/v1/generate",
            json=sample_generation_request,
            headers=dev_user_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["queue_position"] is not None

    def test_generate_video_free_tier_rejected(
        self, client, free_user_headers, sample_generation_request
    ):
        """Test that free tier cannot generate videos."""
        response = client.post(
            "/v1/generate",
            json=sample_generation_request,
            headers=free_user_headers,
        )
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_TIER"

    def test_generate_video_invalid_prompt(self, client, dev_user_headers):
        """Test generation with invalid prompt."""
        response = client.post(
            "/v1/generate",
            json={"prompt": "", "duration": 10},
            headers=dev_user_headers,
        )
        assert response.status_code == 400

    def test_generate_video_duration_exceeds_tier_limit(self, client, dev_user_headers):
        """Test that duration exceeding tier limit is rejected."""
        response = client.post(
            "/v1/generate",
            json={"prompt": "A test video", "duration": 60},  # Dev max is 30s
            headers=dev_user_headers,
        )
        assert response.status_code == 403

    def test_generate_video_pro_tier(self, client, pro_user_headers):
        """Test video generation with pro tier (longer duration allowed)."""
        response = client.post(
            "/v1/generate",
            json={"prompt": "A test video", "duration": 60},
            headers=pro_user_headers,
        )
        assert response.status_code == 202

    def test_batch_generate_pro_tier(self, client, pro_user_headers, sample_batch_request):
        """Test batch generation with pro tier."""
        response = client.post(
            "/v1/generate/batch",
            json=sample_batch_request,
            headers=pro_user_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert "job_ids" in data
        assert len(data["job_ids"]) == 2
        assert data["total_queued"] == 2

    def test_batch_generate_developer_rejected(
        self, client, dev_user_headers, sample_batch_request
    ):
        """Test that developer tier cannot batch generate."""
        response = client.post(
            "/v1/generate/batch",
            json=sample_batch_request,
            headers=dev_user_headers,
        )
        assert response.status_code == 403

    def test_list_models(self, client, dev_user_headers):
        """Test listing available models."""
        response = client.get("/v1/generate/models", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0
        assert any(m["id"] == "dream-machine-1.5" for m in data["models"])

    def test_generate_with_all_options(self, client, dev_user_headers):
        """Test generation with all options specified."""
        response = client.post(
            "/v1/generate",
            json={
                "prompt": "A beautiful landscape",
                "duration": 10,
                "resolution": "720p",
                "style": "cinematic",
                "aspect_ratio": "9:16",
                "model": "dream-machine-1.5",
                "metadata": {"project": "test"},
            },
            headers=dev_user_headers,
        )
        assert response.status_code == 202


class TestJobsAPI:
    """Tests for /v1/jobs endpoints."""

    @pytest.fixture
    def created_job(self, client, dev_user_headers, sample_generation_request):
        """Create a job for testing."""
        response = client.post(
            "/v1/generate",
            json=sample_generation_request,
            headers=dev_user_headers,
        )
        return response.json()

    def test_get_job_status(self, client, dev_user_headers, created_job):
        """Test getting job status."""
        job_id = created_job["job_id"]
        response = client.get(f"/v1/jobs/{job_id}", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data

    def test_get_job_not_found(self, client, dev_user_headers):
        """Test getting non-existent job."""
        response = client.get("/v1/jobs/job_nonexistent", headers=dev_user_headers)
        assert response.status_code == 404

    def test_list_jobs(self, client, dev_user_headers, created_job):
        """Test listing jobs."""
        response = client.get("/v1/jobs", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_cancel_job(self, client, dev_user_headers, created_job):
        """Test cancelling a job."""
        job_id = created_job["job_id"]
        response = client.delete(f"/v1/jobs/{job_id}", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_job_wrong_owner(
        self, client, free_user_headers, dev_user_headers, sample_generation_request
    ):
        """Test that users cannot cancel others' jobs."""
        # Create job as dev user
        response = client.post(
            "/v1/generate",
            json=sample_generation_request,
            headers=dev_user_headers,
        )
        job_id = response.json()["job_id"]

        # Try to cancel as free user
        response = client.delete(f"/v1/jobs/{job_id}", headers=free_user_headers)
        assert response.status_code == 403
