import {expect, type Page, test} from '@playwright/test';

const password = process.env.NOPING_DEMO_USER_PASSWORD || 'NoPing-Demo-2026!';
const channelPath = '/acme/channels/project-atlas';

async function login(page: Page, username: string): Promise<void> {
    await page.context().clearCookies();
    await page.goto('/login');
    await page.getByRole('textbox', {name: /Email or username/i}).fill(username);
    await page.getByRole('textbox', {name: /^Password/i}).fill(password);
    await page.getByRole('button', {name: /Continue to NoBS|Log in/i}).click();
    await page.goto(channelPath);
    await expect(page.locator('#post_textbox, [data-testid="post_textbox"], .ProseMirror[contenteditable="true"]').last()).toBeVisible();
    await page.locator('#initialPageLoadingScreen').waitFor({state: 'hidden', timeout: 30_000}).catch(() => undefined);
    await page.getByText(/No thanks, I.ll figure it out myself/i).last().click({timeout: 8_000}).catch(() => undefined);
    await page.locator('[data-cy="onboarding-task-list-overlay"]').waitFor({state: 'hidden', timeout: 8_000}).catch(() => undefined);
}

async function post(page: Page, message: string): Promise<void> {
    const composer = page.locator('#post_textbox, [data-testid="post_textbox"], .ProseMirror[contenteditable="true"]').last();
    await composer.fill(message);
    await composer.press('Enter');
}

test('capture native NoPing release evidence', async ({page}) => {
    test.skip(process.env.NOPING_CAPTURE_EVIDENCE !== 'true', 'Run explicitly after the native browser suite passes.');

    await page.setViewportSize({width: 1440, height: 900});
    await login(page, 'maya');
    await page.screenshot({path: '../docs/evidence/native-channel-workspace.png', fullPage: true});

    await post(page, `@sarah What is blocking Atlas security? ${Date.now()}`);
    await expect(page.getByText('Sarah Chen · NoPing agent', {exact: true}).last()).toBeVisible({timeout: 60_000});
    await page.screenshot({path: '../docs/evidence/native-personal-delegate.png', fullPage: true});

    await page.getByText(/delegates consulted · 0 humans interrupted/i).last().click();
    await expect(page.getByText('Employee delegate', {exact: true})).toBeVisible();
    await page.screenshot({path: '../docs/evidence/native-route-panel.png', fullPage: true});

    await page.getByRole('button', {name: /Needs You/i}).click();
    await page.screenshot({path: '../docs/evidence/native-needs-you.png', fullPage: true});

    await page.locator('[aria-label*="Close"], [data-testid*="close"] button').last().click().catch(() => undefined);
    await post(page, `--direct @sarah Please call me about Atlas ${Date.now()}`);
    await expect(page.getByText('Human only', {exact: true}).last()).toBeVisible();
    await page.screenshot({path: '../docs/evidence/native-human-only.png', fullPage: true});

    await page.setViewportSize({width: 390, height: 844});
    await expect(page.locator('#post_textbox, [data-testid="post_textbox"], .ProseMirror[contenteditable="true"]').last()).toBeVisible();
    await page.screenshot({path: '../docs/evidence/native-phone.png', fullPage: true});
});
