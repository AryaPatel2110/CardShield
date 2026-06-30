import {
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useRef,
  useState,
} from 'react'
import { Link } from 'react-router-dom'
import SystemPage from './SystemPage'

const clamp = (value: number) => Math.min(Math.max(value, 0), 1)

const capabilities = [
  {
    id: 'case',
    label: 'Decision explained',
    title: 'Why was this payment flagged?',
    body: 'Replay one decision from its transaction context to the final score, selected threshold, stored verdict, and operator facing record.',
  },
  {
    id: 'stream',
    label: 'Streaming reliability',
    title: 'Keep scoring when individual events fail',
    body: 'Versioned contracts isolate malformed payloads, while independent checkpoints preserve progress for scoring and dead letter routes.',
  },
  {
    id: 'operations',
    label: 'Operational clarity',
    title: 'Turn a model result into an auditable decision',
    body: 'Every stored result carries its probability, model version, transaction identity, and a short lived trace through the live pipeline.',
  },
] as const

type CapabilityId = typeof capabilities[number]['id']

const livePipelineNodes = [
  { name: 'API Replay', detail: 'POST api pipeline', icon: 'api' },
  { name: 'Kafka', detail: 'transactions.v1', icon: 'kafka' },
  { name: 'Spark Streaming', detail: 'parse and contract check', icon: 'spark' },
  { name: 'ML Model', detail: 'score and decision', icon: 'model' },
  { name: 'Cassandra', detail: 'transactions by day', icon: 'database' },
  { name: 'FastAPI', detail: 'aggregate recent window', icon: 'server' },
  { name: 'React Dashboard', detail: 'decision and audit drawer', icon: 'screen' },
] as const

const livePipelineFrames = [
  { code: 'Overview', detail: 'One transaction moves through the complete CardShield decision path.' },
  { code: 'API accepted', detail: 'The payment is validated against the versioned event contract.' },
  { code: 'Kafka published', detail: 'The validated event enters transactions.v1 with a stable partition key.' },
  { code: 'Contract checked', detail: 'Spark parses the event while malformed payloads route to the dead letter topic.' },
  { code: 'Model scored', detail: 'The saved Spark ML pipeline resolves probability, decision, and model version.' },
  { code: 'Result persisted', detail: 'Cassandra stores the decision and writes flagged fraud to the alert table.' },
  { code: 'Window assembled', detail: 'FastAPI reads recent partitions and assembles the operator response.' },
  { code: 'Decision visible', detail: 'React presents the result with its trace and measured latency.' },
] as const

