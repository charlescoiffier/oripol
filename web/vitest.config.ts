import { defineConfig } from 'vitest/config';

// Config séparée : les tests ciblent de la logique TypeScript pure, sans le plugin SvelteKit.
export default defineConfig({ test: { include: ['src/**/*.test.ts'] } });
