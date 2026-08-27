import {defineConfig} from '@playwright/test';

export default defineConfig({
    testDir: '.',
    testMatch: '**/*.spec.ts',
    timeout: 45_000,
    expect: {timeout: 10_000},
    fullyParallel: false,
    workers: 1,
    retries: 0,
    reporter: [['list']],
    use: {
        baseURL: process.env.MATTERMOST_URL || 'http://localhost:8065',
        screenshot: 'only-on-failure',
        trace: 'retain-on-failure',
    },
});
