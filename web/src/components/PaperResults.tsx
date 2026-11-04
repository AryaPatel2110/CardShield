const models = [
  { name: 'Logistic Regression', precision: '85%', recall: '43%', f1: '0.57' },
  { name: 'Decision Tree', precision: '74%', recall: '97%', f1: '0.84' },
  { name: 'Random Forest · baseline', precision: '97%', recall: '79%', f1: '0.87' },
  { name: 'XGBoost', precision: '98%', recall: '70%', f1: '0.82' },
  { name: 'Random Forest · SMOTE + tuning', precision: '92%', recall: '90%', f1: '0.91' },
]

export default function PaperResults() {
  return (
    <article className="panel paper-results" id="paper-results" aria-labelledby="paper-title">
      <div className="panel-heading">
        <div><span>Published research · PaySim benchmark</span><h2 id="paper-title">Random Forest, developed for rare fraud</h2></div>
        <a href="https://arxiv.org/abs/2604.07952v1" target="_blank" rel="noreferrer">Read paper ↗</a>
      </div>
      <p>
        Batsyas and Yaduwanshi, <cite>Fraud Detection System for Banking Transactions</cite>,
        9 April 2026. Results below come from the paper’s synthetic PaySim experiment;
        CardShield continues to use Kafka, Spark ML, Cassandra, FastAPI, and React.
        The research model has not been retrained or deployed into this pipeline.
      </p>
      <div className="model-metrics paper-metrics">
        <div className="primary"><span>Fraud recall</span><strong>90%</strong></div>
        <div className="primary"><span>Fraud precision</span><strong>92%</strong></div>
        <div><span>Fraud F1 score</span><strong>0.91</strong></div>
        <div><span>Accuracy · paper headline</span><strong>99.97%</strong></div>
      </div>
      <h3>Model development process</h3>
      <ol className="paper-process">
        <li><strong>Understand the data.</strong> Follow CRISP-DM: business understanding, data understanding, preparation, modeling, evaluation, and deployment. Explore transaction amount, transaction type, and recipient patterns. The paper reports 0.129% fraud, concentrated in TRANSFER and CASH-OUT.</li>
        <li><strong>Prepare six predictors.</strong> Retain type, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest, and newbalanceDest. Remove step, nameOrig, nameDest, and isFlaggedFraud; label-encode transaction type.</li>
        <li><strong>Reserve the test set.</strong> Use a stratified 90:10 split: 5,726,358 training rows and 636,262 test rows, including 821 fraud cases in the test set.</li>
        <li><strong>Compare four baselines.</strong> Evaluate Logistic Regression, Decision Tree, Random Forest, and XGBoost. Select Random Forest for its highest baseline fraud F1 of 0.87, using 15 trees and random seed 42.</li>
        <li><strong>Balance training data.</strong> Apply SMOTE only to the training set to reach a 1:1 class balance, expanding roughly 5.7 million rows to 11.4 million.</li>
        <li><strong>Tune and evaluate.</strong> Use GridSearchCV with stratified 3-fold cross-validation and F1 scoring over 16 configurations: 50/100 trees, depth None/10, minimum split 2, minimum leaf 1/2, sqrt features, and balanced class weights. Evaluate the selected model on the reserved test set.</li>
      </ol>
      <h3>Model comparison</h3>
      <p>Fraud-class results from Tables 1–5, rounded as published. These models share the paper’s test set; CardShield’s runtime evaluation uses a different dataset.</p>
      <div className="paper-table-scroll" role="region" aria-label="Research model comparison" tabIndex={0}>
        <table className="paper-table">
          <caption>PaySim test set · 636,262 transactions · 821 fraud cases</caption>
          <thead><tr><th scope="col">Model</th><th scope="col">Precision</th><th scope="col">Recall</th><th scope="col">F1</th></tr></thead>
          <tbody>{models.map((model, index) => (
            <tr key={model.name} className={index === models.length - 1 ? 'paper-best' : undefined}>
              <th scope="row">{model.name}</th><td>{model.precision}</td><td>{model.recall}</td><td>{model.f1}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p>Compared with baseline Random Forest, the tuned model increases recall by 11 percentage points and F1 by 0.04, while precision falls by 5 points. Decision Tree has the highest recall, at 97%, with lower precision of 74%.</p>
      <h3>Final confusion matrix</h3>
      <div className="paper-table-scroll" role="region" aria-label="Research confusion matrix" tabIndex={0}>
        <table className="paper-table">
          <caption>Table 5 · actual classes in rows, predicted classes in columns</caption>
          <thead><tr><th scope="col">Actual class</th><th scope="col">Predicted legitimate</th><th scope="col">Predicted fraud</th></tr></thead>
          <tbody>
            <tr><th scope="row">Legitimate</th><td>635,373 true negatives</td><td>68 false positives</td></tr>
            <tr><th scope="row">Fraud</th><td>83 false negatives</td><td>738 true positives</td></tr>
          </tbody>
        </table>
      </div>
      <details className="paper-notes">
        <summary>Source notes and evaluation limits</summary>
        <p>The paper’s headline accuracy is 99.97%; its final confusion matrix implies 99.9763% (99.98% rounded to two decimals). The comparison uses the classification tables: Logistic Regression recall is 0.43 (43%), although the prose says 0.43%. Dataset size and imbalance descriptions also vary; the train/test counts above follow Section 2.4.1.</p>
        <p>The paper reports XGBoost ROC AUC of 0.96, but does not report final tuned Random Forest PR AUC or ROC AUC. No values are inferred for those metrics. Its cross-validation follows SMOTE on the training set; validation-fold isolation during resampling is not documented.</p>
        <p>Millisecond API scoring is proposed in the paper’s conclusion, with no measured deployment latency. Drift monitoring, retraining, rule-based safeguards, temporal models, and SHAP/LIME explanations are proposed directions.</p>
      </details>
    </article>
  )
}
