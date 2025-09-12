import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from auth.services import AuthService
from auth.models import User
from tests.conftest import mock_user_data

class TestAuthService:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, test_db):
        self.auth_service = AuthService()
        self.test_db = test_db

    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user(self, mock_user_data):
        """Test creating a new user."""
        # Mock Casdoor user info
        user_info = {
            'id': 'new-user-123',
            'name': 'newuser',
            'email': 'new@example.com',
            'displayName': 'New User',
            'avatar': 'https://example.com/avatar.jpg'
        }
        
        user = await self.auth_service.get_or_create_user(user_info)
        
        assert user is not None
        assert user.casdoor_id == 'new-user-123'
        assert user.email == 'new@example.com'
        assert user.name == 'newuser'
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_user(self, mock_user_data):
        """Test getting an existing user."""
        # First create a user
        user_info = {
            'id': 'existing-user-123',
            'name': 'existinguser',
            'email': 'existing@example.com',
            'displayName': 'Existing User'
        }
        
        user1 = await self.auth_service.get_or_create_user(user_info)
        
        # Try to get the same user again
        user2 = await self.auth_service.get_or_create_user(user_info)
        
        assert user1.id == user2.id
        assert user2.casdoor_id == 'existing-user-123'

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, mock_user_data):
        """Test getting user by ID."""
        user_info = {
            'id': 'test-user-by-id',
            'name': 'testuser',
            'email': 'test@example.com',
            'displayName': 'Test User'
        }
        
        created_user = await self.auth_service.get_or_create_user(user_info)
        found_user = await self.auth_service.get_user_by_id(str(created_user.id))
        
        assert found_user is not None
        assert found_user.id == created_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_casdoor_id(self, mock_user_data):
        """Test getting user by Casdoor ID."""
        user_info = {
            'id': 'test-casdoor-id',
            'name': 'testuser',
            'email': 'test@example.com',
            'displayName': 'Test User'
        }
        
        created_user = await self.auth_service.get_or_create_user(user_info)
        found_user = await self.auth_service.get_user_by_casdoor_id('test-casdoor-id')
        
        assert found_user is not None
        assert found_user.casdoor_id == 'test-casdoor-id'

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, mock_user_data):
        """Test getting user by email."""
        user_info = {
            'id': 'test-email-user',
            'name': 'testuser',
            'email': 'email@example.com',
            'displayName': 'Test User'
        }
        
        created_user = await self.auth_service.get_or_create_user(user_info)
        found_user = await self.auth_service.get_user_by_email('email@example.com')
        
        assert found_user is not None
        assert found_user.email == 'email@example.com'

    @pytest.mark.asyncio
    async def test_update_user(self, mock_user_data):
        """Test updating user information."""
        user_info = {
            'id': 'update-user-123',
            'name': 'updateuser',
            'email': 'update@example.com',
            'displayName': 'Update User'
        }
        
        user = await self.auth_service.get_or_create_user(user_info)
        
        # Update user
        from auth.schemas import UserUpdate
        update_data = UserUpdate(
            display_name="Updated Display Name",
            avatar="https://example.com/new-avatar.jpg"
        )
        
        updated_user = await self.auth_service.update_user(user, update_data)
        
        assert updated_user.display_name == "Updated Display Name"
        assert updated_user.avatar == "https://example.com/new-avatar.jpg"

    @pytest.mark.asyncio
    async def test_delete_user(self, mock_user_data):
        """Test deleting a user."""
        user_info = {
            'id': 'delete-user-123',
            'name': 'deleteuser',
            'email': 'delete@example.com',
            'displayName': 'Delete User'
        }
        
        user = await self.auth_service.get_or_create_user(user_info)
        result = await self.auth_service.delete_user(str(user.id))
        
        assert result is True
        
        # Verify user is deleted
        deleted_user = await self.auth_service.get_user_by_id(str(user.id))
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self):
        """Test deleting a user that doesn't exist."""
        result = await self.auth_service.delete_user("nonexistent-id")
        assert result is False