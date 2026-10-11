# The AI research loop (seb.ai's "AI hedge fund that remembers every mistake", built for us)
His posts (@seb.ai, 2026-10-11: DeVMfJihXuC "Grok AI hedge fund", DeOFgvvPw8v "6 bots turned $89 into $55,698") are hype reposts.
"FOMO x Grok" is a crypto/prediction-market bot, unverifiable; his Linktree sells sessions, no guide. The STRUCTURE is good, and we already have most of it:

| His agent | Ours |
|---|---|
| Idea agent | Claude reads STRATEGY-DB.csv + new sources (IG/YouTube traders Moses sends) and proposes untested ideas |
| Coder agent | new signal families in bot\lab.py / bot\gold_lab.py / custom scripts (tom.py, sd_ema.py) |
| Backtest agent | lab.py (15k+ strategies, 1-min accurate) + lab_score.py: train / test / last-6-months + random controls |
| Paper-trade agent | bot\propfarm.py (live free data, per-firm lanes, Telegram/Discord) |
| Memory DB | STRATEGY-DB.csv (strategy_db.py), RESULTS-*.md, history\LOG.md |
| Risk agent ("stops chasing pumps") | eval_opt.py / firms_compare.py sizing + daily loss stop + firm rules in the farm |
| Execution agent | TODO: TopstepX/ProjectX API or Tradovate (after paper proof) |

## How to run one research cycle (any Claude session)
1. python bot\strategy_db.py -> read the ROBUST list and the FAIL list (never retest a FAIL without a new twist).
2. Pick 3-5 new ideas (from sources Moses sends, or combos of ROBUST pieces). Code them as lab families.
3. python bot\lab.py NQ / GC -> python bot\lab_score.py NQ / GC -> keep only 7+/16 settings positive in all 3 periods AND beats the random controls.
4. Check the eval value: bot\firms_compare.py with the new strategy added. Promote to the paper farm only if net/eval improves.
5. Update STRATEGY-DB (strategy_db.py MANUAL list), history\LOG.md, memory.
Next candidates already ROBUST in the DB but not in the farm: NQ bollinger_break 5m NYAM, NQ engulfing 60m ASIA, NQ three_bar_momo 15m NYAM, NQ vwap_2sigma FADE 60m after-10, gold Asian-range 1R.
