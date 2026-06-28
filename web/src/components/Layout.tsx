import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

function ShieldMark() {
  return (
    <span className="shield-mark" aria-hidden="true">
      <span />
    </span>
  )
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
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
      <main>{children}</main>
      <footer>
        <div className="brand footer-brand"><ShieldMark /> CardShield</div>
        <p>Streaming intelligence for safer payments.</p>
        <span>Kafka · Spark · Cassandra</span>
      </footer>
    </div>
  )
}
