# Underwriting Memo for BNPL Merchant Portfolio

## Executive Summary
The BNPL merchant portfolio exhibits a moderate risk profile, with an expected high-risk merchant count of approximately 3.54 out of 50. The average predicted risk stands at 0.071, with an expected loss proxy of $3,946.87. **Recommendation: Approve with Conditions.**

## Data Sources & Methodology
Data was sourced from a combination of CSV files, a mock API, REST Countries for regional enrichment, and a PDF document. The risk model was built using out-of-fold evaluation with two baseline models, ensuring robust performance metrics.

## Portfolio Risk Overview
The portfolio consists of 50 merchants, with an expected high-risk count of 3.54. The average predicted risk is 0.071, while the expected loss proxy is calculated at $3,946.87. The risk distribution is as follows:
- Minimum: 0.000000468
- Mean: 0.071
- Median: 0.032
- 90th Percentile: 0.167

## Top Risk Merchants
The following are the top 10 merchants by predicted risk:

| Merchant ID | Country        | Monthly Volume | Probability of High Risk | Internal Risk Flag |
|-------------|----------------|----------------|--------------------------|---------------------|
| M005        | United States  | $45,000        | 0.521                    | High                |
| M041        | Romania        | $51,000        | 0.337                    | High                |
| M032        | United Kingdom  | $49,000        | 0.335                    | High                |
| M020        | Portugal       | $22,000        | 0.322                    | High                |
| M014        | United Kingdom  | $41,000        | 0.266                    | High                |
| M008        | United Kingdom  | $67,000        | 0.156                    | High                |
| M004        | United Kingdom  | $78,000        | 0.145                    | Medium              |
| M044        | United Kingdom  | $76,000        | 0.139                    | High                |
| M002        | United States  | $89,000        | 0.117                    | High                |
| M026        | Sweden         | $115,000       | 0.112                    | High                |

## Key Risk Drivers
Key risk drivers identified include:
- High dispute rate merchants: 4
- Internal risk breakdown: 17 high, 17 medium, 16 low
- Feature importance ranking indicates that the most significant drivers are:
  - Internal risk flag
  - Volume growth proxy
  - Binary high internal flag

## External Context (ClarityPay)
ClarityPay has over 1,900 merchants and has issued more than $1.2 billion in credit. The company reports a growth rate of 25% and an NPS score of +91, highlighting strong customer satisfaction.

## Document Insights (PDF)
The PDF insights indicate various metrics related to the portfolio, including transaction counts and risk assessments, although specific details are obscured.

## Model Comparison
The model comparison between Logistic Regression and Random Forest shows both models have a ROC AUC of 0.711. However, Logistic Regression is preferred due to its performance in precision, recall, and F1 score metrics, all at 0.2.

## Recommendations & Controls
- Implement manual reviews for merchants with a probability of high risk greater than 0.5.
- Conduct manual reviews for merchants flagged as high risk internally.
- Regularly monitor dispute rates and adjust thresholds accordingly.
- Enhance data collection methods to improve model accuracy.

### Underwriting Conditions
- Manual review for merchants with prob_high_risk > 0.5.
- Manual review for merchants with internal_risk_flag == high.

## Caveats & Assumptions
- Sample data may not represent production conditions.
- High dispute risk is defined as a dispute rate exceeding 0.002.
- Expected loss proxy is based on a 2% assumed loss rate on at-risk volume.
- The external context from ClarityPay is based on scraped data, which may change.

**Recommendation: Approve with Conditions**  
Conditions: Manual review for merchants with prob_high_risk > 0.5 and for those with internal_risk_flag == high.