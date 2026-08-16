# 18 — Research and Source References

Verified/retrieved during briefing preparation on 2026-08-12. Codex should re-check current documentation during implementation.

## Iran official / market infrastructure

1. Securities and Exchange Organization — announcement of new TSETMC REST web service; official docs referenced at `https://api.tsetmc.com/docs/`:
   - https://service.seo.ir/news/93205

2. TSETMC REST documentation entry point:
   - https://api.tsetmc.com/docs/

3. Codal / Rayan Bourse SEDRA data services statement describing REST API data services:
   - https://my.codal.ir/fa/statement/540929/

4. SEO material on algorithmic trading requirements/oversight; re-verify latest regulation before live integration:
   - https://service.seo.ir/news/80293
   - https://service.seo.ir/news/67862

5. 2026 SEO discussion noting algorithmic trading/API use in the Iranian market context:
   - https://service.seo.ir/news/79307
   - https://service.seo.ir/news/79215

## Core quantitative research

6. Jegadeesh, N. & Titman, S. (1993), “Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency.” Journal of Finance.
   - https://www.jstor.org/stable/2328882
   - accessible mirror retrieved: https://www.bauer.uh.edu/rsusmel/phd/jegadeesh-titman93.pdf

7. Moskowitz, T., Ooi, Y.H., Pedersen, L.H. (2012), “Time Series Momentum.” Journal of Financial Economics.
   - https://www.sciencedirect.com/science/article/pii/S0304405X11002613
   - author PDF: https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf

8. Gu, S., Kelly, B., Xiu, D. (2020), “Empirical Asset Pricing via Machine Learning.” Review of Financial Studies 33(5), 2223–2273.
   - https://academic.oup.com/rfs/article/33/5/2223/5758276
   - NBER working paper: https://www.nber.org/papers/w25398

9. Bailey, D.H., Borwein, J.M., López de Prado, M., Zhu, Q.J., “The Probability of Backtest Overfitting.”
   - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

## Tehran Stock Exchange specific research / diagnostics

10. Order imbalance and realized volatility study using TSE/IFB intraday data:
    - https://jfm.alzahra.ac.ir/article_7413_en.html

11. Order flow imbalance effects on TSE prices / largest stocks:
    - https://jfmp.sbu.ac.ir/article_103073_en.html

12. Price limits and trading halts in Tehran Stock Exchange:
    - https://jfr.ut.ac.ir/article_72749.html?lang=en

13. Machine-learning study on Tehran market/index groups (use as local evidence, not production truth):
    - https://arxiv.org/abs/2004.01497

14. Persian social sentiment and TSE prediction research:
    - https://arxiv.org/abs/1909.03792

15. Recent experimental bubble dynamics/LPPLS in Iranian stock market (research-only risk diagnostic):
    - https://arxiv.org/abs/2512.12054

## Interpretation policy

These references justify hypotheses and engineering safeguards; they do **not** prove a strategy will be profitable in current Iranian markets. Production promotion requires local point-in-time, executable, out-of-sample validation.