export default function LandingPage() {
  const heroRef = useRef<HTMLElement>(null)
  const ctaButtonRef = useRef<HTMLAnchorElement>(null)
  const [activeCapability, setActiveCapability] = useState<CapabilityId>('case')

  useEffect(() => {
    let animationFrame = 0
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

    const updateScroll = () => {
      animationFrame = 0
      const hero = heroRef.current
      if (!hero) return

      if (reducedMotion.matches) {
        hero.style.setProperty('--hero-progress', '0')
        return
      }

      const heroRect = hero.getBoundingClientRect()
      const heroProgress = clamp(-heroRect.top / Math.max(heroRect.height * 0.72, 1))
      hero.style.setProperty('--hero-progress', heroProgress.toFixed(4))
      hero.style.setProperty('--hero-copy-y', `${heroProgress * -72}px`)
      hero.style.setProperty('--hero-copy-opacity', `${1 - heroProgress * 0.86}`)
      hero.style.setProperty('--hero-visual-y', `${heroProgress * 44}px`)
      hero.style.setProperty('--hero-visual-scale', `${1 - heroProgress * 0.09}`)
      hero.style.setProperty('--hero-visual-opacity', `${1 - heroProgress * 0.68}`)

    }

    const requestUpdate = () => {
      if (!animationFrame) animationFrame = window.requestAnimationFrame(updateScroll)
    }

    updateScroll()
    window.addEventListener('scroll', requestUpdate, { passive: true })
    window.addEventListener('resize', requestUpdate)
    reducedMotion.addEventListener('change', requestUpdate)

    return () => {
      window.cancelAnimationFrame(animationFrame)
      window.removeEventListener('scroll', requestUpdate)
      window.removeEventListener('resize', requestUpdate)
      reducedMotion.removeEventListener('change', requestUpdate)
    }
  }, [])

  const moveMagneticButton = (event: ReactPointerEvent<HTMLAnchorElement>) => {
    const button = ctaButtonRef.current
    if (!button) return
    const bounds = button.getBoundingClientRect()
    const x = (event.clientX - bounds.left - bounds.width / 2) * 0.13
    const y = (event.clientY - bounds.top - bounds.height / 2) * 0.18
    button.style.transform = `translate(${x}px, ${y}px)`
  }

  const resetMagneticButton = () => {
    if (ctaButtonRef.current) ctaButtonRef.current.style.transform = ''
  }

  const activeCapabilityContent = capabilities.find(
    (capability) => capability.id === activeCapability,
  ) ?? capabilities[0]

  return (
    <div className="landing-page">
      <section className="hero sardine-hero page-width" ref={heroRef}>
        <div className="hero-copy">
          <div className="hero-kicker"><span /> Live payment intelligence</div>
          <h1>Catch fraud faster.<br /><em>Explain every decision.</em></h1>
          <p>
            CardShield turns each payment into an auditable risk decision through
            one visible system built with Kafka, Spark ML, Cassandra, FastAPI, and React.
          </p>
          <div className="hero-actions">
            <Link to="/simulate" className="button button-primary">
              Test a transaction <span className="button-direction" aria-hidden="true" />
            </Link>
            <a href="#decision-flow" className="button button-quiet">
              See how it works
            </a>
          </div>
        </div>

        <HeroCheckoutPreview />
      </section>

      <section className="technology-rail" aria-label="CardShield technology">
        <div className="technology-track">
          <span>PYTHON</span><i />
          <span>KAFKA</span><i />
          <span>SPARK ML</span><i />
          <span>CASSANDRA</span><i />
          <span>FASTAPI</span><i />
          <span>REACT</span><i />
          <span>PYTHON</span><i />
          <span>KAFKA</span><i />
          <span>SPARK ML</span><i />
          <span>CASSANDRA</span><i />
          <span>FASTAPI</span><i />
          <span>REACT</span>
        </div>
      </section>

      <section className="pipeline-scroll" id="decision-flow" aria-labelledby="pipeline-title">
        <div className="pipeline-sticky">
          <div className="pipeline-shell page-width">
            <div className="pipeline-heading">
              <div>
                <div className="eyebrow"><i /> Inside the decision path</div>
                <h2 id="pipeline-title">From swipe to signal</h2>
              </div>
              <p>
                Watch live scenarios move continuously through the same versioned
                flow documented in the project README.
              </p>
            </div>

            <div className="workflow-embed">
              <iframe
                src="/cardshield_workflow.html"
                title="CardShield continuously animated decision workflow"
                loading="lazy"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="capability-section page-width" aria-labelledby="capability-title">
        <div className="capability-heading">
          <div className="eyebrow"><i /> Built as one system</div>
          <h2 id="capability-title">Go beyond a model prediction</h2>
          <p>
            Explore the engineering choices that turn offline evaluation into a
            live, inspectable fraud decision.
          </p>
        </div>
        <div className="capability-layout">
          <div className="capability-tabs" role="tablist" aria-label="Project capabilities">
            {capabilities.map((capability, index) => (
              <button
                type="button"
                role="tab"
                aria-selected={activeCapability === capability.id}
                className={activeCapability === capability.id ? 'active' : ''}
                onClick={() => setActiveCapability(capability.id)}
                key={capability.id}
              >
                <span>0{index + 1}</span>
                <strong>{capability.label}</strong>
              </button>
            ))}
          </div>
          <div className={`capability-story ${activeCapability === 'stream' ? 'streaming-story' : ''}`}>
            <div>
              <span>{activeCapabilityContent.label}</span>
              <h3>{activeCapabilityContent.title}</h3>
              <p>{activeCapabilityContent.body}</p>
              <a href="#system">
                See the engineering evidence <span className="button-direction" aria-hidden="true" />
              </a>
            </div>
            <CapabilityDisplay key={activeCapability} capability={activeCapability} />
          </div>
        </div>
      </section>

      <SystemPage />

      <MerchantBenefits />

      <section className="final-cta page-width">
        <div className="cta-radar" aria-hidden="true"><i /></div>
        <div>
          <div className="eyebrow"><i /> See the system respond</div>
          <h2>Put a transaction<br />through the shield.</h2>
          <p>Choose a held out scenario or enter your own payment details.</p>
        </div>
        <Link
          ref={ctaButtonRef}
          to="/simulate"
          className="button button-dark magnetic-cta"
          onPointerMove={moveMagneticButton}
          onPointerLeave={resetMagneticButton}
        >
          Open simulator <span className="button-direction" aria-hidden="true" />
        </Link>
      </section>
    </div>
  )
}

