import asyncio
import logging

import aiohttp

from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ielts_daily_trigger")


async def run() -> None:
    settings = get_settings()
    if not settings.daily_job_url or not settings.daily_job_secret:
        raise RuntimeError("DAILY_JOB_URL and DAILY_JOB_SECRET are required for the cron service")
    timeout = aiohttp.ClientTimeout(total=90, connect=30)
    async with aiohttp.ClientSession(timeout=timeout) as client:
        for attempt in range(3):
            try:
                async with client.post(
                    settings.daily_job_url,
                    headers={"X-Daily-Job-Secret": settings.daily_job_secret.get_secret_value()},
                ) as response:
                    if response.status == 200:
                        logger.info("Daily message trigger completed")
                        return
                    logger.warning("Daily trigger returned status %s", response.status)
                    if response.status not in {502, 503, 504}:
                        response.raise_for_status()
            except (aiohttp.ClientError, TimeoutError):
                logger.warning("Daily trigger request failed (attempt %s/3)", attempt + 1)
            if attempt < 2:
                await asyncio.sleep(2**attempt)
    raise RuntimeError("Daily trigger failed after retries")


if __name__ == "__main__":
    asyncio.run(run())
