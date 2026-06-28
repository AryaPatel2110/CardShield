CREATE KEYSPACE IF NOT EXISTS bigdata
WITH replication = {
    'class': 'NetworkTopologyStrategy',
    'replication_factor': 1
};

CREATE TABLE IF NOT EXISTS bigdata.transactions_by_day (
    transaction_day date,
    shard tinyint,
    inserted_at timestamp,
    trans_num text,
    merchant text,
    category text,
    amt decimal,
    is_fraud int,
    is_fraud_prediction int,
    fraud_probability double,
    model_version text,
    PRIMARY KEY ((transaction_day, shard), inserted_at, trans_num)
) WITH CLUSTERING ORDER BY (inserted_at DESC, trans_num ASC);

CREATE TABLE IF NOT EXISTS bigdata.fraud_alerts_by_day (
    alert_day date,
    shard tinyint,
    inserted_at timestamp,
    trans_num text,
    merchant text,
    category text,
    amt decimal,
    fraud_probability double,
    model_version text,
    PRIMARY KEY ((alert_day, shard), inserted_at, trans_num)
) WITH CLUSTERING ORDER BY (inserted_at DESC, trans_num ASC);

