"""Tests for root endpoints."""


class TestRootIndexEndpoint:
    """Test root API index endpoint."""

    def test_root_endpoint_accessible(self, client):
        """Test root endpoint is accessible without authentication."""
        response = client.get('/')
        assert response.status_code == 200

    def test_root_endpoint_json_response(self, client):
        """Test root endpoint returns JSON."""
        response = client.get('/')
        assert response.content_type == 'application/json'
        data = response.get_json()
        assert isinstance(data, dict)

    def test_root_endpoint_has_api_info(self, client):
        """Test root endpoint returns API information."""
        response = client.get('/')
        data = response.get_json()
        assert 'name' in data
        assert 'version' in data
        assert 'description' in data
        assert data['name'] == 'Flight Management System API'

    def test_root_endpoint_has_endpoints_list(self, client):
        """Test root endpoint lists available endpoints."""
        response = client.get('/')
        data = response.get_json()
        assert 'endpoints' in data
        endpoints = data['endpoints']
        assert 'tokens' in endpoints
        assert 'users' in endpoints
        assert 'flights' in endpoints
        assert 'bookings' in endpoints
        assert 'swagger' in endpoints

    def test_root_endpoint_has_documentation_link(self, client):
        """Test root endpoint provides documentation link."""
        response = client.get('/')
        data = response.get_json()
        assert 'documentation' in data
        assert 'apidocs' in data['documentation']


class TestHealthCheckEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_accessible(self, client):
        """Test health endpoint is accessible without authentication."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_endpoint_json_response(self, client):
        """Test health endpoint returns JSON."""
        response = client.get('/health')
        assert response.content_type == 'application/json'
        data = response.get_json()
        assert isinstance(data, dict)

    def test_health_endpoint_returns_healthy_status(self, client):
        """Test health endpoint indicates system is healthy."""
        response = client.get('/health')
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'healthy'

    def test_health_endpoint_returns_service_name(self, client):
        """Test health endpoint returns service name."""
        response = client.get('/health')
        data = response.get_json()
        assert 'service' in data
        assert 'Flight Management System API' in data['service']




