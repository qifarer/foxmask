import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_get_current_user_me(self, test_client, auth_headers):
        """Test getting current user info."""
        # Mock Casdoor user info
        with patch('utils.casdoor_client.casdoor_client.get_user_info') as mock_user_info:
            mock_user_info.return_value = {
                'id': 'test-user-123',
                'name': 'testuser',
                'email': 'test@example.com',
                'displayName': 'Test User'
            }
            
            response = test_client.get("/api/auth/users/me", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["name"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, test_client):
        """Test unauthorized access to user endpoint."""
        response = test_client.get("/api/auth/users/me")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_current_user(self, test_client, auth_headers):
        """Test updating current user info."""
        # Mock Casdoor user info and update
        with patch('utils.casdoor_client.casdoor_client.get_user_info') as mock_user_info, \
             patch('auth.services.auth_service.get_or_create_user') as mock_get_user:
            
            mock_user_info.return_value = {
                'id': 'test-user-123',
                'name': 'testuser',
                'email': 'test@example.com',
                'displayName': 'Test User'
            }
            
            # Mock user model
            from auth.models import User
            mock_user = User(
                casdoor_id="test-user-123",
                name="testuser",
                email="test@example.com"
            )
            mock_get_user.return_value = mock_user
            
            update_data = {
                "display_name": "Updated User",
                "avatar": "https://example.com/new-avatar.jpg"
            }
            
            response = test_client.put(
                "/api/auth/users/me",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["display_name"] == "Updated User"