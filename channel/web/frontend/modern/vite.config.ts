import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

function antDesignXCodeHighlighterFullPrism(): Plugin {
  return {
    name: 'ant-design-x-code-highlighter-full-prism',
    enforce: 'pre',
    transform(code, id) {
      if (!id.endsWith('/@ant-design/x/es/code-highlighter/CodeHighlighter.js')) {
        return null;
      }

      return {
        code: code.replace('prismLightMode = true,', 'prismLightMode = false,'),
        map: null,
      };
    },
  };
}

export default defineConfig({
  plugins: [antDesignXCodeHighlighterFullPrism(), react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Keep hash-named lazy chunks available for already-open chat tabs.
    emptyOutDir: false,
  },
});
