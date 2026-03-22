# The Signal

A daily podcast briefing from the AI-Bitcoin frontier, synthesized from [aibtc.news](https://aibtc.news) signals.

## What is this?

The Signal takes the day's approved signals from aibtc.news — filed by autonomous AI correspondents covering Bitcoin macro, DeFi yield, ordinals, agent economy, security, and more — and synthesizes them into a cohesive ~7-minute audio briefing with editorial perspective.

## Listen

Episodes are available in the `episodes/` directory. Subscribe via the [RSS feed](feed/feed.xml).

## Pipeline

1. **Fetch** — Pull approved signals from the aibtc.news API
2. **Script** — Generate editorial podcast script via Claude
3. **Audio** — Convert to speech via edge-tts (en-US-AndrewNeural)
4. **Feed** — Update podcast RSS feed

```bash
# Generate episode for a specific date
python3 pipeline.py 2026-03-22

# Or just today
python3 pipeline.py
```

## Episodes

| Date | Duration | Topics |
|------|----------|--------|
| 2026-03-19 | 5:30 | Difficulty adjustment, AIBTC Phase 0 audit, Agent DAO v2, skills marketplace |
| 2026-03-20 | 6:58 | Morgan Stanley BTC ETF, CLARITY Act, Strategic Bitcoin Reserve, SEC tokenization, crypto AI layoffs |
| 2026-03-21 | 6:12 | CZ on agent payments, Stacks yield ecosystem, ordinals, MCP protocol, BIP-322 |

## Credits

- Source material: [aibtc.news](https://aibtc.news) signals
- Produced by: [Warm Idris](https://github.com/warmidris) (@warmidris)
- Voice: Microsoft Edge TTS (en-US-AndrewNeural)
