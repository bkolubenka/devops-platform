import { useEffect, useState } from "react";

import { BuildFooter } from "../components/BuildFooter";
import { SharedNav } from "../components/SharedNav";
import { api } from "../lib/api";
import type { BuildMetadata } from "../types";

export function ResumePage() {
  const [build, setBuild] = useState<BuildMetadata | null>(null);
  const [buildError, setBuildError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadBuild() {
      try {
        const overview = await api.getOverview();
        if (!active) {
          return;
        }
        setBuild(overview.build);
        setBuildError(null);
      } catch (error) {
        if (!active) {
          return;
        }
        setBuildError(error instanceof Error ? error.message : "Unknown build metadata error");
      }
    }

    void loadBuild();

    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <SharedNav />
      <div className="page-shell">
        <main>
          <p className="eyebrow">Professional Profile</p>
          <h1>Resume</h1>
          <p>
            Senior DevOps Engineer and Technical Lead with extensive experience in cloud
            infrastructure, CI/CD, and enterprise systems.
          </p>

          <div className="portfolio-intro">
            <section className="panel">
              <p className="eyebrow">Professional Summary</p>
              <h2>Senior DevOps / Platform Engineer</h2>
              <p>
                Senior DevOps Engineer and Technical Lead with 14 years of experience across
                cloud infrastructure, CI/CD, enterprise systems, and production support. Strong
                background in Azure, automation, reliability, and cross-functional delivery for
                business-critical platforms in large-scale Oil &amp; Gas environments.
              </p>
            </section>

            <div className="resume-grid">
              <section className="panel">
                <p className="eyebrow">Career Highlights</p>
                <h2>Experience Snapshot</h2>
                <div className="highlight-list">
                  {[
                    {
                      title:
                        "14 years across DevOps, architecture, infrastructure, and enterprise systems",
                      description:
                        "Career span covering platform engineering, production support, automation, GIS, and system leadership.",
                    },
                    {
                      title: "System Architect / Technical Lead at Tengizchevroil (Chevron)",
                      description:
                        "Owned delivery, modernization, and operational readiness for enterprise-scale Azure-based systems.",
                    },
                    {
                      title: "Owned CI/CD, deployment automation, and production support in Azure",
                      description:
                        "Built and improved pipelines, environment governance, testing integration, and release reliability.",
                    },
                    {
                      title:
                        "Improved critical data-intensive queries from 7+ minutes to under 1 second",
                      description:
                        "Applied architecture and database-level optimization for 100M+ record enterprise datasets.",
                    },
                    {
                      title: "Introduced Playwright automation into delivery pipelines",
                      description:
                        "Integrated UI test coverage into PR and post-deploy flows to catch regressions earlier.",
                    },
                    {
                      title:
                        "Hands-on with Azure, Kubernetes, Terraform, Ansible, Docker, and CI/CD",
                      description:
                        "Comfortable across cloud, platform automation, infrastructure as code, and operational ownership.",
                    },
                  ].map((item) => (
                    <div className="highlight-item" key={item.title}>
                      <span className="highlight-mark" />
                      <div className="highlight-copy">
                        <strong>{item.title}</strong>
                        <span>{item.description}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="panel">
                <p className="eyebrow">Contact</p>
                <h2>Let&apos;s Connect</h2>
                <p>Professional links and contact information.</p>
                <div className="contact-list">
                  <div className="contact-item">
                    <div className="contact-copy">
                      <strong>GitHub</strong>
                      <span>
                        <a
                          href="https://github.com/bkolubenka/devops-platform"
                          target="_blank"
                          rel="noreferrer"
                        >
                          github.com/bkolubenka/devops-platform
                        </a>
                      </span>
                    </div>
                  </div>
                  <div className="contact-item">
                    <div className="contact-copy">
                      <strong>LinkedIn</strong>
                      <span>
                        <a href="https://www.linkedin.com/in/kydyrov/" target="_blank" rel="noreferrer">
                          linkedin.com/in/kydyrov
                        </a>
                      </span>
                    </div>
                  </div>
                  <div className="contact-item">
                    <div className="contact-copy">
                      <strong>Email</strong>
                      <span>
                        <a href="mailto:meirambek@kydyrov.dev">meirambek@kydyrov.dev</a>
                      </span>
                    </div>
                  </div>
                  <div className="contact-item">
                    <div className="contact-copy">
                      <strong>Resume PDF</strong>
                      <span>
                        <a href="/resume/Meirambek-Kydyrov-CV-DevOps.pdf" target="_blank" rel="noreferrer">
                          Meirambek-Kydyrov-CV-DevOps.pdf
                        </a>
                      </span>
                    </div>
                  </div>
                  <div className="contact-item">
                    <div className="contact-copy">
                      <strong>Location</strong>
                      <span>Astana, Kazakhstan</span>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>

          <BuildFooter build={build} error={buildError} compact />
        </main>
      </div>
    </>
  );
}
