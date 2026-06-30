# Recruiter demo runbook

## Before the call

```bash
make demo-check
docker compose --profile demo up --build
```

Wait for the website and API health checks, then open
<http://localhost:3000>. Keep the `/system`, `/simulate`, and `/dashboard`
pages open in separate tabs. Confirm that the routine and high-risk presets
produce the expected model decisions.

The dashboard displays clearly labeled preview data if Cassandra becomes
unavailable. That mode is presentation insurance, not evidence that the live
pipeline is healthy.

## Three-minute story

1. **Problem — 20 seconds.** On the landing page, explain that fraud decisions
   need both low-latency scoring and an operational audit trail.
2. **Architecture — 35 seconds.** Open `/system`. Follow React → FastAPI →
   Kafka → Spark ML → Cassandra. Point to versioned events, the dead-letter
   topic, checkpoints, and idempotent writes.
3. **Live transaction — 60 seconds.** Open `/simulate`, select **High-risk
   pattern**, keep **Live pipeline** selected, and analyze it. Let the audience
   see each real stage complete and call out the measured end-to-end latency.
4. **Operational payoff — 35 seconds.** Select **View on live dashboard**.
   Show the highlighted row and open its audit drawer.
5. **Engineering judgment — 30 seconds.** Return to `/system`. Lead with fraud
   recall, precision, and PR-AUC. State that accuracy is misleading for this
   imbalanced dataset and name the threshold and fairness gates still required
   before production.

## Do not claim

- The Compose environment is not a production payment deployment.
- A low-risk decision is not a guarantee that a transaction is legitimate.
- Derived decision-context indicators are not Random Forest feature
  attribution.
- Preview dashboard data is not live data.
