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

        <h1>
          Deploy your applications
          <br />
          <span>with confidence.</span>
        </h1>

        <p className="description">
          A Python-powered deployment tool using Docker, Amazon ECR,
          Amazon ECS, Terraform, and GitHub Actions.
        </p>

        <div className="buttons">
          <a href="#features" className="primary">
            Explore Features
          </a>
          <a href="#pipeline" className="secondary">
            View CI/CD Pipeline
          </a>
        </div>

        <section id="features" className="features">
          <article className="feature">
            <h3>Python CLI</h3>
            <p>Manage application deployments from the terminal.</p>
          </article>

          <article className="feature">
            <h3>Docker</h3>
            <p>Package the React application into a container image.</p>
          </article>

          <article className="feature">
            <h3>Amazon ECR</h3>
            <p>Store and manage Docker container images.</p>
          </article>

          <article className="feature">
            <h3>Amazon ECS</h3>
            <p>Run and manage the containerized application.</p>
          </article>

          <article className="feature">
            <h3>Terraform</h3>
            <p>Define and provision cloud infrastructure using code.</p>
          </article>

          <article className="feature">
            <h3>GitHub Actions</h3>
            <p>Automate the build and deployment workflow.</p>
          </article>
        </section>

        <section id="pipeline" className="pipeline">
          <h2>Deployment Pipeline</h2>
          <p>
            GitHub → GitHub Actions → Docker → Amazon ECR
            → Amazon ECS → Application Load Balancer
          </p>
        </section>
      </main>

      <footer>
        Built as a DevOps Capstone Project
      </footer>
    </div>
  )
}

export default App
