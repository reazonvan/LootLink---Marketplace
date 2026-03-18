# Codebase Concerns

**Analysis Date:** 2026-03-18

## Tech Debt

**Bare Exception Handlers:**
- Issue: Multiple bare `except:` clauses that catch all exceptions including SystemExit and KeyboardInterrupt
- Files: `accounts/tasks_export.py:106`, `accounts/views_analytics.py:24`, `listings/search_views.py:57,63,71`, `listings/views_trading.py:123`, `tests/test_security_comprehensive.py:248-285`
- Impact: Hides errors, makes debugging difficult, swallows critical exceptions
- Fix approach: Replace with specific exception types (e.g., `except ValueError:`, `except Exception as e:`) and log errors

**Duplicate Balance Fields:**
- Issue: `Profile.balance` (line 90-96 in `accounts/models.py`) duplicates `Wallet.balance` (line 20-26 in `payments/models.py`)
- Files: `accounts/models.py`, `payments/models.py`
- Impact: Data inconsistency risk, confusion about source of truth, potential sync issues
- Fix approach: Remove `Profile.balance`, use `Wallet.balance` exclusively. Update views to reference wallet instead

**Large Monolithic Files:**
- Issue: Several files exceed 600 lines, making them hard to maintain and test
- Files: `accounts/models.py` (631 lines), `listings/views.py` (618 lines), `accounts/views.py` (571 lines), `config/settings.py` (552 lines), `payments/models.py` (533 lines)
- Impact: Reduced readability, harder to locate functionality, increased merge conflicts
- Fix approach: Split into smaller modules (e.g., separate views by concern, split models into model files per entity)

## Performance Bottlenecks

**N+1 Query Problem in Analytics:**
- Problem: `analytics_dashboard` view (lines 73-83 in `accounts/views_analytics.py`) loops through days and queries database for each day
- Files: `accounts/views_analytics.py:73-83`
- Cause: Loop with individual database queries instead of aggregation
- Improvement path: Use `annotate()` with `TruncDate` to get all data in single query, or use raw SQL with date grouping

**Multiple Separate Aggregation Queries:**
- Problem: `analytics_dashboard` makes separate queries for sales_stats, purchase_stats, reviews_stats instead of combining them
- Files: `accounts/views_analytics.py:30-101`
- Cause: Each stat section queries independently
- Improvement path: Combine related queries using `annotate()` and `aggregate()` to reduce database round trips

**Missing Query Optimization:**
- Problem: Some views lack `select_related()` or `prefetch_related()` for related objects
- Files: Various views, particularly in `listings/views_trading.py`, `transactions/views_disputes.py`
- Cause: Lazy loading of related objects causes additional queries
- Improvement path: Add `select_related()` for ForeignKey/OneToOne, `prefetch_related()` for reverse relations

## Security Considerations

**CSRF Cookie Accessibility:**
- Risk: `CSRF_COOKIE_HTTPONLY = False` (line 332 in `config/settings.py`) allows JavaScript access to CSRF token
- Files: `config/settings.py:332`
- Current mitigation: Comment explains WebSocket needs access
- Recommendations: Consider using separate CSRF token endpoint for WebSocket connections instead of exposing cookie to JavaScript

**Private Keys in Repository:**
- Risk: `.vapid_private.pem` and `private_key.pem` files present in repo root
- Files: `.vapid_private.pem`, `private_key.pem`
- Current mitigation: Should be in .gitignore
- Recommendations: Move to environment variables or secure key management system, add to .gitignore, rotate keys

**Bare Exception Handlers Hide Security Issues:**
- Risk: Security exceptions (authentication failures, permission denials) may be silently caught
- Files: `accounts/tasks_export.py:106`, `accounts/views_analytics.py:24`, `listings/search_views.py:57,63,71`
- Current mitigation: None
- Recommendations: Use specific exception handling, log all security-relevant exceptions

**Incomplete Error Handling in Export Task:**
- Risk: `generate_data_export` task (lines 99-109 in `accounts/tasks_export.py`) catches broad exceptions but nested try-except at line 102-107 has bare except
- Files: `accounts/tasks_export.py:102-107`
- Current mitigation: Logs error but bare except may hide issues
- Recommendations: Specify exception type, ensure all error paths are logged

## Fragile Areas

**Profile Model Constraints:**
- Files: `accounts/models.py:31-36, 236-241`
- Why fragile: `delete()` method raises exception instead of preventing deletion. Any code calling `.delete()` will crash
- Safe modification: Use `pre_delete` signal to prevent deletion, or override manager to prevent queryset deletion
- Test coverage: No tests for delete prevention

