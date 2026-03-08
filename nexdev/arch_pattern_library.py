#!/usr/bin/env python3
"""
NexDev Architectural Patterns Library (Phase 2 Feature)

Stores, retrieves, and suggests architectural patterns based on use cases.
Learns from successful past projects to recommend proven solutions.
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

PATTERNS_DB_PATH = Path.home() / ".openclaw/workspace/nexdev/patterns_db.json"


@dataclass
class Pattern:
    """Represents an architectural pattern."""
    id: str
    name: str
    category: str  # "microservice", "monolith", "event-driven", etc.
    description: str
    use_cases: List[str]
    technologies: List[str]
    pros: List[str]
    cons: List[str]
    complexity: str  # "low", "medium", "high"
    team_size_required: int
    success_count: int  # How many times this pattern worked well
    example_code: Optional[str] = None
    anti_patterns: Optional[List[str]] = None  # What NOT to do
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Default patterns database
DEFAULT_PATTERNS = [
    Pattern(
        id="auth-service",
        name="Centralized Authentication Service",
        category="security",
        description="Single service handling authentication/authorization across all applications",
        use_cases=[
            "Multiple services need auth",
            "Enterprise applications",
            "SaaS platforms",
            "Multi-tenant systems"
        ],
        technologies=["OAuth 2.0", "JWT", "Keycloak", "Auth0", "Cognito"],
        pros=[
            "Single source of truth for user data",
            "Consistent security policies",
            "Easier compliance audits",
            "SSO support out of box"
        ],
        cons=[
            "Single point of failure risk",
            "Can become bottleneck at scale",
            "Complexity in migration if vendor changes"
        ],
        complexity="medium",
        team_size_required=3,
        success_count=15,
        example_code='''# Example OAuth2 token endpoint
@app.route('/oauth/token', methods=['POST'])
def issue_token():
    credentials = request.json
    user = authenticate(credentials.username, credentials.password)
    
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    
    token = jwt.encode({
        'sub': user.id,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, SECRET_KEY)
    
    return jsonify({"access_token": token}), 200''',
        anti_patterns=[
            "Don't hardcode secrets in application code",
            "Don't store passwords in plaintext",
            "Avoid rolling your own crypto"
        ]
    ),
    
    Pattern(
        id="api-gateway-pattern",
        name="API Gateway Pattern",
        category="architecture",
        description="Single entry point that routes requests to backend services",
        use_cases=[
            "Microservices architecture",
            "Mobile and web clients",
            "Rate limiting needed",
            "Request aggregation required"
        ],
        technologies=["Kong", "Apigee", "AWS API Gateway", "nginx", "Express Gateway"],
        pros=[
            "Client abstraction from internal structure",
            "Centralized cross-cutting concerns",
            "Easier versioning",
            "Built-in rate limiting/auth"
        ],
        cons=[
            "Additional network hop",
            "Single point of failure",
            "Can become overly complex"
        ],
        complexity="medium",
        team_size_required=4,
        success_count=22,
        example_code='''# Kong route configuration
{
  "routes": [
    {
      "name": "user-service-route",
      "paths": ["/api/users"],
      "strip_path": true,
      "upstream_url": "http://user-service:8080",
      "plugins": ["rate-limiting", "jwt"]
    }
  ]
}''',
        anti_patterns=[
            "Don't put business logic in gateway",
            "Avoid tight coupling between gateway and services",
            "Don't expose internal ports directly"
        ]
    ),
    
    Pattern(
        id="event-sourcing",
        name="Event Sourcing Pattern",
        category="data",
        description="Store state as sequence of events rather than current state",
        use_cases=[
            "Audit trail required",
            "Temporal queries needed",
            "Financial systems",
            "Inventory management"
        ],
        technologies=["EventStoreDB", "Axon", "Kafka", "RabbitMQ"],
        pros=[
            "Complete audit history",
            "Can reconstruct any point in time",
            "Supports CQRS naturally",
            "Excellent for debugging"
        ],
        cons=[
            "Complex query patterns",
            "Event schema evolution challenges",
            "Requires mindset shift",
            "Storage overhead"
        ],
        complexity="high",
        team_size_required=5,
        success_count=8,
        example_code='''# Event store repository
class OrderRepository:
    def __init__(self, event_store):
        self.event_store = event_store
    
    def get_order(self, order_id):
        events = self.event_store.get_events(order_id)
        order = Order()
        for event in events:
            order.apply(event)
        return order
    
    def save(self, order):
        new_events = order.get_uncommitted_events()
        self.event_store.append(order.id, new_events)
        order.mark_events_as_committed()''',
        anti_patterns=[
            "Don't use when simple CRUD suffices",
            "Avoid storing PII in events",
            "Don't forget about snapshotting for performance"
        ]
    ),
    
    Pattern(
        id="circuit-breaker",
        name="Circuit Breaker Pattern",
        category="resilience",
        description="Prevent cascading failures by failing fast when downstream service unavailable",
        use_cases=[
            "External API calls",
            "Database connections",
            "Third-party integrations",
            "High-latency operations"
        ],
        technologies=["Hystrix", "Resilience4j", "pybreaker", " Polly (.NET)"],
        pros=[
            "Prevents cascade failures",
            "Graceful degradation possible",
            "Faster failure detection",
            "Automatic recovery"
        ],
        cons=[
            "Added complexity",
            "Need to define fallback behavior",
            "Can hide real problems"
        ],
        complexity="medium",
        team_size_required=2,
        success_count=18,
        example_code='''# Circuit breaker decorator
import pybreaker

order_service_breaker = pybreaker.CircuitBreaker(
    name='order-service',
    fail_max=3,
    reset_timeout=30,
    state_storage=MemoryStorage()
)

@order_service_breaker
def get_orders(customer_id):
    response = requests.get(f'http://orders/{customer_id}', timeout=5)
    return response.json()''',
        anti_patterns=[
            "Don't set too low fail_max threshold",
            "Always provide meaningful fallback",
            "Monitor circuit state metrics"
        ]
    ),
    
    Pattern(
        id="cache-aside",
        name="Cache-Aside Pattern",
        category="performance",
        description="Application manages cache separately from data source",
        use_cases=[
            "Read-heavy workloads",
            "Expensive queries",
            "Frequently accessed data",
            "CDN caching"
        ],
        technologies=["Redis", "Memcached", "Varnish", "CloudFront"],
        pros=[
            "Improved read performance",
            "Reduced database load",
            "Simple to implement",
            "Granular cache control"
        ],
        cons=[
            "Cache invalidation complexity",
            "Stale data risk",
            "Memory management"
        ],
        complexity="low",
        team_size_required=2,
        success_count=30,
        example_code='''# Cache-aside implementation
def get_user(user_id):
    # Try cache first
    cached = redis_client.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    
    # Cache miss - load from DB
    user = db.query(User).filter_by(id=user_id).first()
    
    # Populate cache
    if user:
        redis_client.setex(
            f"user:{user_id}",
            TTL_HOURS * 3600,
            json.dumps(user.to_dict())
        )
    
    return user''',
        anti_patterns=[
            "Don't cache everything",
            "Set appropriate TTL values",
            "Handle cache stampede with locking"
        ]
    ),
    
    Pattern(
        id=" Saga-orchestration",
        name="Saga Orchestration Pattern",
        category="distributed-transactions",
        description="Manage distributed transactions through compensating actions",
        use_cases=[
            "Multi-step workflows",
            "Cross-service transactions",
            "Order processing pipelines",
            "Payment flows"
        ],
        technologies=["Temporal", "Camunda", "Zeebe", "Custom orchestration"],
        pros=[
            "Maintains data consistency",
            "Compensating rollbacks",
            "Visible workflow state",
            "Retry support built-in"
        ],
        cons=[
            "Complex implementation",
            "Debugging difficulties",
            "Potential infinite loops"
        ],
        complexity="high",
        team_size_required=4,
        success_count=12,
        example_code='''# Saga definition
@saga(name="OrderSaga")
def process_order(order_id: str):
    yield create_inventory_reservation(order_id)
    yield charge_payment(order_id)
    yield ship_order(order_id)
    yield send_confirmation_email(order_id)

@process_order.compensate
def cancel_order(order_id: str):
    yield release_inventory(order_id)
    yield refund_payment(order_id)
    yield cancel_shipment(order_id)
''',
        anti_patterns=[
            "Don't block sagas unnecessarily",
            "Keep compensation logic simple",
            "Implement saga timeout"
        ]
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Pattern Database Management
# ──────────────────────────────────────────────────────────────────────────────

def init_patterns_db():
    """Initialize patterns database with defaults if it doesn't exist."""
    if not PATTERNS_DB_PATH.exists():
        patterns = {
            "patterns": [p.to_dict() for p in DEFAULT_PATTERNS],
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
        with open(PATTERNS_DB_PATH, 'w') as f:
            json.dump(patterns, f, indent=2)


def load_patterns() -> List[Pattern]:
    """Load all patterns from database."""
    init_patterns_db()
    
    try:
        with open(PATTERNS_DB_PATH) as f:
            data = json.load(f)
        
        return [Pattern.from_dict(p) for p in data.get("patterns", [])]
    except Exception as e:
        print(f"Error loading patterns: {e}")
        return []


def add_pattern(pattern: Pattern):
    """Add a new pattern or update existing one."""
    patterns = load_patterns()
    
    # Check if exists
    existing_idx = next((i for i, p in enumerate(patterns) if p.id == pattern.id), None)
    
    if existing_idx is not None:
        patterns[existing_idx] = pattern
    else:
        patterns.append(pattern)
    
    # Save updated database
    db_data = {
        "patterns": [p.to_dict() for p in patterns],
        "last_updated": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    with open(PATTERNS_DB_PATH, 'w') as f:
        json.dump(db_data, f, indent=2)


def increment_success_count(pattern_id: str):
    """Increment success count for a pattern after successful usage."""
    patterns = load_patterns()
    
    for p in patterns:
        if p.id == pattern_id:
            p.success_count += 1
            break
    
    add_pattern(pattern)  # Reuse save logic


def search_patterns(query: str, category: Optional[str] = None) -> List[Pattern]:
    """Search patterns by keyword and optionally filter by category."""
    patterns = load_patterns()
    
    results = []
    query_lower = query.lower()
    
    for p in patterns:
        match_score = 0
        
        # Search in name
        if query_lower in p.name.lower():
            match_score += 3
        
        # Search in description
        if query_lower in p.description.lower():
            match_score += 2
        
        # Search in use cases
        for use_case in p.use_cases:
            if query_lower in use_case.lower():
                match_score += 1
        
        # Search in technologies
        for tech in p.technologies:
            if query_lower in tech.lower():
                match_score += 1
        
        if match_score > 0:
            results.append((match_score, p))
    
    # Sort by match score descending
    results.sort(key=lambda x: x[0], reverse=True)
    
    # Apply category filter if specified
    if category:
        results = [(score, p) for score, p in results if p.category == category]
    
    return [p for _, p in results]


def get_patterns_for_use_case(use_case: str) -> List[Pattern]:
    """Get patterns recommended for a specific use case."""
    return search_patterns(use_case)


def recommend_pattern(
    requirements: Dict[str, Any],
    constraints: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Recommend patterns based on requirements and constraints.
    
    Args:
        requirements: Dict with keys like "scalability", "team_size", "complexity_tolerance", "tech_stack"
        constraints: Dict with keys like "max_team_size", "budget", "timeline"
        
    Returns:
        List of recommended patterns ranked by suitability
    """
    recommendations = []
    
    patterns = load_patterns()
    
    for pattern in patterns:
        score = 0
        notes = []
        
        # Score based on complexity match
        req_complexity = requirements.get("complexity_tolerance", "medium")
        if pattern.complexity == req_complexity:
            score += 3
        elif abs(["low", "medium", "high"].index(pattern.complexity) - 
                 ["low", "medium", "high"].index(req_complexity)) <= 1:
            score += 1
        
        # Score based on team size compatibility
        max_team = constraints.get("max_team_size", 10) if constraints else 10
        if pattern.team_size_required <= max_team:
            score += 2
        else:
            score -= 2
            notes.append(f"Requires {pattern.team_size_required} people (beyond max)")
        
        # Score based on technology overlap
        tech_stack = requirements.get("tech_stack", [])
        overlapping_techs = [t for t in pattern.technologies if t in tech_stack]
        if overlapping_techs:
            score += len(overlapping_techs)
        
        # Boost patterns with high success counts
        score += min(pattern.success_count * 0.5, 5)
        
        if score > 0:
            recommendations.append({
                "pattern": pattern,
                "score": score,
                "notes": notes,
                "recommended_tech": pattern.technologies[0] if pattern.technologies else None
            })
    
    # Sort by score
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return recommendations


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("🏛️  ARCHITECTURAL PATTERNS LIBRARY - DEMO")
    print("=" * 60)
    
    # Initialize DB
    init_patterns_db()
    print("\n✅ Patterns database initialized")
    
    # Load all patterns
    patterns = load_patterns()
    print(f"\n📚 Loaded {len(patterns)} architectural patterns")
    
    # Display categories
    categories = {}
    for p in patterns:
        if p.category not in categories:
            categories[p.category] = []
        categories[p.category].append(p.name)
    
    print("\nPatterns by Category:")
    for cat, names in categories.items():
        print(f"\n  {cat.upper()} ({len(names)}):")
        for name in names[:3]:  # Show first 3
            print(f"    • {name}")
    
    # Search demo
    print("\n" + "=" * 60)
    print("SEARCH DEMO")
    print("=" * 60)
    
    test_queries = [
        "authentication oauth",
        "cache redis performance",
        "circuit breaker resilient"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Searching: '{query}'")
        results = search_patterns(query)
        
        for score, pattern in results[:3]:
            print(f"   {score}pts: {pattern.name} (successes: {pattern.success_count})")
    
    # Recommendations demo
    print("\n" + "=" * 60)
    print("RECOMMENDATION DEMO")
    print("=" * 60)
    
    requirements = {
        "complexity_tolerance": "medium",
        "team_size": 4,
        "tech_stack": ["Python", "Redis", "PostgreSQL"],
        "scalability": "high"
    }
    
    constraints = {
        "max_team_size": 6,
        "budget": "$10k/month"
    }
    
    print("\nRequirements:", requirements)
    print("Constraints:", constraints)
    
    recs = recommend_pattern(requirements, constraints)
    
    print("\nTop Recommendations:")
    for i, rec in enumerate(recs[:5], 1):
        print(f"\n  {i}. {rec['pattern'].name}")
        print(f"     Score: {rec['score']:.1f}")
        print(f"     Recommended Tech: {rec['recommended_tech']}")
        if rec['notes']:
            print(f"     Notes: {'; '.join(rec['notes'])}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
