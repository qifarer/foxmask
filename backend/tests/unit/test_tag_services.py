import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from tag.services import TagService
from tag.models import Tag, TagType

class TestTagService:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, test_db):
        self.tag_service = TagService()
        self.test_db = test_db

    @pytest.mark.asyncio
    async def test_create_tag(self):
        """Test creating a tag."""
        from tag.schemas import TagCreate
        tag_data = TagCreate(
            name="test-tag",
            type=TagType.USER,
            description="Test tag description",
            color="#FF0000",
            related_tags=[]
        )
        
        tag = await self.tag_service.create_tag(tag_data, "test-user-123")
        
        assert tag is not None
        assert tag.name == "test-tag"
        assert tag.type == TagType.USER
        assert tag.created_by == "test-user-123"
        assert tag.usage_count == 0

    @pytest.mark.asyncio
    async def test_create_duplicate_tag(self):
        """Test creating a duplicate tag."""
        from tag.schemas import TagCreate
        tag_data = TagCreate(name="duplicate-tag")
        
        # Create first tag
        await self.tag_service.create_tag(tag_data, "test-user-123")
        
        # Try to create duplicate
        with pytest.raises(HTTPException) as exc_info:
            await self.tag_service.create_tag(tag_data, "test-user-123")
        
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_increment_tag_usage(self):
        """Test incrementing tag usage count."""
        tag = Tag(name="usage-tag", created_by="test-user-123")
        await tag.insert()
        
        result = await self.tag_service.increment_tag_usage(str(tag.id))
        
        assert result is True
        
        # Verify usage count increased
        updated_tag = await self.tag_service.get_tag(str(tag.id))
        assert updated_tag.usage_count == 1

    @pytest.mark.asyncio
    async def test_search_tags(self):
        """Test searching tags."""
        # Create test tags
        tag1 = Tag(name="python-programming", created_by="test-user-123")
        await tag1.insert()
        
        tag2 = Tag(name="javascript-programming", created_by="test-user-123")
        await tag2.insert()
        
        tag3 = Tag(name="machine-learning", created_by="test-user-123")
        await tag3.insert()
        
        # Search for programming tags
        results = await self.tag_service.search_tags("programming")
        
        assert len(results) == 2
        assert all("programming" in tag.name for tag in results)

    @pytest.mark.asyncio
    async def test_get_popular_tags(self):
        """Test getting popular tags."""
        # Create tags with different usage counts
        tag1 = Tag(name="popular-tag", usage_count=100, created_by="test-user-123")
        await tag1.insert()
        
        tag2 = Tag(name="medium-tag", usage_count=50, created_by="test-user-123")
        await tag2.insert()
        
        tag3 = Tag(name="unpopular-tag", usage_count=1, created_by="test-user-123")
        await tag3.insert()
        
        popular_tags = await self.tag_service.get_popular_tags(limit=2)
        
        assert len(popular_tags) == 2
        assert popular_tags[0].usage_count >= popular_tags[1].usage_count
        assert popular_tags[0].name == "popular-tag"