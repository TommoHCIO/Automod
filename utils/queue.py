"""
Message Queue for Rate Limiting
Prevents Discord API rate limiting (50 req/sec limit)
"""

import asyncio
import logging
from collections import deque
from typing import Callable, Any
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class MessageQueue:
    """
    Async message queue with rate limiting
    Keeps bot under Discord's 50 requests/second limit
    """
    
    def __init__(
        self,
        max_requests_per_second: int = 40,
        delay_between_messages: float = 0.5
    ):
        """
        Initialize message queue
        
        Args:
            max_requests_per_second: Maximum requests per second (default: 40, safe margin)
            delay_between_messages: Delay between processing messages in seconds
        """
        self.max_requests_per_second = max_requests_per_second
        self.delay_between_messages = delay_between_messages
        
        self.queue = deque()
        self.processing = False
        self.request_timestamps = deque()
        
        # Statistics
        self.total_processed = 0
        self.total_queued = 0
        
        logger.info(f"Message queue initialized: {max_requests_per_second} req/s limit")
    
    async def add_to_queue(
        self,
        callback: Callable,
        *args,
        **kwargs
    ) -> asyncio.Future:
        """
        Add a message processing task to the queue
        
        Args:
            callback: Async function to call
            *args, **kwargs: Arguments for the callback
        
        Returns:
            Future that will contain the result
        """
        future = asyncio.Future()
        
        self.queue.append({
            "callback": callback,
            "args": args,
            "kwargs": kwargs,
            "future": future,
            "queued_at": datetime.now(timezone.utc)
        })
        
        self.total_queued += 1
        
        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self._process_queue())
        
        return future
    
    async def _process_queue(self):
        """Process queued messages with rate limiting"""
        self.processing = True
        
        while self.queue:
            # Check rate limit
            await self._enforce_rate_limit()
            
            # Get next item
            item = self.queue.popleft()
            
            try:
                # Execute callback
                result = await item["callback"](*item["args"], **item["kwargs"])
                
                # Set result on future
                if not item["future"].done():
                    item["future"].set_result(result)
                
                self.total_processed += 1
                
                # Track request timestamp
                self.request_timestamps.append(datetime.now(timezone.utc))
                
                # Clean old timestamps (older than 1 second)
                self._clean_old_timestamps()
                
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                
                # Set exception on future
                if not item["future"].done():
                    item["future"].set_exception(e)
            
            # Delay between messages
            if self.queue:  # Only delay if there are more messages
                await asyncio.sleep(self.delay_between_messages)
        
        self.processing = False
        logger.debug("Queue processing completed")
    
    async def _enforce_rate_limit(self):
        """Ensure we don't exceed rate limit"""
        # Clean old timestamps
        self._clean_old_timestamps()
        
        # If we're at the limit, wait
        while len(self.request_timestamps) >= self.max_requests_per_second:
            await asyncio.sleep(0.1)
            self._clean_old_timestamps()
    
    def _clean_old_timestamps(self):
        """Remove timestamps older than 1 second"""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        while self.request_timestamps and self.request_timestamps[0] < cutoff:
            self.request_timestamps.popleft()
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        return {
            "queue_size": len(self.queue),
            "total_processed": self.total_processed,
            "total_queued": self.total_queued,
            "current_rate": len(self.request_timestamps),
            "max_rate": self.max_requests_per_second,
            "is_processing": self.processing
        }
    
    def clear_queue(self):
        """Clear all pending items"""
        cleared = len(self.queue)
        
        # Cancel all futures
        while self.queue:
            item = self.queue.popleft()
            if not item["future"].done():
                item["future"].cancel()
        
        logger.info(f"Cleared {cleared} items from queue")
        return cleared
