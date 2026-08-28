import {expect, type Page, test} from '@playwright/test';

const demoPassword = process.env.NOPING_DEMO_USER_PASSWORD || 'NoPing-Demo-2026!';

async function login(page: Page, username: string): Promise<void> {
    await page.context().clearCookies();
    await page.goto('/login');
    const viewInBrowser = page.getByRole('link', {name: 'View in Browser'});
    if (await viewInBrowser.waitFor({state: 'visible', timeout: 10_000}).then(() => true).catch(() => false)) {
        await viewInBrowser.click();
    }
    await page.getByRole('textbox', {name: 'Email or Username'}).fill(username);
    await page.getByRole('textbox', {name: 'Password'}).fill(demoPassword);
    await page.getByRole('button', {name: 'Log in', exact: true}).click();
    await expect(page).not.toHaveURL(/\/login/);
    await page.goto('/noping');
    await expect(page.getByText('Agent network healthy')).toBeVisible();
}

async function ask(page: Page, question: string): Promise<void> {
    const input = page.getByRole('textbox', {name: 'Ask your company'});
    await input.fill(question);
    const response = page.waitForResponse((item) => item.url().endsWith('/api/v1/query') && item.request().method() === 'POST');
    await input.press('Enter');
    await expect((await response).status()).toBe(200);
}

test('capture deployed Phase 2 evidence', async ({page}) => {
    test.skip(process.env.NOPING_CAPTURE_EVIDENCE !== 'true', 'Run explicitly to refresh deployed evidence screenshots.');

    await login(page, 'maya');
    await ask(page, 'Why has Atlas not shipped?');
    await expect(page.getByText('Answered by the organization')).toBeVisible();
    await page.screenshot({path: '../docs/evidence/phase2-organization-answer.png', fullPage: true});

    await login(page, 'priya');
    await ask(page, 'Should Atlas launch for the $200K customer?');
    await expect(page.getByText('Existing decision applied')).toBeVisible();
    await page.screenshot({path: '../docs/evidence/phase2-decision-memory.png', fullPage: true});

    await page.getByRole('button', {name: 'Audit trail'}).click();
    await expect(page.getByRole('heading', {name: 'Audit trail'})).toBeVisible();
    await page.screenshot({path: '../docs/evidence/phase2-audit-trail.png', fullPage: true});

    await page.getByRole('button', {name: 'Agent operations'}).click();
    await expect(page.getByRole('heading', {name: 'Agent operations'})).toBeVisible();
    await page.screenshot({path: '../docs/evidence/phase2-agent-operations.png', fullPage: true});
});
