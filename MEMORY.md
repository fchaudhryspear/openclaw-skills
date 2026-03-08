# Optimus Memory

## NexDev System (2026-03-04)
- 7 model tiers operational, real API calls via nexdev_executor.py
- QwenCoder model ID: qwen-coder-plus (NOT qwen-coder)
- integration_layer.py fully wired with aiohttp
- MO_ROUTING.md v2.0 deployed with topic-aware routing
- Mode switching: /nexdev and /mo write to memory/mode.json

## Mission Control
- Backend fix deployed (formattedResults mapping)
- Stack: mission-control-api, Lambda: MonitoringFunction
- URL: https://missioncontrol.credologi.com
