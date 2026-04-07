import { Navigate, Route, Routes } from "react-router-dom";

import { ResumePage } from "./pages/ResumePage";
import { PortalPage } from "./pages/PortalPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PortalPage />} />
      <Route path="/resume" element={<ResumePage />} />
      <Route path="/resume/" element={<ResumePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
