"""Redis Streams background consumer for distributed asynchronous inference."""

import asyncio
import contextlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from inference_worker.config import WorkerSettings
from inference_worker.graphs import build_intent_graph, build_narration_graph, build_stand_in_graph
from inference_worker.llm_client import MultiBackendLLMClient

logger = logging.getLogger("runefoble.inference.redis_consumer")


class RedisInferenceConsumer:
    """Consumes inference tasks from Redis Streams and publishes results."""

    def __init__(self, settings: WorkerSettings, llm_client: MultiBackendLLMClient) -> None:
        self.settings = settings
        self.llm_client = llm_client
        self._running = False
        self._task: asyncio.Task | None = None
        self._redis: aioredis.Redis | None = None

        self._intent_graph = build_intent_graph(llm_client)
        self._narration_graph = build_narration_graph(llm_client)
        self._stand_in_graph = build_stand_in_graph(llm_client)

    async def start(self) -> None:
        """Start background consumer loop."""
        if not self.settings.redis_enabled:
            logger.info("Redis streams worker disabled by configuration.")
            return

        self._running = True
        self._redis = aioredis.from_url(self.settings.redis_url, decode_responses=True)

        # Ensure consumer group exists
        with contextlib.suppress(Exception):
            await self._redis.xgroup_create(
                name=self.settings.redis_stream_in,
                groupname=self.settings.redis_consumer_group,
                id="0",
                mkstream=True,
            )

        self._task = asyncio.create_task(self._consume_loop())
        logger.info(
            "Redis inference consumer started on stream '%s' group '%s'",
            self.settings.redis_stream_in,
            self.settings.redis_consumer_group,
        )

    async def stop(self) -> None:
        """Stop background consumer loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._redis:
            await self._redis.close()
            logger.info("Redis inference consumer closed.")

    async def _consume_loop(self) -> None:
        while self._running:
            try:
                assert self._redis is not None
                entries = await self._redis.xreadgroup(
                    groupname=self.settings.redis_consumer_group,
                    consumername=self.settings.redis_consumer_name,
                    streams={self.settings.redis_stream_in: ">"},
                    count=5,
                    block=2000,
                )
                if not entries:
                    continue

                for _stream_name, messages in entries:
                    for message_id, raw_fields in messages:
                        await self._process_message(message_id, raw_fields)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in Redis consumer loop: %s", e)
                await asyncio.sleep(2.0)

    async def _process_message(self, message_id: str, fields: dict[str, Any]) -> None:
        assert self._redis is not None
        try:
            task_type = fields.get("type", "unknown")
            payload_str = fields.get("payload", "{}")
            payload = json.loads(payload_str)

            result_data: dict[str, Any] = {}
            if task_type == "parse_intent":
                state = await self._intent_graph.ainvoke({"request": payload})
                result_data = state.get("parsed_action", {})
            elif task_type == "generate_narration":
                state = await self._narration_graph.ainvoke({"request": payload})
                result_data = state.get("final_response", {})
            elif task_type == "stand_in_action":
                state = await self._stand_in_graph.ainvoke({"request": payload})
                result_data = state.get("final_response", {})

            # Publish result
            correlation_id = fields.get("correlation_id", message_id)
            await self._redis.xadd(
                self.settings.redis_stream_out,
                {
                    "correlation_id": correlation_id,
                    "task_type": task_type,
                    "result": json.dumps(result_data),
                },
            )

            # Acknowledge processed message
            await self._redis.xack(
                self.settings.redis_stream_in,
                self.settings.redis_consumer_group,
                message_id,
            )
        except Exception as e:
            logger.error("Failed processing message %s: %s", message_id, e)
