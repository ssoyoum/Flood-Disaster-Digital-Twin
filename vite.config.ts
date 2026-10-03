import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Search Console verifies the served HTML, so its meta tag has to be in index.html, not added by JS.
// The tag appears only when VITE_GSC_VERIFICATION is set at build time.
function searchConsoleVerification(token: string | undefined): Plugin {
  return {
    name: "floodops-search-console-verification",
    transformIndexHtml(html) {
      if (!token || !/^[A-Za-z0-9_-]{10,100}$/.test(token)) return html;
      return html.replace("</title>", `</title>
    <meta name="google-site-verification" content="${token}" />`);
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  return {
    plugins: [react(), searchConsoleVerification(env.VITE_GSC_VERIFICATION)],
    server: {
      host: true,
      port: 5173,
      strictPort: true,
    },
  };
});
