from typing import Any

from app.modules.ai.service import wardrobe_summary
from app.modules.wardrobe.service import wardrobe_service


class AnalyticsService:
    async def get_user_wardrobe_analytics(self, user_id: str) -> dict[str, Any]:
        """Compute summary statistics for user's persistent wardrobe."""
        items = await wardrobe_service.get_user_items(user_id)
        return wardrobe_summary(items)


analytics_service = AnalyticsService()
