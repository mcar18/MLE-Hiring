# Underwriting Memo for BNPL Merchant Portfolio

## Executive Summary
The BNPL merchant portfolio exhibits a moderate level of risk, with an expected high-risk merchant count of approximately 3.54 out of 50. The average predicted risk across the portfolio is 0.071, with an expected loss proxy of $3,946.87. Given these findings, the underwriting recommendation is **Approve with Conditions**.

## Data Sources & Methodology
Data was sourced from multiple channels including CSV files, mock APIs, REST Countries, and a ClarityPay scrape. The risk model was built using out-of-fold evaluation with two baseline models for comparison.

## Portfolio Risk Overview
The portfolio consists of 50 merchants, with an expected high-risk count of 3.54. The average predicted risk is 0.071, while the expected loss proxy is $3,946.87. The risk distribution is summarized as follows:
- Minimum risk: 0.000000468
- Mean risk: 0.071
- Median risk: 0.032
- 90th percentile risk: 0.167

## Top Risk Merchants
The following are the top 10 merchants by predicted risk:

| Merchant ID | Country        | Monthly Volume | Prob High Risk | Internal Risk Flag |
|-------------|----------------|----------------|----------------|---------------------|
| M005        | United States   | $45,000        | 0.521          | high                |
| M041        | Romania        | $51,000        | 0.337          | high                |
| M032        | United Kingdom  | $49,000        | 0.335          | high                |
| M020        | Portugal       | $22,000        | 0.322          | high                |
| M014        | United Kingdom  | $41,000        | 0.266          | high                |
| M008        | United Kingdom  | $67,000        | 0.156          | high                |
| M004        | United Kingdom  | $78,000        | 0.145          | medium              |
| M044        | United Kingdom  | $76,000        | 0.139          | high                |
| M002        | United States   | $89,000        | 0.117          | high                |
| M026        | Sweden         | $115,000       | 0.112          | high                |

## Key Risk Drivers
The primary risk drivers identified include:
- Dispute rates: 4 merchants exceed a high dispute rate (>0.002).
- Internal risk breakdown: 17 merchants classified as high risk, 17 as medium, and 16 as low.
- Feature importance ranking indicates that internal risk flags and volume growth proxies are significant predictors of risk.

## External Context (ClarityPay)
ClarityPay has over 1,900 merchants, with more than $1.2 billion in credit issued and a growth rate of 25%. The NPS score stands at +91, indicating strong customer satisfaction.

## Document Insights (PDF)
The PDF insights indicate a need for further analysis and monitoring of the portfolio's risk metrics, emphasizing the importance of ongoing evaluation.

## Model Comparison
The comparison between logistic regression and random forest models yielded the following metrics:
- ROC AUC: 0.711
- Precision: 0.2
- Recall: 0.2
- F1 Score: 0.2
- Brier Score: 0.0567

The logistic regression model was chosen due to its superior ROC AUC performance.

## Calibration & Probability Quality
Calibration metrics indicate a Brier score of 0.0567, suggesting that predicted probabilities are roughly aligned with observed outcomes. However, the small sample size limits confidence in these results, and they should be considered illustrative only.

## Recommendations & Controls
- Implement manual review for merchants with a probability of high risk greater than 0.5.
- Conduct manual review for merchants flagged as high risk internally.
- Monitor dispute rates closely for any merchants exceeding the high-risk threshold.

### Underwriting Conditions
- Manual review for merchants with prob_high_risk > 0.5.
- Manual review for merchants with internal_risk_flag == high.

## Caveats & Assumptions
- The sample data is not representative of production.
- High dispute risk is defined as a dispute rate greater than 0.002.
- The expected loss proxy uses a 2% assumed loss rate on at-risk volume.
- Calibration results are illustrative due to a very small dataset.

**Recommendation: Approve with Conditions**