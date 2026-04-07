import type { BuildMetadata } from "../types";

interface BuildFooterProps {
  build: BuildMetadata | null;
  error?: string | null;
  compact?: boolean;
}

export function BuildFooter({ build, error = null, compact = false }: BuildFooterProps) {
  const summary = error
    ? `Build metadata unavailable: ${error}`
    : build
      ? compact
        ? `App: ${build.app_version} | Image: ${build.image_tag} | Build: ${build.build_id}`
        : `DevOps Platform 2026 | v${build.app_version} | tag ${build.image_tag} | built ${build.build_date} | run ${build.build_id} | FE/BE ${build.app_version} | DB ${build.component_versions.PostgreSQL} | registry ${build.container_registry}`
      : "Loading deployment fingerprint...";

  return (
    <footer className="build-footer">
      <p className="eyebrow">Build Metadata</p>
      <details open={Boolean(error)} id="build-footer-shell">
        <summary className="build-summary">{summary}</summary>
        {build ? (
          <div className="build-details-body">
            <div className={compact ? "compact-grid" : "grid"}>
              <article className="card">
                <div className="label">Deployment</div>
                <p className="card-title">v{build.app_version}</p>
                <div className="muted-row">
                  <span>Environment: {build.environment}</span>
                  <span>Image tag: {build.image_tag}</span>
                </div>
                <div className="muted-row">
                  <span>Build SHA: {build.build_sha}</span>
                  <span>Build ID: {build.build_id}</span>
                </div>
                <div className="muted-row">
                  <span>Build date: {build.build_date}</span>
                  <span>Registry: {build.container_registry}</span>
                </div>
              </article>
              <article className="card">
                <div className="label">Recommended Components</div>
                <div className="detail-list">
                  {Object.entries(build.component_versions).map(([name, version]) => (
                    <div className="detail-item" key={name}>
                      <span>{name}</span>
                      <strong>{version}</strong>
                    </div>
                  ))}
                </div>
                <p className="footer-note">
                  These are the pinned versions this stack is intended to run against.
                </p>
              </article>
            </div>
          </div>
        ) : null}
      </details>
    </footer>
  );
}
