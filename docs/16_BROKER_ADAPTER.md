# 16 — Future Broker Adapter Contract

Phase 1 ships the contract + paper adapter only. A real adapter requires explicit documented/authorized broker access.

## 1. Interface

Conceptual protocol:

```python
class BrokerAdapter(Protocol):
    async def health(self) -> BrokerHealth: ...
    async def get_account(self) -> AccountSnapshot: ...
    async def get_positions(self) -> list[BrokerPosition]: ...
    async def get_open_orders(self) -> list[BrokerOrder]: ...
    async def submit_order(self, order: BrokerOrderRequest, idempotency_key: str) -> BrokerOrder: ...
    async def cancel_order(self, broker_order_id: str) -> BrokerOrder: ...
    async def replace_order(self, broker_order_id: str, change: OrderChange) -> BrokerOrder: ...
    async def get_order(self, broker_order_id: str) -> BrokerOrder: ...
    async def get_fills(self, since) -> list[BrokerFill]: ...
```

Optional capabilities advertised explicitly:
- native stop order;
- native take profit;
- OCO/bracket;
- conditional order;
- validity/GTC equivalents;
- streaming order updates.

ExecutionEngine must not assume a capability exists.

## 2. Capability negotiation

```json
{
  "supports_market_order": false,
  "supports_limit_order": true,
  "supports_stop": false,
  "supports_oco": false,
  "supports_replace": true,
  "supports_streaming": false
}
```

If broker lacks native stop/OCO, future live execution may emulate monitoring **only if authorized and operationally safe**, otherwise require manual/native broker controls.

## 3. Authentication

Adapter owns authentication lifecycle. No broker token in frontend. Refresh/expiry state is monitored. Authentication failure blocks new orders.

## 4. Idempotency

Internal order intent ID maps one-to-one to idempotency key. On timeout/unknown response:
1. query broker order state;
2. reconcile before retry;
3. never blindly resubmit.

## 5. Instrument mapping

Maintain broker instrument code ↔ canonical instrument mapping; validate before trading. Never submit based on Persian ticker text alone.

## 6. Reconciliation

At startup and periodically:
- fetch broker cash/positions/orders/fills;
- compare internal ledger;
- surface mismatches;
- block automated new orders if discrepancy exceeds tolerance.

## 7. SL/TP logic

Internal desired trade can contain:
- entry intent;
- stop/invalidation;
- take-profit/trailing policy.

After entry fill:
- if broker supports native bracket/OCO, map it;
- if only conditional SL/TP exists, use documented capability;
- otherwise keep exit intent in monitored execution engine only after explicit live safety approval.

A stop trigger does not guarantee fill in a price-limited/queued market.

## 8. Regulatory/authorization note

Iran's market has specific requirements around algorithmic orders and broker identification/oversight. The project must use the broker's authorized route and preserve required order/audit metadata. Current SEO materials should be re-verified before enabling live mode.
