
import json, pathlib, datetime

LOG_PATH = pathlib.Path.home() / ".openclaw/workspace/memory/nexdev_session_log.jsonl"
PERF_PATH = pathlib.Path.home() / ".openclaw/workspace/memory/model_performance.json"

def log_routing(task, topic, model, latency_ms, success=True):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.datetime.now().isoformat(), "task": task[:100], "topic": topic, "model": model, "latency_ms": round(latency_ms), "success": success}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _update_performance(topic, model, latency_ms, success)

def _update_performance(topic, model, latency_ms, success):
    try:
        perf = json.loads(PERF_PATH.read_text()) if PERF_PATH.exists() else {"version": "1.0", "topics": {}}
        t = perf.setdefault("topics", {}).setdefault(topic, {}).setdefault(model, {"success": 0, "fail": 0, "avg_latency_ms": 0, "count": 0})
        t["success" if success else "fail"] += 1
        t["count"] = t.get("count", 0) + 1
        t["avg_latency_ms"] = round((t["avg_latency_ms"] * (t["count"] - 1) + latency_ms) / t["count"])
        PERF_PATH.write_text(json.dumps(perf, indent=2))
    except Exception:
        pass
