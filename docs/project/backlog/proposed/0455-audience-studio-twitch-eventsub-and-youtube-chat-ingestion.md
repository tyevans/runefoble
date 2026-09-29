---
id: '0455'
title: Audience Studio Twitch EventSub and YouTube Live Chat Ingestion Engine
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0051
- TASK-0439
governing_adrs:
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0011
governing_stories:
- US-0006
- US-0031
target_release: 0.9.0
---

# TASK-0455: Audience Studio Twitch EventSub and YouTube Live Chat Ingestion Engine

## Status
Proposed

## Summary
Implement a resilient, high-concurrency external stream chat ingestion adapter in `services/audience_studio` supporting Twitch EventSub webhooks (Channel Points redemptions, chat polls) and YouTube Live Chat event streams. Ingest spectator chat commands (`!vote <option>`, `!chaos`) and reward redemptions directly into the `pollEngine`, enforcing anti-spam rate limiting and voter deduplication.

## Problem Statement
While `services/audience_studio` supports direct WebSocket client voting, PRD-0011 and US-0031 require real-time ingestion from Twitch and YouTube streaming ecosystems where spectators naturally interact. Without dedicated Twitch EventSub and YouTube Live Chat adapters, stream viewers cannot vote via chat commands or redeem Twitch Channel Points for environmental chaos modifiers, limiting spectator engagement to web client users only.

## Governing Architecture & ADRs
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Pub/sub fanout of incoming stream events and high-throughput buffer.
- **ADR-0007: Domain-Driven Design Architecture**: Service isolation within the `audience_studio` bounded context.

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0006-realtime-spectator-stream-and-chronicle.md`](../../user_stories/accepted/us-0006-realtime-spectator-stream-and-chronicle.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Scope of Work
1. **Twitch EventSub Webhook Handler (`services/audience_studio/src/integrations/twitch.ts`)**:
   - Implement Fastify webhook endpoint `/api/v1/integrations/twitch/eventsub` with HMAC-SHA256 signature verification (`Twitch-Eventsub-Message-Signature`).
   - Support `channel.channel_points_custom_reward_redemption.add` for chaos modifier triggers.
   - Ingest chat message events (`channel.chat.message`) matching `!vote [1-4]` or `!vote <option_label>`.
2. **YouTube Live Chat Adapter (`services/audience_studio/src/integrations/youtube.ts`)**:
   - Provide periodic or streaming listener for YouTube Live Chat API with token refresh and quota-conscious polling intervals.
   - Extract vote commands and forward to `pollEngine.castVote()`.
3. **Voter Deduplication & Anti-Spam (`services/audience_studio/src/integrations/dedup.ts`)**:
   - Store voter platform IDs (`twitch:<user_id>`, `youtube:<channel_id>`) in Redis with expiration matching poll duration.
   - Prevent multi-voting across platforms for the same poll.
4. **Blackbox Integration Tests (`tests/test_blackbox_audience_stream_ingestion.py`)**:
   - Simulate Twitch EventSub webhook payloads with HMAC signatures and verify vote increments in `pollEngine`.
   - Test duplicate vote prevention and error handling for malformed webhooks.

## Definition of Done
1. `services/audience_studio/src/integrations/twitch.ts` and `youtube.ts` implemented strictly < 300 lines each.
2. Webhook HMAC verification and chat command parsing validated.
3. Redis voter deduplication prevents double-voting.
4. Blackbox test suite passes with 100% assertions.
