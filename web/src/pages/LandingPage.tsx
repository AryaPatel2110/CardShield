import { Link } from 'react-router-dom'

const flow = [
  ['01', 'Ingest', 'Kafka receives a continuous stream of transaction events.'],
  ['02', 'Score', 'Spark applies the trained fraud pipeline in near real time.'],
  ['03', 'Respond', 'High-risk activity is persisted and surfaced immediately.'],
]

export default function LandingPage() {
  return (
    <>
      <section className="hero page-width">
        <div className="hero-copy">
          <div className="eyebrow"><i /> Real-time fraud intelligence</div>
          <h1>Every payment.<br /><em>Protected.</em></h1>
          <p>
            CardShield turns live transaction data into immediate fraud decisions,
            helping teams act before suspicious activity becomes a loss.
          </p>
          <div className="hero-actions">
            <Link to="/simulate" className="button button-primary">
              Test a transaction <span>→</span>
            </Link>
            <Link to="/dashboard" className="button button-quiet">
              View live dashboard
            </Link>
          </div>
          <div className="trust-row">
            <span><b>11</b> risk signals</span>
            <span><b>24/7</b> monitoring</span>
            <span><b>Live</b> model scoring</span>
          </div>
        </div>
        <div className="hero-visual" aria-label="Live fraud detection preview">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="signal-card signal-main">
            <div className="signal-heading">
              <span className="pulse-dot" />
              Live risk engine
              <small>ONLINE</small>
            </div>
            <div className="score-ring">
              <div><strong>08</strong><span>risk score</span></div>
            </div>
            <div className="signal-status">
              <span>Transaction approved</span>
              <b>Low risk</b>
            </div>
          </div>
          <div className="floating-card floating-top">
            <span className="mini-icon">⌁</span>
            <div><small>Signals analyzed</small><strong>11 / 11</strong></div>
          </div>
          <div className="floating-card floating-bottom">
            <span className="mini-icon alert-icon">!</span>
            <div><small>Threat response</small><strong>Real time</strong></div>
          </div>
        </div>
      </section>

      <section className="proof-strip">
        <div className="page-width">
          <p>Built for the velocity of modern payments</p>
          <div className="proof-metrics">
            <div><strong>Kafka</strong><span>Event ingestion</span></div>
            <div><strong>Spark ML</strong><span>Fraud scoring</span></div>
            <div><strong>Cassandra</strong><span>Operational store</span></div>
            <div><strong>React</strong><span>Decision console</span></div>
          </div>
        </div>
      </section>

      <section className="flow-section page-width">
        <div className="section-heading">
          <div className="eyebrow"><i /> Under the hood</div>
          <h2>From swipe to signal<br />in one clean flow.</h2>
          <p>The production pipeline is designed around fast, explainable decisions.</p>
        </div>
        <div className="flow-grid">
          {flow.map(([number, title, body]) => (
            <article className="flow-card" key={number}>
              <span>{number}</span>
              <div className={`flow-glyph glyph-${number}`}>{number === '01' ? '↳' : number === '02' ? '⌁' : '✓'}</div>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="final-cta page-width">
        <div>
          <div className="eyebrow"><i /> See it in action</div>
          <h2>Put a transaction<br />through the shield.</h2>
        </div>
        <Link to="/simulate" className="button button-dark">
          Open simulator <span>→</span>
        </Link>
      </section>
    </>
  )
}