function MerchantBenefits() {
  return (
    <section className="merchant-benefits page-width" aria-labelledby="merchant-benefits-title">
      <div className="merchant-benefits-heading">
        <div>
          <div className="eyebrow"><i /> Merchant outcomes</div>
          <h2 id="merchant-benefits-title">Better fraud operations for every payment.</h2>
        </div>
        <div className="merchant-benefit-stats">
          <div><strong>66.5%</strong><span>Fraud recall in held out evaluation</span></div>
          <div><strong>4</strong><span>Auditable decision checkpoints</span></div>
        </div>
      </div>

      <div className="merchant-benefit-grid">
        <article>
          <span>01</span>
          <h3>Protect more good payments</h3>
          <p>Apply one calibrated review threshold consistently and keep lower risk payments clear of unnecessary investigation.</p>
          <div className="merchant-card-visual approval-visual" aria-hidden="true">
            <div className="merchant-visual-node">
              <i />
              <span><strong>Payment risk</strong><small>Score resolved</small></span>
              <b>0.04</b>
            </div>
            <div className="merchant-route-line"><i /></div>
            <strong className="merchant-verdict approved">Approved</strong>
          </div>
        </article>

        <article>
          <span>02</span>
          <h3>Catch fraud before losses grow</h3>
          <p>Surface high risk decisions as soon as the model score crosses the selected operating threshold.</p>
          <div className="merchant-card-visual prevention-visual" aria-hidden="true">
            <div className="merchant-score-head"><span>Fraud probability</span><strong>0.87</strong></div>
            <div className="merchant-score-track"><i /><b /></div>
            <div className="merchant-transaction-row"><span>TXN 6de094e9</span><strong>Flagged</strong></div>
            <div className="merchant-transaction-row"><span>TXN 29ba841c</span><strong className="safe">Approved</strong></div>
          </div>
        </article>

        <article>
          <span>03</span>
          <h3>Make investigations faster</h3>
          <p>Give operators the transaction context, probability, model version, and complete pipeline trace in one record.</p>
          <div className="merchant-card-visual audit-visual" aria-hidden="true">
            <div className="merchant-audit-title"><span>Decision trace</span><strong>Complete</strong></div>
            <ol>
              <li><i />API accepted<small>12 ms</small></li>
              <li><i />Kafka published<small>31 ms</small></li>
              <li><i />Model scored<small>84 ms</small></li>
              <li><i />Decision persisted<small>109 ms</small></li>
            </ol>
          </div>
        </article>
      </div>
    </section>
  )
}

