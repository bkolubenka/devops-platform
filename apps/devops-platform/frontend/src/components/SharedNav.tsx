import { Link, useLocation } from "react-router-dom";

interface SharedNavProps {
  activeSection?: string;
}

const sectionLinks = [
  { id: "home", label: "Overview" },
  { id: "portfolio", label: "Projects" },
  { id: "services", label: "Services" },
  { id: "incidents", label: "Incidents" },
  { id: "ai", label: "Incident Assistant" },
  { id: "observability", label: "Observability" },
];

export function SharedNav({ activeSection = "home" }: SharedNavProps) {
  const location = useLocation();
  const isResume = location.pathname.startsWith("/resume");

  return (
    <nav className="site-nav">
      <div className="nav-shell">
        <Link className="brand" to="/">
          DevOps Platform
        </Link>
        <div className="nav-links">
          {sectionLinks.map((link) => (
            <a
              key={link.id}
              href={`/#${link.id}`}
              className={`nav-link${!isResume && activeSection === link.id ? " active" : ""}`}
            >
              {link.label}
            </a>
          ))}
          <Link className={`nav-link${isResume ? " active" : ""}`} to="/resume/">
            Resume
          </Link>
        </div>
      </div>
    </nav>
  );
}
