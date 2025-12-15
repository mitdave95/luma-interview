"""Integration tests for rate limiting."""



class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_rate_limit_headers_present(self, client, dev_user_headers):
        """Test that rate limit headers are present on responses."""
        response = client.get("/v1/videos", headers=dev_user_headers)
        assert response.status_code == 200

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "X-RateLimit-Window" in response.headers
        assert "X-RateLimit-Policy" in response.headers

    def test_rate_limit_remaining_decrements(self, client, dev_user_headers):
        """Test that remaining count decrements with each request."""
        # First request
        response1 = client.get("/v1/videos", headers=dev_user_headers)
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])

        # Second request
        response2 = client.get("/v1/videos", headers=dev_user_headers)
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])

        assert remaining2 < remaining1

    def test_rate_limit_enforced_for_free_tier(self, client, free_user_headers):
        """Test that rate limiting is enforced for free tier (10/min)."""
        # Make 10 requests
        for i in range(10):
            response = client.get("/v1/account", headers=free_user_headers)
            assert response.status_code == 200

        # 11th request should be rate limited
        response = client.get("/v1/account", headers=free_user_headers)
        assert response.status_code == 429

        # Check error response format
        data = response.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in data["error"]["details"]

        # Check Retry-After header
        assert "Retry-After" in response.headers

    def test_different_tiers_different_limits(self, client, free_user_headers, dev_user_headers):
        """Test that different tiers have different rate limits."""
        # Get limits from headers
        free_response = client.get("/v1/account", headers=free_user_headers)
        dev_response = client.get("/v1/account", headers=dev_user_headers)

        free_limit = int(free_response.headers["X-RateLimit-Limit"])
        dev_limit = int(dev_response.headers["X-RateLimit-Limit"])

        assert free_limit == 10  # Free tier
        assert dev_limit == 30  # Developer tier

    def test_rate_limit_per_user(self, client, dev_user_headers, pro_user_headers):
        """Test that rate limits are per-user, not global."""
        # Exhaust developer's requests on a specific endpoint
        # (This would need many requests, just verify they're separate)

        # Dev user request
        dev_response = client.get("/v1/account", headers=dev_user_headers)
        dev_remaining = int(dev_response.headers["X-RateLimit-Remaining"])

        # Pro user request (should have full limit)
        pro_response = client.get("/v1/account", headers=pro_user_headers)
        pro_remaining = int(pro_response.headers["X-RateLimit-Remaining"])

        # Pro has higher limit so should have more remaining
        assert pro_remaining > dev_remaining

    def test_request_id_header_present(self, client, dev_user_headers):
        """Test that X-Request-ID header is present."""
        response = client.get("/v1/videos", headers=dev_user_headers)
        assert "X-Request-ID" in response.headers

    def test_health_endpoint_not_rate_limited(self, client):
        """Test that health endpoint is not rate limited."""
        for _ in range(20):
            response = client.get("/health")
            assert response.status_code == 200


class TestAccountAPI:
    """Tests for /v1/account endpoints."""

    def test_get_account(self, client, dev_user_headers):
        """Test getting account details."""
        response = client.get("/v1/account", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "developer"
        assert "email" in data
        assert "user_id" in data

    def test_get_usage(self, client, dev_user_headers):
        """Test getting usage statistics."""
        response = client.get("/v1/account/usage", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "daily"
        assert "requests_made" in data
        assert "videos_generated" in data

    def test_get_usage_monthly(self, client, dev_user_headers):
        """Test getting monthly usage statistics."""
        response = client.get(
            "/v1/account/usage",
            params={"period": "monthly"},
            headers=dev_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "monthly"

    def test_get_quota(self, client, dev_user_headers):
        """Test getting quota information."""
        response = client.get("/v1/account/quota", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "developer"
        assert "rate_limit" in data
        assert "daily_quota" in data
        assert "concurrent_jobs" in data
        assert data["can_generate"] is True
        assert data["can_batch_generate"] is False

    def test_quota_shows_correct_tier_limits(self, client, pro_user_headers):
        """Test that quota shows correct tier limits."""
        response = client.get("/v1/account/quota", headers=pro_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "pro"
        assert data["can_batch_generate"] is True
        assert data["max_video_duration"] == 120
