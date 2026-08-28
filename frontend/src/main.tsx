import React from "react";
import ReactDOM from "react-dom/client";
import CssBaseline from "@mui/joy/CssBaseline";
import { CssVarsProvider } from "@mui/joy/styles";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <CssVarsProvider defaultMode="system" modeStorageKey="graphrag-mode">
      <CssBaseline />
      <App />
    </CssVarsProvider>
  </React.StrictMode>
);
