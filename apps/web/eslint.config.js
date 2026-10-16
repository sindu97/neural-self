import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'
import globals from 'globals'
import jsdoc from 'eslint-plugin-jsdoc'
import tseslint from 'typescript-eslint'

export default defineConfig([
  globalIgnores(['dist', 'src/lib/api/schema.d.ts']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // Feature boundaries: another feature is used only through its public
      // index.ts (e.g. '@/features/documents'), never its internal files.
      // Inside a feature, use relative imports. Pages are loaded lazily by
      // the router, which is the one place allowed to reach into a feature.
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/features/*/*'],
              message: "Import another feature through its public API, e.g. '@/features/documents'.",
            },
          ],
        },
      ],
    },
  },
  {
    // Documentation (TSDoc style): every exported function, component, hook,
    // class and interface explains what it does. Types live in TypeScript,
    // so comments never repeat them.
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/components/ui/**', 'src/**/*.test.{ts,tsx}', 'src/lib/api/schema.d.ts'],
    plugins: { jsdoc },
    settings: { jsdoc: { mode: 'typescript' } },
    rules: {
      'jsdoc/require-jsdoc': [
        'error',
        {
          publicOnly: true,
          require: { FunctionDeclaration: true, ClassDeclaration: true },
          contexts: ['TSInterfaceDeclaration'],
        },
      ],
      'jsdoc/require-description': 'error',
      'jsdoc/no-types': 'error',
      'jsdoc/check-alignment': 'error',
      'jsdoc/check-tag-names': ['error', { definedTags: ['remarks'] }],
      'jsdoc/multiline-blocks': 'error',
      'jsdoc/no-multi-asterisks': 'error',
    },
  },
  {
    files: ['src/app/router.tsx'],
    rules: { 'no-restricted-imports': 'off' },
  },
  {
    // Generated shadcn/ui components export their style variants alongside the component.
    files: ['src/components/ui/**'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
  {
    files: ['tests/**', '**/*.test.{ts,tsx}'],
    rules: { 'no-restricted-imports': 'off' },
  },
])