**Wallet Freeze/Unfreeze Operations:**
- Files: `payments/models.py:55-76`
- Why fragile: Uses `select_for_update()` but doesn't handle race conditions if multiple concurrent requests occur
- Safe modification: Add transaction isolation level configuration, add retry logic
- Test coverage: Gaps in concurrent transaction testing

**Rate Limiting Middleware:**
- Files: `core/middleware.py:14-80`
- Why fragile: Depends on cache availability but doesn't handle cache failures gracefully
- Safe modification: Add fallback behavior if cache is unavailable, add circuit breaker pattern
- Test coverage: No tests for cache failure scenarios

**Search View Exception Handling:**
- Files: `listings/search_views.py:54-72`
- Why fragile: Bare except clauses silently ignore invalid price/rating inputs
- Safe modification: Validate inputs before conversion, log invalid attempts
- Test coverage: No tests for invalid input handling

## Scaling Limits

**Database Connection Pooling:**
- Current capacity: `CONN_MAX_AGE=600` (10 minutes) with default pool size
- Limit: Under high load, connection pool may exhaust
- Scaling path: Increase `CONN_MAX_AGE`, configure `max_connections` in connection pool, use PgBouncer for connection pooling

**Cache Layer:**
- Current capacity: Redis configured with `max_connections=50` (line 362 in `config/settings.py`)
- Limit: 50 concurrent connections may be insufficient for high traffic
- Scaling path: Increase `max_connections`, implement cache warming, use Redis cluster

**Celery Task Queue:**
- Current capacity: Single Redis instance for broker and result backend
- Limit: Single point of failure, no redundancy
- Scaling path: Use RabbitMQ for broker, separate Redis for results, implement task prioritization

## Dependencies at Risk

**Yookassa Integration:**
- Risk: Hard dependency on `yookassa` library with no fallback
- Impact: Payment system unavailable if library fails to import
- Files: `payments/yookassa_integration.py:30-37`
- Migration plan: Implement payment gateway abstraction layer, add support for alternative payment providers (Stripe, PayPal)

**Django Channels with Redis:**
- Risk: WebSocket functionality depends on Redis availability
- Impact: Real-time chat/notifications fail if Redis is down
- Files: `config/settings.py:159-166`
- Migration plan: Add fallback to database-backed channel layer, implement graceful degradation

## Missing Critical Features

**Audit Logging for Financial Transactions:**
- Problem: No comprehensive audit trail for wallet operations, escrow releases, or payment processing
- Blocks: Compliance requirements, fraud investigation, dispute resolution
- Files: `payments/models.py`, `payments/yookassa_integration.py`
- Recommendation: Implement immutable transaction log with all state changes

**Rate Limiting Bypass Detection:**
- Problem: No detection for distributed rate limit attacks or proxy rotation
- Blocks: Protection against sophisticated DDoS/abuse
- Files: `core/middleware.py`
- Recommendation: Implement fingerprinting, behavioral analysis, or third-party rate limiting service

**Data Consistency Checks:**
- Problem: No periodic validation that wallet balances match transaction history
- Blocks: Early detection of data corruption or bugs
- Files: `payments/models.py`, `core/tasks.py`
- Recommendation: Add scheduled task to verify balance consistency

## Test Coverage Gaps

**Concurrent Transaction Handling:**
- What's not tested: Race conditions in wallet freeze/unfreeze, escrow operations under concurrent load
- Files: `payments/models.py:55-76`, `payments/models.py:189-250`
- Risk: Data corruption or lost updates in high-concurrency scenarios
- Priority: High

**Cache Failure Scenarios:**
- What's not tested: Behavior when Redis is unavailable, cache key collisions, cache invalidation
- Files: `core/middleware.py`, `config/settings.py:348-387`
- Risk: Silent failures or stale data served to users
- Priority: High

**Invalid Input Handling:**
- What's not tested: Malformed search parameters, invalid price ranges, SQL injection attempts in search
- Files: `listings/search_views.py:54-72`, `accounts/views_analytics.py:22-25`
- Risk: Crashes or unexpected behavior with edge case inputs
- Priority: Medium

**Export Task Failure Paths:**
- What's not tested: Disk full during export, email delivery failure, file permission issues
- Files: `accounts/tasks_export.py:18-109`
- Risk: Incomplete exports, orphaned files, user confusion
- Priority: Medium

**Escrow Auto-Release Timing:**
- What's not tested: Edge cases around release deadline, timezone handling, task retry behavior
- Files: `payments/models.py:234-243`, `config/settings.py:435-438`
- Risk: Funds stuck in escrow or released prematurely
- Priority: High

---

*Concerns audit: 2026-03-18*
