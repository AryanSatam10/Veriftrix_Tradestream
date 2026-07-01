import logging
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# IMPORT THE SETTINGS HERE
from core.config import settings
from core.models import Commodity

logger = logging.getLogger(__name__)

class MarketDataIngestionService:
    """
    Handles scheduling or real-time pulls from global commodity indices.
    """
    
    def __init__(self):
        # Dynamically load the URL from the settings module
        self.api_base_url = settings.MARKET_DATA_API_URL
        self.timeout = httpx.Timeout(5.0, connect=2.0)

    async def fetch_latest_commodity_price(self, commodity_code: str) -> float:
        """
        Queries the external data broker for active global pricing values.
        """
        url = f"{self.api_base_url}/prices/{commodity_code}"
        
        # Dynamically load the API Key from the settings module
        headers = {"Authorization": f"Bearer {settings.MARKET_DATA_API_KEY}"}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Requesting external market updates for asset: {commodity_code}")
                response = await client.get(url, headers=headers)
                
                response.raise_for_status()
                data = response.json()
                
                return float(data.get("spot_price", 0.0))
                
            except httpx.HTTPStatusError as e:
                logger.error(f"External broker returned error status {e.response.status_code}")
                raise RuntimeError(f"Market index unavailable: Status {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"Network anomaly while communicating with index: {str(e)}")
                raise RuntimeError("Failed connection with external commodity data broker.")

    async def update_internal_price_index(self, db_session: AsyncSession, commodity_code: str) -> None:
        """
        Synchronizes external market pricing into the Postgres index layer.
        """
        try:
            live_price = await self.fetch_latest_commodity_price(commodity_code)
            
            if live_price <= 0:
                raise ValueError(f"Extracted price for {commodity_code} is structurally invalid.")

            stmt = select(Commodity).where(Commodity.commodity_code == commodity_code)
            result = await db_session.execute(stmt)
            commodity_record = result.scalar_one_or_none()

            if commodity_record:
                commodity_record.current_market_price = live_price
                commodity_record.last_updated = datetime.utcnow()
                logger.info(f"Successfully synchronized pricing index for {commodity_code}: ${live_price}")
            else:
                new_commodity = Commodity(
                    commodity_code=commodity_code,
                    display_name=commodity_code.replace("_", " ").title(),
                    current_market_price=live_price
                )
                db_session.add(new_commodity)
                logger.warning(f"Created a previously non-existent commodity signature: {commodity_code}")
                
        except Exception as e:
            logger.critical(f"Aborting persistence synchronization for {commodity_code}: {str(e)}")
            raise