function HeroCheckoutPreview() {
  return (
    <div
      className="hero-checkout-preview"
      role="img"
      aria-label="A CardShield checkout sending a payment through live fraud scoring"
    >
      <div className="hero-flow-lines" aria-hidden="true">
        <i /><i /><i />
        <b /><b /><b />
      </div>

      <div className="hero-checkout-window">
        <div className="hero-checkout-brand">
          <span className="hero-brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>
          <strong>CardShield checkout</strong>
        </div>

        <div className="hero-checkout-content">
          <div className="hero-payment-panel">
            <span className="hero-field-label">Pay with</span>
            <div className="hero-payment-methods">
              <div className="active"><i className="method-card" /><strong>Card</strong></div>
              <div><i className="method-bank" /><strong>Bank</strong></div>
              <div><i className="method-transfer" /><strong>Transfer</strong></div>
            </div>

            <span className="hero-field-label">Card details</span>
            <div className="hero-card-number">
              <span>•••• •••• •••• 4587</span>
              <strong>VISA</strong>
            </div>
            <div className="hero-card-fields">
              <span>Expiry date</span>
              <span>CVV</span>
            </div>
            <div className="hero-save-card"><i /> Save card details</div>
            <div className="hero-pay-button">
              <span>Pay USD 209.97</span>
              <i aria-hidden="true" />
            </div>
            <div className="hero-powered">
              <span>Powered by</span>
              <i aria-hidden="true" />
              <strong>CardShield</strong>
            </div>
          </div>

          <div className="hero-order-panel">
            <div className="hero-product">
              <i aria-hidden="true"><span /></i>
              <div>
                <strong>Protected electronics order</strong>
                <span>$199.49, Qty 1</span>
              </div>
            </div>
            <div className="hero-order-rule" />
            <div className="hero-discount"><span>Discount code</span><strong>Apply</strong></div>
            <dl>
              <div><dt>Subtotal</dt><dd>$199.49</dd></div>
              <div><dt>Shipping</dt><dd>$8.24</dd></div>
              <div className="total"><dt>Total<small>Including $2.24 tax</small></dt><dd>$209.97</dd></div>
            </dl>
          </div>
        </div>
      </div>

      <div className="hero-risk-chip">
        <i aria-hidden="true" />
        <span><strong>CardShield</strong><small>Live risk score</small></span>
        <b>0.04</b>
        <em>Low</em>
      </div>

      <div className="hero-insight-card">
        <div className="hero-insight-metrics">
          <span><small>Total chargebacks</small><strong>114</strong></span>
          <span><small>Chargeback rate</small><strong>0.07%</strong></span>
          <em>0.14%</em>
        </div>
        <svg viewBox="0 0 420 116" aria-hidden="true">
          <defs>
            <linearGradient id="heroChartFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#43b985" stopOpacity=".22" />
              <stop offset="1" stopColor="#43b985" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path className="hero-chart-grid" d="M0 20H420M0 58H420M0 96H420" />
          <path className="hero-chart-area" d="M0 48 C55 42 78 38 120 50 S205 82 256 72 S314 49 360 65 S400 82 420 87 V116 H0 Z" />
          <path className="hero-chart-line" d="M0 48 C55 42 78 38 120 50 S205 82 256 72 S314 49 360 65 S400 82 420 87" />
          <circle cx="256" cy="72" r="5" />
        </svg>
        <div className="hero-chart-labels"><span>April</span><span>May</span><span>June</span><span>July</span><span>August</span></div>
      </div>
    </div>
  )
}

function CapabilityDisplay({ capability }: { capability: CapabilityId }) {
  if (capability === 'stream') {
    return <LivePipelineAnimation />
  }

  if (capability === 'operations') {
    return (
      <div className="capability-display operations-display">
        <div className="display-topbar"><span>Recent decisions</span><small>Live view</small></div>
        <div className="operations-summary">
          <span><small>Analyzed</small><strong>248</strong></span>
          <span><small>Flagged</small><strong>7</strong></span>
          <span><small>At risk</small><strong>$4,821</strong></span>
        </div>
        <div className="operations-table">
          <div><span>Schmitt Inc</span><b>94.7%</b><strong>Flagged</strong></div>
          <div><span>Hills Witting</span><b>3.1%</b><strong>Approved</strong></div>
          <div><span>Pacocha Bauch</span><b>88.2%</b><strong>Flagged</strong></div>
        </div>
      </div>
    )
  }

  return <DecisionCaseDisplay />
}

function DecisionCaseDisplay() {
  return (
    <div className="capability-display decision-case-display">
      <div className="display-topbar">
        <span>Decision replay</span>
        <small>TXN 6de094e9</small>
      </div>

      <div className="decision-case-payment">
        <div>
          <span>Protected electronics order</span>
          <strong>$149.95</strong>
        </div>
        <small>shopping net</small>
      </div>

      <div className="decision-signal-list" aria-label="Recorded transaction context">
        <div className="signal-distance">
          <span><strong>Merchant distance</strong><small>711 miles from customer</small></span>
          <b>High</b><i><em /></i>
        </div>
        <div className="signal-category">
          <span><strong>Purchase category</strong><small>Online electronics</small></span>
          <b>Elevated</b><i><em /></i>
        </div>
        <div className="signal-amount">
          <span><strong>Transaction amount</strong><small>Payment value recorded</small></span>
          <b>$149.95</b><i><em /></i>
        </div>
      </div>

      <div className="decision-case-score">
        <div>
          <span>Fraud probability</span>
          <strong>0.87</strong>
        </div>
        <div className="decision-score-track">
          <i />
          <b><span>Threshold</span>0.625</b>
        </div>
        <div className="decision-verdict">
          <span><i />Decision persisted</span>
          <strong>Flagged for review</strong>
        </div>
      </div>
    </div>
  )
}

