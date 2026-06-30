import { type PointerEvent, type ReactNode, useEffect, useId, useRef } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

function ShieldMark() {
  const gradientId = useId()

  return (
    <span className="shield-mark" aria-hidden="true">
      <svg viewBox="0 0 40 44" role="presentation">
        <defs>
          <linearGradient id={gradientId} x1="5" y1="3" x2="35" y2="40">
            <stop offset="0" stopColor="#7bddad" />
            <stop offset="1" stopColor="#35b77c" />
          </linearGradient>
        </defs>
        <path
          className="shield-mark-body"
          fill={`url(#${gradientId})`}
          d="M20 2 36 8v13.8c0 9.7-5.8 16.1-16 20.2C9.8 37.9 4 31.5 4 21.8V8l16-6Z"
        />
        <path
          className="shield-mark-chevron-back"
          d="m10.8 29.7 9.2-9.2 9.2 9.2"
        />
        <path
          className="shield-mark-chevron-front"
          d="m10.8 24.1 9.2-9.2 9.2 9.2"
        />
      </svg>
    </span>
  )
}

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const shellRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let observer: IntersectionObserver | undefined
    const frame = window.requestAnimationFrame(() => {
      const elements = document.querySelectorAll(
        '.flow-card, .metric-card, .panel, .proof-strip, .capability-heading, .capability-layout, .system-heading, .merchant-benefits-heading, .merchant-benefit-grid article, .final-cta, footer > span',
      )
      const nextObserver = new IntersectionObserver(
        (entries) => entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('motion-visible')
            nextObserver.unobserve(entry.target)
          }
        }),
        { threshold: 0.12 },
      )
      observer = nextObserver
      elements.forEach((element) => {
        element.classList.add('motion-reveal')
        nextObserver.observe(element)
      })
      shellRef.current?.setAttribute('data-observer-ready', 'true')
    })
    return () => {
      window.cancelAnimationFrame(frame)
      observer?.disconnect()
    }
  }, [location.pathname])

  const trackPointer = (event: PointerEvent<HTMLDivElement>) => {
    shellRef.current?.style.setProperty('--pointer-x', `${event.clientX}px`)
    shellRef.current?.style.setProperty('--pointer-y', `${event.clientY}px`)
  }

  return (
    <div className="app-shell" ref={shellRef} onPointerMove={trackPointer}>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <NavLink to="/" className="brand" aria-label="CardShield home">
          <ShieldMark />
          <span>Card<span>Shield</span></span>
        </NavLink>
        <nav aria-label="Main navigation">
          <NavLink to="/">Home</NavLink>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/simulate" className="nav-cta">Test transaction</NavLink>
        </nav>
      </header>
      <main id="main-content" key={location.pathname} className="page-transition">{children}</main>
      <footer>
        <div className="brand footer-brand"><ShieldMark /> CardShield</div>
        <p>Streaming intelligence for safer payments.</p>
        <span>Kafka&nbsp;&nbsp; Spark&nbsp;&nbsp; Cassandra</span>
      </footer>
    </div>
  )
}
