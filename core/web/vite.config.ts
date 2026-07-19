import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { getVertical } from "./src/config/verticals";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, "VITE_");
  const vertical = getVertical(env.VITE_VERTICAL);
  return {
    server: {
      host: "::",
      port: 8080,
    },
    plugins: [
      react(),
      {
        name: "vertical-html",
        transformIndexHtml: {
          order: "pre" as const,
          handler(html: string) {
            return html
              .replaceAll("%VITE_SITE_TITLE%", vertical.metaTitle)
              .replaceAll("%VITE_SITE_DESCRIPTION%", vertical.metaDescription)
              .replaceAll(
                "%VITE_SITE_AUTHOR%",
                `${vertical.logoText.primary}${vertical.logoText.suffix}`,
              );
          },
        },
      },
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
