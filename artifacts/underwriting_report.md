# Underwriting Memo for BNPL Merchant Portfolio

## Executive Summary
The BNPL merchant portfolio presents a moderate risk profile with an expected high-risk count of approximately 3.54 merchants. The average predicted risk stands at 0.071, with an expected loss proxy of $3,946.87. **Recommendation: Approve with Conditions.**

## Data Sources & Methodology
Data was sourced from CSV files, a mock API, REST Countries, and a PDF summary, supplemented by a ClarityPay scrape. The risk model was built using out-of-fold evaluation with two baseline models for comparison.

## Portfolio Risk Overview
The portfolio consists of 50 merchants, with an expected high-risk merchant count of 3.54. The risk distribution is as follows:
- Minimum risk: 0.000000468
- Mean risk: 0.071
- Median risk: 0.032
- 90th percentile risk: 0.167

## Top Risk Merchants
The following are the top 10 merchants by predicted risk:

| Merchant ID | Country        | Monthly Volume | Prob High Risk | Internal Risk Flag |
|-------------|----------------|----------------|----------------|---------------------|
| M005        | United States  | $45,000        | 0.521          | High                |
| M041        | Romania        | $51,000        | 0.337          | High                |
| M032        | United Kingdom  | $49,000        | 0.335          | High                |
| M020        | Portugal       | $22,000        | 0.322          | High                |
| M014        | United Kingdom  | $41,000        | 0.266          | High                |
| M008        | United Kingdom  | $67,000        | 0.156          | High                |
| M004        | United Kingdom  | $78,000        | 0.145          | Medium              |
| M044        | United Kingdom  | $76,000        | 0.139          | High                |
| M002        | United States  | $89,000        | 0.117          | High                |
| M026        | Sweden         | $115,000       | 0.112          | High                |

## Key Risk Drivers
Key risk drivers include:
- High dispute rate merchants: 4
- Internal risk breakdown: 17 high, 17 medium, 16 low
- Feature importance ranking indicates that the most significant drivers are:
  1. Internal risk flag encoded
  2. Volume growth proxy
  3. Binary high internal flag

## External Context (ClarityPay)
ClarityPay has over 1,900 merchants and has issued more than $1.2 billion in credit. The company has a growth rate of 25% and an NPS score of +91, indicating strong customer satisfaction.

## Document Insights (PDF)
The PDF insights indicate a comprehensive analysis of risk factors and trends, providing valuable context for the current portfolio assessment.

## Model Comparison
The model comparison between Logistic Regression and Random Forest shows both models achieved a ROC AUC of 0.711. However, Logistic Regression was chosen due to its consistent performance across precision, recall, and F1 score metrics.

## Recommendations & Controls
- Implement manual review for merchants with a probability of high risk greater than 0.5.
- Conduct manual review for merchants flagged as high risk internally.
- Monitor dispute rates closely and adjust thresholds as necessary.

## Caveats & Assumptions
- Sample data may not be representative of production.
- High dispute risk is defined as a dispute rate greater than 0.002.
- Expected loss proxy is based on a 2% assumed loss rate on at-risk volume.
- The model has limitations due to its reliance on sample data and external context that may change.

**Recommendation: Approve with Conditions**
- Manual review for merchants with prob_high_risk > 0.5.
- Manual review for merchants with internal_risk_flag == high.