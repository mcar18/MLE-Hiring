# Underwriting Memo for BNPL Merchant Portfolio

## Executive Summary
The BNPL merchant portfolio presents a moderate risk profile, with an expected high-risk count of approximately 3.54 merchants and an average predicted risk of 0.071. The expected loss proxy is estimated at $3,946.89. **Recommendation: Approve with Conditions.**

## Data Sources & Methodology
Data was sourced from a combination of CSV files, mock APIs, REST Countries for regional enrichment, and a ClarityPay scrape. The risk model was built using out-of-fold evaluation with two baseline models for comparison.

## Portfolio Risk Overview
The portfolio consists of 50 merchants, with the following risk distribution metrics:
- **Minimum Risk:** 0.0000004682300411391176
- **Mean Risk:** 0.07086350288917864
- **Median Risk:** 0.03164722557950874
- **90th Percentile Risk (p90):** 0.1667379236072478

The expected high-risk merchants count is approximately 3.54, with an expected loss proxy of $3,946.89.

## Top Risk Merchants
The following are the top 10 merchants by predicted risk:

| Merchant ID | Country       | Monthly Volume | Prob High Risk | Internal Risk Flag |
|-------------|---------------|----------------|----------------|---------------------|
| M005        | United States | $45,000        | 0.5209         | High                |
| M041        | Romania       | $51,000        | 0.3368         | High                |
| M032        | United Kingdom | $49,000       | 0.3353         | High                |
| M020        | Portugal      | $22,000        | 0.3223         | High                |
| M014        | United Kingdom | $41,000       | 0.2663         | High                |
| M008        | United Kingdom | $67,000       | 0.1557         | High                |
| M004        | United Kingdom | $78,000       | 0.1453         | Medium              |
| M044        | United Kingdom | $76,000       | 0.1386         | High                |
| M002        | United States | $89,000        | 0.1166         | High                |
| M026        | Sweden        | $115,000       | 0.1121         | High                |

## Key Risk Drivers
Key risk drivers identified include:
- **Dispute Rates:** 4 merchants have high dispute rates (>0.002).
- **Internal Risk Breakdown:** 17 merchants classified as high risk, 17 as medium, and 16 as low.
- **Feature Importance Ranking:** 
  - Internal risk flag encoded
  - Volume growth proxy
  - Binary high internal flag

## External Context (ClarityPay)
ClarityPay has over 1,900 merchants and has issued more than $1.2 billion in credit, with a growth rate of 25% and an NPS score of +91. Their value propositions include flexible payment plans and instant pre-approval.

## Document Insights (PDF)
The PDF insights indicate a structured analysis of risk metrics, though specific details are obscured. The summary suggests a focus on risk management and merchant performance.

## Model Comparison
The model comparison between Logistic Regression and Random Forest yielded the following metrics:
- **Logistic Regression:** ROC AUC: 0.7111, Precision: 0.2, Recall: 0.2, F1 Score: 0.2
- **Random Forest:** ROC AUC: 0.7111, Precision: 0.0, Recall: 0.0, F1 Score: 0.0

The Logistic Regression model was chosen due to its balanced performance across metrics.

## Recommendations & Controls
- Conduct manual reviews for merchants with a probability of high risk greater than 0.5.
- Implement manual reviews for merchants flagged as high risk internally.
- Regularly monitor dispute rates and adjust thresholds as necessary.
- Enhance data enrichment processes for better risk assessment.

## Caveats & Assumptions
- Sample data is not representative of production environments.
- High dispute risk is defined as a dispute rate greater than 0.002.
- The expected loss proxy uses a 2% assumed loss rate on at-risk volume.
- The model comparison is limited to Logistic Regression and Random Forest; chosen based on ROC AUC.

**Recommendation: Approve with Conditions**
- Manual review for merchants with prob_high_risk > 0.5.
- Manual review for merchants with internal_risk_flag == high.