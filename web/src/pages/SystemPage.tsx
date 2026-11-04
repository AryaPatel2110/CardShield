import BenchmarkResults from '../components/BenchmarkResults'

export default function SystemPage() {
  return (
    <section className="system-page page-width" id="system" aria-labelledby="system-title">
      <div className="system-heading">
        <div className="eyebrow"><i /> Model development</div>
        <h2 id="system-title">Inside the shield</h2>
        <p>Explore model development, evaluation, and the PaySim model comparison.</p>
      </div>

      <BenchmarkResults />
    </section>
  )
}
