import { type PointerEvent, type ReactNode, useEffect, useRef } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

function ShieldMark() {
  return (
    <span className="shield-mark" aria-hidden="true">
      <span />
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
        '.flow-card, .metric-card, .panel, .proof-strip, .final-cta',
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
          <NavLink to="/system">System</NavLink>
          <NavLink to="/simulate" className="nav-cta">Test transaction</NavLink>
        </nav>
      </header>
      <main id="main-content" key={location.pathname} className="page-transition">{children}</main>
      <footer>
        <div className="brand footer-brand"><ShieldMark /> CardShield</div>
        <p>Streaming intelligence for safer payments.</p>
        <span>Kafka · Spark · Cassandra</span>
      </footer>
    </div>
  )
}
