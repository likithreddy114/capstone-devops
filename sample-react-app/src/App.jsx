
import './App.css'

function App() {
  return (
    <div className="app">
      <header className="navbar">
        <h2>DeployTool</h2>
        <span>DevOps Capstone Project</span>
      </header>

      <main className="hero">
        <p className="tag">AUTOMATED CLOUD DEPLOYMENT</p>

        <h1>Deploy your applications<br />
          <span>with confidence.</span>
        </h1>

        <p className="description">
          A Python-powered deployment tool using AWS S3,
          CloudFront, Terraform, and React.
        </p>

        <div className="buttons">
          <a href="#features" className="primary">
            Explore Features
          </a>
          <a
            href="https://aws.amazon.com/cloudfront/"
            className="secondary"
            target="_blank"
            rel="noreferrer"
          >
            About CloudFront
          </a>
        </div>

        <section id="features" className="features">
          <article className="feature">
            <h3>Python CLI</h3>
            <p>Configure and manage deployments from the terminal.</p>
          </article>

          <article className="feature">
            <h3>AWS S3</h3>
            <p>Store and host your production-ready frontend files.</p>
          </article>

          <article className="feature">
            <h3>CloudFront CDN</h3>
            <p>Deliver website content securely and efficiently.</p>
          </article>

          <article className="feature">
            <h3>Terraform</h3>
            <p>Provision cloud infrastructure using code.</p>
          </article>
        </section>
      </main>

      <footer>
        Built as a DevOps Capstone Project
      </footer>
    </div>
  )
}

export default App
