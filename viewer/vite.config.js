import { defineConfig } from "vite";
import cssInjectedByJsPlugin from "vite-plugin-css-injected-by-js";

export default defineConfig({
    plugins: [cssInjectedByJsPlugin()],
    build: {
        lib: {
            entry: "src/main.ts",
            name: "AppendixViewer",
            fileName: (format) => `appendix-viewer.js`,
            formats: ["umd"],
        },
        rollupOptions: {
            external: ["jquery"],
            output: {
                globals: { jquery: "$" },
            },
        },
    },
});
