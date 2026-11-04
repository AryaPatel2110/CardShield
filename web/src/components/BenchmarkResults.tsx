const models = [
  { name: 'Logistic Regression', precision: '85%', recall: '43%', f1: '0.57' },
  { name: 'Decision Tree', precision: '74%', recall: '97%', f1: '0.84' },
  { name: 'Random Forest · baseline', precision: '97%', recall: '79%', f1: '0.87' },
  { name: 'XGBoost', precision: '98%', recall: '70%', f1: '0.82' },
  { name: 'Random Forest · SMOTE + tuning', precision: '92%', recall: '90%', f1: '0.91' },
]

export default function BenchmarkResults() {
  return (
    <article className="panel benchmark-results" id="benchmark-results" aria-labelledby="benchmark-title">
      <div className="panel-heading">
        <div><span>PaySim model benchmark</span><h2 id="benchmark-title">Random Forest, developed for rare fraud</h2></div>
      </div>
      <p>
        Results below describe a synthetic PaySim benchmark. CardShield continues
        to use Kafka, Spark ML, Cassandra, FastAPI, and React.
      </p>
      <div className="model-metrics benchmark-metrics">
        <div className="primary"><span>Fraud recall</span><strong>90%</strong></div>
        <div className="primary"><span>Fraud precision</span><strong>92%</strong></div>
        <div><span>Fraud F1 score</span><strong>0.91</strong></div>
        <div><span>Accuracy · calculated</span><strong>99.98%</strong></div>
      </div>
      <h3>Model development process</h3>
      <ol className="benchmark-process">
        <li><strong>Understand the data.</strong> Follow CRISP-DM: business understanding, data understanding, preparation, modeling, evaluation, and deployment. Explore transaction amount, transaction type, and recipient patterns. The benchmark contains 0.129% fraud, concentrated in TRANSFER and CASH-OUT.</li>
        <li><strong>Prepare six predictors.</strong> Retain type, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest, and newbalanceDest. Remove step, nameOrig, nameDest, and isFlaggedFraud; label-encode transaction type.</li>
        <li><strong>Reserve the test set.</strong> Use a stratified 90:10 split: 5,726,358 training rows and 636,262 test rows, including 821 fraud cases in the test set.</li>
        <li><strong>Compare four baselines.</strong> Evaluate Logistic Regression, Decision Tree, Random Forest, and XGBoost. Select Random Forest for its highest baseline fraud F1 of 0.87, using 15 trees and random seed 42.</li>
        <li><strong>Balance training data.</strong> Apply SMOTE only to the training set to reach a 1:1 class balance, expanding roughly 5.7 million rows to 11.4 million.</li>
        <li><strong>Tune and evaluate.</strong> Use GridSearchCV with stratified 3-fold cross-validation and F1 scoring over 16 configurations: 50/100 trees, depth None/10, minimum split 2, minimum leaf 1/2, sqrt features, and balanced class weights. Evaluate the selected model on the reserved test set.</li>
      </ol>
      <h3>Model comparison</h3>
      <p>Rounded fraud-class results. These models share the same PaySim test set; CardShield’s runtime evaluation uses a different dataset.</p>
      <div className="benchmark-table-scroll" role="region" aria-label="Benchmark model comparison" tabIndex={0}>
        <table className="benchmark-table">
          <caption>PaySim test set · 636,262 transactions · 821 fraud cases</caption>
          <thead><tr><th scope="col">Model</th><th scope="col">Precision</th><th scope="col">Recall</th><th scope="col">F1</th></tr></thead>
          <tbody>{models.map((model, index) => (
            <tr key={model.name} className={index === models.length - 1 ? 'benchmark-best' : undefined}>
              <th scope="row">{model.name}</th><td>{model.precision}</td><td>{model.recall}</td><td>{model.f1}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p>Compared with baseline Random Forest, the tuned model increases recall by 11 percentage points and F1 by 0.04, while precision falls by 5 points. Decision Tree has the highest recall, at 97%, with lower precision of 74%.</p>
      <h3>Final confusion matrix</h3>
      <div className="benchmark-table-scroll" role="region" aria-label="Benchmark confusion matrix" tabIndex={0}>
        <table className="benchmark-table">
          <caption>Actual classes in rows, predicted classes in columns</caption>
          <thead><tr><th scope="col">Actual class</th><th scope="col">Predicted legitimate</th><th scope="col">Predicted fraud</th></tr></thead>
          <tbody>
            <tr><th scope="row">Legitimate</th><td>635,373 true negatives</td><td>68 false positives</td></tr>
            <tr><th scope="row">Fraud</th><td>83 false negatives</td><td>738 true positives</td></tr>
          </tbody>
        </table>
      </div>
      <details className="benchmark-notes">
        <summary>Evaluation notes and limits</summary>
        <p>Accuracy is calculated from the final confusion matrix: 99.9763%, rounded to 99.98%. Precision, recall, and F1 are rounded classification metrics.</p>
        <p>XGBoost ROC AUC is 0.96. Final tuned Random Forest PR AUC and ROC AUC are unavailable. Cross-validation follows SMOTE on the training set; validation-fold isolation during resampling is not documented.</p>
        <p>Deployment latency has not been measured for the benchmark model. Drift monitoring, retraining, rule-based safeguards, temporal models, and SHAP/LIME explanations remain future directions.</p>
      </details>
    </article>
  )
}