function LivePipelineAnimation() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setStep(livePipelineFrames.length - 1)
      return
    }

    const timer = window.setInterval(
      () => setStep((current) => (current + 1) % livePipelineFrames.length),
      1550,
    )
    return () => window.clearInterval(timer)
  }, [])

  const activeNode = step === 0 ? -1 : step - 1
  const frame = livePipelineFrames[step]
  const stateFor = (index: number) => {
    if (index < activeNode) return 'completed'
    if (index === activeNode) return 'active'
    return 'pending'
  }

  return (
    <div className={`live-pipeline-animation live-pipeline-step-${step}`}>
      <div className="live-pipeline-header">
        <div className="live-pipeline-brand">
          <i aria-hidden="true"><span /></i>
          <span><strong>CardShield</strong><small>Live decision pipeline</small></span>
        </div>
        <div className="live-pipeline-step">
          <strong>{step === 0 ? 'Overview' : `Step ${step} / 7`}</strong>
          <small>Sparkov schema v1</small>
        </div>
      </div>

      <div className="live-pipeline-stage">
        <div className="live-pipeline-stage-inner">
          <div className="live-transaction">
            <i />
            TXN 6de094e9
            <span>$149.95</span>
            {step >= 4 && <b>p=0.87 fraud</b>}
          </div>

          <div className="live-pipeline-node-row">
            {livePipelineNodes.map((node, index) => (
              <div
                className={`live-pipeline-node-wrap ${index < activeNode ? 'connected' : ''}`}
                key={node.name}
              >
                <div className={`live-pipeline-node ${stateFor(index)}`}>
                  <LivePipelineIcon type={node.icon} />
                  <strong>{node.name}</strong>
                  <small>{node.detail}</small>
                  <i className="live-pipeline-node-state" />
                </div>
              </div>
            ))}
          </div>

          <div className={`live-pipeline-branch live-pipeline-dlq ${step === 3 ? 'active' : ''}`}>
            <strong>transactions.dlq.v1</strong>
            <small>malformed events isolated</small>
          </div>
          <div className={`live-pipeline-branch live-pipeline-alert ${step === 5 ? 'active' : ''}`}>
            <strong>fraud alerts by day</strong>
            <small>written when fraud is flagged</small>
          </div>
        </div>
      </div>

      <div className="live-pipeline-copy" aria-live="polite">
        <strong>{frame.code}</strong>
        <p>{frame.detail}</p>
      </div>

      <div className="live-pipeline-trace">
        <span>Pipeline trace</span>
        <div>
          {[1, 2, 4, 5].map((requiredStep) => (
            <i
              className={step > requiredStep ? 'completed' : step === requiredStep ? 'active' : ''}
              key={requiredStep}
            ><b /></i>
          ))}
        </div>
        <ol>
          <li>API accepted</li>
          <li>Kafka published</li>
          <li>Model scored</li>
          <li>Cassandra persisted</li>
        </ol>
      </div>

      <div className="live-pipeline-legend">
        <span><i className="active" />Active</span>
        <span><i className="completed" />Completed</span>
        <span><i />Pending</span>
        <span><i className="dlq" />Dead letter</span>
        <span><i className="alert" />Fraud alert</span>
      </div>
    </div>
  )
}

function LivePipelineIcon({ type }: { type: typeof livePipelineNodes[number]['icon'] }) {
  if (type === 'api') return <svg viewBox="0 0 24 24"><path d="M12 3v11m0 0-4-4m4 4 4-4M5 17v3h14v-3" /></svg>
  if (type === 'kafka') return <svg viewBox="0 0 24 24"><path d="M5 9v6m5-9v12m5-8v4m4-7v10" /></svg>
  if (type === 'spark') return <svg viewBox="0 0 24 24"><path d="m14 2-8 12h6l-2 8 8-12h-6z" /></svg>
  if (type === 'model') return <svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="2" /><circle cx="5" cy="18" r="2" /><circle cx="19" cy="18" r="2" /><path d="m11 7-5 9m7-9 5 9M7 18h10" /></svg>
  if (type === 'database') return <svg viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="7" ry="3" /><path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7" /></svg>
  if (type === 'server') return <svg viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="7" rx="2" /><rect x="4" y="14" width="16" height="7" rx="2" /><path d="M8 6.5h.1M8 17.5h.1M12 6.5h5M12 17.5h5" /></svg>
  return <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="13" rx="2" /><path d="M8 21h8m-4-4v4" /></svg>
}
