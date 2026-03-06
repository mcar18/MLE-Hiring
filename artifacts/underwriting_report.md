# Underwriting Memo for BNPL Merchant Portfolio

## Executive Summary
The BNPL merchant portfolio presents a moderate risk profile, with an expected high-risk count of approximately 3.54 out of 50 merchants. The average predicted risk is 0.071, with an expected loss proxy of $3,946.87. **Recommendation: Approve with Conditions.**

## Data Sources & Methodology
Data was sourced from various formats including CSV, mock API, REST Countries, and a PDF scrape from ClarityPay. The risk model was built using out-of-fold evaluation and compared against two baselines to ensure robustness.

## Portfolio Risk Overview
The portfolio consists of 50 merchants, with an expected high-risk merchant count of 3.54. The average predicted risk is 0.071, while the expected loss proxy stands at $3,946.87. The risk distribution is as follows:
- Minimum risk: 0.000000468
- Mean risk: 0.071
- Median risk: 0.032
- 90th percentile risk: 0.167

## Top Risk Merchants
The following are the top 10 merchants by predicted risk:

| Merchant ID | Country        | Monthly Volume | Probability High Risk | Internal Risk Flag |
|-------------|----------------|----------------|-----------------------|---------------------|
| M005        | United States  | $45,000        | 0.521                 | High                |
| M041        | Romania        | $51,000        | 0.337                 | High                |
| M032        | United Kingdom  | $49,000        | 0.335                 | High                |
| M020        | Portugal       | $22,000        | 0.322                 | High                |
| M014        | United Kingdom  | $41,000        | 0.266                 | High                |
| M008        | United Kingdom  | $67,000        | 0.156                 | High                |
| M004        | United Kingdom  | $78,000        | 0.145                 | Medium              |
| M044        | United Kingdom  | $76,000        | 0.139                 | High                |
| M002        | United States  | $89,000        | 0.117                 | High                |
| M026        | Sweden         | $115,000       | 0.112                 | High                |

## Key Risk Drivers
The primary risk drivers identified include:
- High dispute rate merchants: 4
- Internal risk breakdown: 17 high, 17 medium, 16 low
- Feature importance ranking highlights:
  - Internal risk flag: 1.120
  - Volume growth proxy: 0.904
  - Binary high internal flag: 0.872

## External Context (ClarityPay)
ClarityPay reports a merchant count of 18, with various value propositions including flexible payment plans and instant pre-approval without credit impact. Partnerships include notable brands like Google and Club Wyndham.

## Document Insights (PDF)
The PDF insights indicate a comprehensive analysis of the portfolio, emphasizing the need for continuous monitoring and potential adjustments based on evolving market conditions.

## Model Comparison
The logistic regression model achieved a ROC AUC of 0.711, with precision, recall, and F1 scores all at 0.2. In contrast, the random forest model showed no predictive capability. The logistic regression model was chosen for its superior performance metrics.

## Recommendations & Controls
- Implement manual review for merchants with a probability of high risk greater than 0.5.
- Conduct manual review for merchants flagged as high risk internally.
- Regularly monitor dispute rates and adjust thresholds accordingly.
- Enhance data enrichment processes to improve risk assessment accuracy.

## Caveats & Assumptions
- Sample data is not representative of production.
- High dispute risk is defined as a dispute rate greater than 0.002.
- The expected loss proxy assumes a 2% loss rate on at-risk volume.
- The model may have limitations in predictive accuracy due to sample size and data quality.

**Recommendation: Approve with Conditions**
- Manual review for merchants with prob_high_risk > 0.5.
- Manual review for merchants with internal_risk_flag == high.