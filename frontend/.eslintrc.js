module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ['react', 'react-hooks'],
  rules: {
    // Minimal rules - just catch common errors
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    'no-console': ['warn', { allow: ['error', 'warn'] }],
    'react/prop-types': 'off', // Disabled since we're not using TypeScript yet
    'react/react-in-jsx-scope': 'off', // Not needed with React 17+
  },
  settings: {
    react: {
      version: 'detect',
    },
  },
};
