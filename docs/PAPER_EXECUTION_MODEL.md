# Paper Execution Model & Queue Simulation — Iran Market Radar

## 1. Point-in-Time & Look-Ahead Prevention
The execution model strictly guarantees:
$$\text{feature.available\_at} \le \text{decision\_at} < \text{order\_submitted\_at} \le \text{fill\_at}$$

- If a signal is generated at timestamp $T$ using bar close price, order execution is evaluated against the **Next-Bar ($T+1$) Auction Open**.
- Zero same-bar look-ahead fills are permitted.

---

## 2. Realistic Price Limit & Queue Modeling

### A. Limit-Up Buy Queues (صف خرید در سقف قیمت)
- If an instrument trades at its statutory upper price limit with zero selling liquidity, simulated buy orders receive `NO_FILL` / `REJECTED` status.
- Visible buying interest is not assumed to guarantee an immediate fill.

### B. Limit-Down Sell Queues (صف فروش در کف قیمت)
- When a Stop-Loss is breached on an instrument locked in limit-down queue, the position state updates to `EXIT_TRIGGERED`.
- The position remains open until actual trading volume permits partial or full execution.

---

## 3. Order Lifecycle State Machine

```
   [ CREATED ]
        │
        ▼
  [ VALIDATED ] ────(PreTrade Risk Violation)────► [ REJECTED ]
        │
        ▼
  [ SUBMITTED ]
        │
        ▼
[ ACKNOWLEDGED ]
        │
        ├──(Partial Fill)──► [ PARTIALLY_FILLED ]
        │                            │
        ▼                            ▼
   [ FILLED ]                   [ FILLED ]
        │
        ▼
[ CANCEL_REQUESTED ] ──► [ CANCELLED ] / [ EXPIRED ]
```

---

## 4. Slippage & Transaction Cost Schedule

- **Round-Trip TSE Equity Costs**:
  - Broker + Exchange + Depository + Regulator: $0.7562\%$
  - Sales Tax: $0.5000\%$
  - Total Round-Trip: $1.2562\%$
- **Linear Slippage Model**:
  $$\text{SlippageRate} = 20\text{ bps} + \left( \frac{\text{OrderQty}}{\text{BarVolume}} \times 50\text{ bps} \right)$$
