# Literature Review

Status: **Draft — Review (written by Claude under decision 0004; Codex reviews).** Sources checked 2026-10-16.

This library records what each source studied, what it found, where it differs from our system, and which spec rule it informs. Findings are paraphrased. A paper showing that something worked historically is a reason to **test** it, not evidence that our implementation will be profitable (charter §1).

**Verification column.** "Checked" means the citation and the findings stated here were confirmed on the linked page on 2026-10-16. "Not re-checked" means the bibliographic details come from prior knowledge and must be confirmed before anyone relies on a specific figure.

Companion documents: `strategy_evidence.md` (rule-by-rule evidence map), `backtesting_standards.md` (how we test), `decision_log.md` (what the evidence changed).

## 1. Trend following and time-series momentum

### Hurst, Ooi & Pedersen (2017). A Century of Evidence on Trend-Following Investing. *Journal of Portfolio Management* 44(1). — Checked ([AQR](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing?aqrPDF=1), [full text](https://fairmodel.econ.yale.edu/ec439/hurst.pdf))

- **Studied:** 67 markets (commodities, equity indices, bonds, currencies), 1880–2016. Before futures existed, cash index returns financed at short rates stand in.
- **Construction:** long if a market's past excess return is positive, short if negative. An equal mix of **1-, 3- and 12-month** lookbacks, rebalanced **monthly**. Each market is sized to equal volatility, and the portfolio is scaled to **10% annualised volatility**.
- **Costs:** returns shown after an assumed 2%/20% fee and estimated transaction costs, with costs scaled up for earlier eras. The authors note cost uncertainty and exclude futures roll costs.
- **Findings:** positive performance in each decade. Positive returns in 8 of the 10 largest 60/40 drawdowns. Low correlation with stocks and bonds. Its own worst drawdown was about 25%. Adding a 20% trend sleeve to a 60/40 portfolio lowered volatility and maximum drawdown over the sample.
- **Limits for us:** long/short futures with leverage, not long-only ETFs. The authors say the early-period strategy was not necessarily implementable. The fee and cost model is theirs, not ours.
- **Informs:** the trend sleeve (spec §4, §5 step 1); the 10% volatility figure (§5 step 6); the 60/40 benchmark choice (research protocol §5).

### Moskowitz, Ooi & Pedersen (2012). Time Series Momentum. *Journal of Financial Economics* 104(2). — Checked ([SSRN](https://papers.ssrn.com/abstract=2089463)); journal volume not re-checked

- **Studied:** 58 liquid futures and forwards across equity indices, currencies, commodities and bonds.
- **Findings:** returns persist over horizons of roughly 1 to 12 months and partly reverse over longer horizons. The authors link this to initial under-reaction followed by delayed over-reaction. A diversified portfolio earned abnormal returns with little exposure to standard factors, and did best in extreme markets. Speculators profited at hedgers' expense.
- **Limits for us:** futures, long/short. It does not test a long-only ETF version.
- **Informs:** the economic rationale for the trend sleeve, and the 12-month horizon in the momentum return.

### Faber (2007). A Quantitative Approach to Tactical Asset Allocation. *Journal of Wealth Management*. — Not re-checked ([SSRN](https://papers.ssrn.com/abstract=962461))

- **Studied:** a simple long-or-cash rule: hold an asset class when its price is above its 10-month moving average, otherwise hold cash.
- **Informs:** the simple baseline that the strategy must beat by ≥ 0.10 Sharpe (research protocol §6, simpler-rule test).

## 2. Cross-sectional (relative) momentum

### Jegadeesh & Titman (1993). Returns to Buying Winners and Selling Losers. *Journal of Finance* 48(1). — Not re-checked

- Classic evidence that US stocks with high past 3–12-month returns kept outperforming over the following months.
- **Informs:** the momentum sleeve's ranking idea.

### Asness, Moskowitz & Pedersen (2013). Value and Momentum Everywhere. *Journal of Finance* 68(3). — Not re-checked

- Momentum premia across eight asset classes, including country equity indices, bonds, currencies and commodities.
- **Informs:** applying relative momentum across asset-class ETFs rather than single stocks.

### Daniel & Moskowitz (2016). Momentum Crashes. *Journal of Financial Economics* 122(2), 221–247. — Checked ([NBER w20439](https://www.nber.org/papers/w20439))

- **Findings:** momentum suffers rare but persistent crashes. They cluster in "panic" states: after market declines, during high volatility, and as markets rebound sharply. A dynamic version that scales exposure using forecasts of momentum's mean and variance roughly doubled the static strategy's Sharpe ratio in their sample.
- **Limits for us:** this is long/short stock momentum. Our sleeve is long-only, with a positive-return filter.
- **Informs:** the positive-return filter on momentum (spec §4) and the volatility ceiling as a crash dampener. See decision log R-003.

## 3. Volatility management

### Moreira & Muir (2017). Volatility-Managed Portfolios. *Journal of Finance* 72(4), 1611–1644. — Checked ([NBER w22208](https://www.nber.org/papers/22208))

