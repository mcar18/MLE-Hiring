# Underwriting Memo: BNPL Merchant Portfolio Risk Analysis

## Executive Summary
The BNPL merchant portfolio exhibits moderate risk, with an expected high-risk merchant count of approximately 3.46 out of 50 total merchants. The average predicted risk stands at 0.0692, leading to an expected loss proxy of $4,447.60. 

## Data & Methodology
The risk model was built using a Random Forest algorithm, with performance metrics indicating a ROC AUC of 1.0, precision of 1.0, and recall of 1.0. Data sources include internal merchant transaction records and external insights from ClarityPay.

## Portfolio Risk Overview
- **Expected High-Risk Merchants:** 3.46
- **Average Predicted Risk:** 0.0692
- **Expected Loss Proxy:** $4,447.60
- **Assumed Loss Rate:** 0.02
- **Total Merchants:** 50

## Top Risk Merchants
1. **Merchant ID:** M005
   - **Country:** United States
   - **Monthly Volume:** $45,000
   - **Dispute Rate:** 0.0025
   - **Probability of High Risk:** 0.88

2. **Merchant ID:** M002
   - **Country:** United States
   - **Monthly Volume:** $89,000
   - **Dispute Rate:** 0.00238
   - **Probability of High Risk:** 0.84

3. **Merchant ID:** M017
   - **Country:** United Kingdom
   - **Monthly Volume:** $55,000
   - **Dispute Rate:** 0.00212
   - **Probability of High Risk:** 0.72

4. **Merchant ID:** M041
   - **Country:** Romania
   - **Monthly Volume:** $51,000
   - **Dispute Rate:** 0.00203
   - **Probability of High Risk:** 0.52

5. **Merchant ID:** M007
   - **Country:** United States
   - **Monthly Volume:** $156,000
   - **Dispute Rate:** 0.00049
   - **Probability of High Risk:** 0.10

## Key Risk Drivers
- **High Dispute Rate Merchants:** 4
- **Internal Risk Breakdown:** 
  - Medium: 17
  - High: 17
  - Low: 16

## External Context (ClarityPay)
ClarityPay offers flexible payment plans with clear terms, enabling consumers to make significant purchases with peace of mind. Their partnerships with reputable brands enhance their market presence and reliability.

## Document Insights (PDF)
The sample PDF provided contains fragmented insights and lacks coherent data, limiting its usefulness for analysis.

## Recommendations & Controls
- Review and adjust thresholds for high-risk merchant identification.
- Implement ongoing monitoring of dispute rates and transaction volumes.
- Conduct regular audits of high-risk merchants to assess risk levels.
- Enhance communication with merchants identified as high-risk to mitigate potential losses.
- Consider hyperparameter tuning for the risk model to improve predictive accuracy.

## Caveats
- Sample data only; not representative of production.
- Model is baseline (Random Forest); no hyperparameter tuning applied.
- External context (ClarityPay) is scraped; site structure may change.
- The model may have limitations due to its reliance on historical data, which may not predict future trends accurately.