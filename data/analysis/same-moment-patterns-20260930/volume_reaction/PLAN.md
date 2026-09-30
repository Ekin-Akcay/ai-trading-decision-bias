# Early volume and price reaction, at existing AI moments

Written before calculating this family. Use only the 1020 existing Terra MA-present opinions and their original native minute paths, already consolidated in new-angles-20260930/target_exhaustion. The paired90 cohort contributes MA_A once. No new AI calls, new sampled dates, refits or parameter optimization. Costs are zero. This is exploratory reuse of outcomes, not independent confirmation.

Question: does observed early price/volume behavior distinguish an AI continuation call that should be faded? Prior work included static volume features and simple early direction confirmation. This extension conditions on early traded volume plus excursion/recovery geometry; it is not a claim to observe actual order-book absorption.

Observe exactly the first30 complete minutes after the original decision. Let O be the first minute open, H/L the highest/lowest price in those30 minutes, and C the last close. ATR is the original pre-entry ATR14 fraction, converted to price distance O*ATR. Let volume_ratio be the first30-minute volume sum divided by the median of100 non-overlapping30-minute sums during the immediately preceding50 hours. Use native one-minute volume for both numerator and denominator. Require complete finite nonnegative volume, positive reference median and valid OHLC; record every coverage exclusion without using future return. Current volume becomes known at elapsed30 minutes. Enter at minute31 open, hold120 complete minutes, exit at minute150 close. No stop or target.

Four candidate policies, frozen thresholds:

1. **Long after sell-pressure recovery:** AI SHORT; O−L >=0.5*O*ATR; C >=(H+L)/2; volume_ratio >=1.5. Buy.
2. **Short after buy-pressure rejection:** AI LONG; H−O >=0.5*O*ATR; C <=(H+L)/2; volume_ratio >=1.5. Sell.
3. **Long after quiet downward extension:** AI SHORT; O−C >=0.5*O*ATR; volume_ratio <=0.75. Buy.
4. **Short after quiet upward extension:** AI LONG; C−O >=0.5*O*ATR; volume_ratio <=0.75. Sell.

These are observable price/volume patterns. Words such as recovery, rejection or pressure do not establish retail positions, actual liquidity, causation or institutional activity. All four candidates share one observation period and one exit; no alternative horizons or cuts may replace them after scoring.

For each candidate, save controls using (a) the same volume/price pattern irrespective of AI action and (b) the same AI/price geometry without the volume condition. Additionally save long-after-AI-SHORT and short-after-AI-LONG at the same30/120-minute clock. These10 controls plus four candidates are all retained. AI-free price-pattern performance is separately useful even if AI adds no value. Report both mean per executed trade and mean per original eligible opportunity (skips zero); unmatched conditional means are not a causal AI estimate.

Save all1020 opportunities for each definition, every missing-data exclusion, features, side, entry/exit price and time, return, MFE/MAE and cohort. Original entry timestamps are the within-period clusters; simultaneous assets stay together. Report cohorts, assets, calendar years, chronological halves/five folds, individual and block counts, worst position, win/payoff sizes, removal of best1/3 original-entry blocks, and full-quarter bootstrap uncertainty (20000 shared draws, seed2026093041). Use the full14-definition family for simultaneous bootstrap intervals and all8 candidate-minus-control opportunity differences as a second family. Intervals remain exploratory given previous search history and outcome reuse.

A positive mean is reported as an observed gross result. A stronger research lead additionally needs30 executed entry-time blocks, positive chronological halves, positive mean without the three best contributing blocks, and a simultaneous lower bound above zero. Report whether price-only controls satisfy the same descriptive checks; do not require an AI increment merely to identify a gross price strategy. A claim about added AI or volume information separately needs a paired opportunity difference and its interval. No passing local screen can be called a verified live profit strategy. No further trade-agent credits will be spent.