- **Findings:** cutting exposure when recent volatility is high, and raising it when low, produced higher Sharpe ratios and significant alphas across several equity factors and the currency carry trade.
- **Informs:** sizing by inverse volatility and the portfolio volatility ceiling.

### Cederburg, O'Doherty, Wang & Yan (2020). On the Performance of Volatility-Managed Portfolios. *Journal of Financial Economics* 138(1), 95–117. — Checked ([RePEc](https://ideas.repec.org/a/eee/jfinec/v138y2020i1p95-117.html))

- **Findings:** across 103 equity strategies, volatility-managed versions that could be run in real time did **not** systematically beat the originals. They often had lower Sharpe ratios out of sample. The authors attribute this mainly to structural instability in the regressions behind the earlier result.
- **Informs:** treating the volatility ceiling as a **risk control, not a return source** (decision log R-004).

## 4. Overfitting, multiple testing and decay

### McLean & Pontiff (2016). Does Academic Research Destroy Stock Return Predictability? *Journal of Finance* 71(1). — Checked ([CFA Institute digest](https://rpc.cfainstitute.org/research/cfa-digest/2016/06/does-academic-research-destroy-stock-return-predictability-digest-summary)); journal volume not re-checked

- **Findings:** across 97 published return predictors, returns were about 26% lower out of sample and about 58% lower after publication. The authors attribute the extra post-publication decline mainly to investors trading on the published findings.
- **Informs:** planning around weaker returns than papers report (decision log R-007).

### Bailey & López de Prado (2014). The Deflated Sharpe Ratio. *Journal of Portfolio Management* 40(5), 94–107. — Checked ([SSRN](https://papers.ssrn.com/abstract=2460551))

- **Findings:** corrects a Sharpe ratio for two sources of inflation: selection bias from testing many strategies, and non-normal returns.
- **Informs:** the Deflated Sharpe Ratio as a required, supplementary statistic in every Gate 3 report (`backtesting_standards.md` §5).

### Bailey & López de Prado (2021). How "Backtest Overfitting" in Finance Leads to False Discoveries. *Significance* 18(6), 22–25. — Checked ([Oxford Academic](https://academic.oup.com/jrssig/article/18/6/22/7038278))

- **Argument:** testing many variants on the same history finds patterns that are noise. The more searching, the likelier the "best" result is a false discovery. Examples include ETF launches whose backtests beat their later live results.
- **Recommendations:** adjust for the number of trials, sample length, skewness and kurtosis (the deflated Sharpe ratio); disclose every trial; require an economic rationale. The authors reject rules of thumb such as halving the Sharpe ratio.
- **Informs:** the trial registry, the trial budget and pre-registration (research protocol §1–2), and the AI-agent rules in `AGENTS.md`.

### Harvey, Liu & Zhu (2016). …and the Cross-Section of Expected Returns. *Review of Financial Studies* 29(1). — Not re-checked

- Argues for higher statistical hurdles when many factors have been tested.

### Sullivan, Timmermann & White (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *Journal of Finance* 54(5). — Not re-checked

- Corrects for testing thousands of technical rules together, and finds that the apparent winners mostly do not survive out of sample.
- **Informs:** excluding chart-pattern and indicator rules from v1.

## 5. Data

### Kenneth French Data Library (Dartmouth). — Checked ([library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html))

- Monthly and daily momentum factor series, momentum-sorted portfolios, and developed-market factor sets, including European and Japanese regions.
- **Use:** an independent sanity check that a momentum calculation behaves as the literature describes. **Not** a substitute for adjusted ETF price histories, and never used as backtest prices.

## 6. Practitioner books

| Book | Details | Status | Use |
|---|---|---|---|
| Chan, *Quantitative Trading: How to Build Your Own Algorithmic Trading Business*, 2nd ed. | Wiley, **July 2021** | Checked ([listing](https://www.abebooks.com/Quantitative-Trading-Build-Own-Algorithmic-Business/31991174687/bd), [MathWorks](https://in.mathworks.com/academia/books/quantitative-trading-chan.html)). Corrects an earlier note that gave 2026 | Practical backtesting and implementation pitfalls |
| Chan, *Algorithmic Trading: Winning Strategies and Their Rationale* | Wiley, 2013, ISBN 9781118460146 | Checked ([listing](https://tenlong.com.tw/products/9781118460146)) | Strategy rationale over curve-fitting |
| Carver, *Systematic Trading* (2015) and *Leveraged Trading* (2019) | Harriman House | Not re-checked | Volatility targeting, position sizing and cost control for individual systematic traders |

## 7. Suggested reading order

1. Hurst, Ooi & Pedersen (2017): why trend following is worth testing.
2. Moskowitz, Ooi & Pedersen (2012): the signal's research basis.
3. Bailey & López de Prado (2021), then (2014): why a backtest can look good by chance.
4. Daniel & Moskowitz (2016), and Moreira & Muir (2017) with Cederburg et al. (2020): the risks and the limits of volatility management.
5. Chan (2021): practical implementation.
