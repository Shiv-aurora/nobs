import {expect, type Locator, type Page, test} from '@playwright/test';

const demoPassword = process.env.NOPING_DEMO_USER_PASSWORD || 'NoPing-Demo-2026!';
const channelPath = '/acme/channels/project-atlas';

async function login(page: Page, username: string): Promise<void> {
    await page.context().clearCookies();
    await page.goto('/login');
    const email = page.getByRole('textbox', {name: /Email or username/i});
    await expect(email).toBeVisible();
    await email.fill(username);
    await page.getByRole('textbox', {name: /^Password/i}).fill(demoPassword);
    await page.getByRole('button', {name: /Log in/i}).click();
    await expect(page).not.toHaveURL(/\/login/);
    await page.goto(channelPath);
    await expect(composer(page)).toBeVisible();
    const dismissOnboarding = page.getByText(/No thanks, I'll figure it out myself/i);
    if (await dismissOnboarding.isVisible().catch(() => false)) {
        await dismissOnboarding.click();
    }
}

function composer(page: Page): Locator {
    return page.locator('#post_textbox, [data-testid="post_textbox"], .ProseMirror[contenteditable="true"]').last();
}

async function post(page: Page, message: string): Promise<void> {
    const input = composer(page);
    await input.fill(message);
    await page.getByRole('button', {name: 'Send Now'}).last().click();
    await expect(page.getByText(message.replace(/^\s*--direct\s+/, ''), {exact: false}).last()).toBeVisible();
}

async function openLatestAgentThread(page: Page): Promise<void> {
    const replyLink = page.getByText(/1 reply/i, {exact: true}).last();
    await expect(replyLink).toBeVisible({timeout: 60_000});
    await replyLink.click();
}

async function openLatestRouteEvidence(page: Page): Promise<void> {
    await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('.np-post-route-link'));
        buttons.at(-1)?.click();
    });
}

async function openNoPingPanel(page: Page): Promise<void> {
    const appBar = page.getByRole('button', {name: 'com.noping.enterprise'});
    await expect(appBar.first()).toBeVisible();
    await page.evaluate(() => window.dispatchEvent(new CustomEvent('noping:open-panel', {detail: {}})));
    await expect(page.getByText('NoBS context', {exact: true})).toBeVisible();
}

async function selectNoBSPanelTab(page: Page, label: string): Promise<void> {
    await page.evaluate((name) => {
        const button = Array.from(document.querySelectorAll<HTMLButtonElement>('.np-native-tabs button')).find((item) => item.textContent?.includes(name));
        button?.click();
    }, label);
}

test('enters the demo workspace with one click', async ({page}) => {
    await page.context().clearCookies();
    await page.goto('/login?redirect_to=/acme/nobs/calendar');
    await page.getByRole('button', {name: /Enter demo workspace/i}).click();
    await expect(page).toHaveURL(/\/acme\/nobs\/calendar$/);
    await expect(page.locator('.nobs-calendar__identity strong')).toHaveText('Calendar');
});

test('lands in the native NoBS channel workspace with no duplicate shell', async ({page}) => {
    await login(page, 'maya');

    await expect(page).toHaveTitle(/NoBS/);
    await expect(page).toHaveURL(/\/acme\/channels\/project-atlas/);
    await expect(page.getByText('Project Atlas', {exact: true}).first()).toBeVisible();
    await expect(page.locator('.SidebarChannel, [data-testid="channel-sidebar"]').first()).toBeVisible();
    await expect(page.locator('#postListContent, [data-testid="postList"]').first()).toBeVisible();
    await expect(page.getByText(/Mobile canary update: 2,416 sessions/i).first()).toBeVisible();
    await expect(page.locator('body')).not.toContainText(/Mattermost/i);
    await expect(page.locator('.np-shell, .np-sidebar, .np-messages-shell')).toHaveCount(0);
});

test('runs one coordinated delegate reply as a native thread and exposes route evidence', async ({page}) => {
    await login(page, 'maya');
    const question = `Why is Atlas delayed? ${Date.now()}`;
    await post(page, question);
    await openLatestAgentThread(page);

    await expect(page.getByText(/delegates consulted · 0 humans interrupted/i).last()).toBeVisible({timeout: 60_000});
    // The router may resolve this broad project question through the
    // organization agent or through Sarah's scoped delegate. Both are audited
    // identities; the next test pins the personal-delegate case specifically.
    await expect(page.locator('.np-post-badge.is-agent').last()).toContainText(/NoBS Organization Agent|Sarah's Agent/);

    await openLatestRouteEvidence(page);
    await expect(page.getByText('Current answer', {exact: true})).toBeVisible();
    await expect(page.getByText('Evidence', {exact: true})).toBeVisible();
    await expect(page.locator('.np-route-list li')).toHaveCount(4);
});

test('uses a represented employee identity for a personal delegate', async ({page}) => {
    await login(page, 'maya');
    await post(page, `What is blocking Atlas security? ${Date.now()}`);
    await openLatestAgentThread(page);

    await expect(page.getByText("Sarah's Agent", {exact: true}).last()).toBeVisible({timeout: 60_000});
    await openLatestRouteEvidence(page);
    await expect(page.getByText('Employee delegate', {exact: true})).toBeVisible();
    await expect(page.getByText('Current focus', {exact: true})).toBeVisible();
    await expect(page.getByText('Active blocker', {exact: true})).toBeVisible();
    await expect(page.getByText('Availability / OOO', {exact: true})).toBeVisible();
    await expect(page.getByText('Can answer without interrupting', {exact: true})).toBeVisible();
});

test('keeps the named employee identity on a policy-denied request', async ({page}) => {
    await login(page, 'maya');
    await post(page, `What is Sarah's salary? ${Date.now()}`);
    await openLatestAgentThread(page);

    await expect(page.getByText("Sarah's Agent", {exact: true}).last()).toBeVisible({timeout: 60_000});
    await expect(page.getByText(/Compensation data is restricted to People Operations/i).last()).toBeVisible();
});

test('shows realistic direct-message attention outcomes', async ({page}) => {
    await login(page, 'maya');
    for (const person of ['sarah', 'daniel', 'priya', 'alex']) {
        await expect(page.locator(`a[href$="/messages/@${person}"]`)).toBeVisible();
    }
});

test('human-only delivery strips the shortcut and makes no delegate reply', async ({page}) => {
    await login(page, 'maya');
    const message = `@sarah please call me about Atlas ${Date.now()}`;
    await post(page, `--direct ${message}`);
    await page.reload();

    const delivered = page.locator('#postListContent .post, [data-testid="post"]').filter({hasText: message}).last();
    await expect(delivered).not.toContainText('--direct');
    await expect(delivered.getByText('Human only', {exact: true}).first()).toBeVisible();
    await page.waitForTimeout(2_500);
    await expect(page.getByText(/agent is checking/i)).toHaveCount(0);
});

test('keeps native messaging usable at every release viewport', async ({page}) => {
    await login(page, 'maya');
    for (const viewport of [
        {width: 1440, height: 900},
        {width: 1024, height: 600},
        {width: 768, height: 1024},
        {width: 390, height: 844},
    ]) {
        await page.setViewportSize(viewport);
        await expect(composer(page)).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    }
});

test('keeps Needs You, attention analytics, and security in the native side panel', async ({page}) => {
    await login(page, 'alex');
    await openNoPingPanel(page);
    await page.getByText(/No thanks, I'll figure it out myself/i).click({timeout: 5_000}).catch(() => undefined);

    await selectNoBSPanelTab(page, 'Needs You');
    await expect(page.getByText(/things actually require you/i)).toBeVisible();
    await selectNoBSPanelTab(page, 'Attention');
    await expect(page.getByText('Human attention saved', {exact: true})).toBeVisible();
    await selectNoBSPanelTab(page, 'Security');
    await expect(page.getByText('Security boundaries', {exact: true})).toBeVisible();
});

test('prepares the two Calendar proof cases and skips a social meeting', async ({page}) => {
    await login(page, 'maya');
    await page.evaluate(async () => {
        await fetch('/plugins/com.noping.enterprise/api/v1/demo/reset', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
            body: '{}',
        });
    });
    await page.goto('/acme/nobs/calendar');
    await expect(page).toHaveURL(/\/acme\/nobs\/calendar$/);
    await expect(page).toHaveTitle('Calendar - NoBS');
    await expect(page.locator('.nobs-calendar__identity strong')).toHaveText('Calendar');
    await expect(page.getByRole('application', {name: 'channel sidebar region'})).toBeVisible();
    await expect(page.locator('#sidebarItem_threads')).toHaveAttribute('href', '/acme/threads');
    await expect(page.getByText('Welcome coffee with the team', {exact: true})).toBeVisible();
    await expect(page.getByText('skipped', {exact: true})).toBeVisible();

    await page.getByRole('button', {name: /Atlas engineering sync/}).click();
    await page.getByRole('button', {name: 'Prepare meeting'}).click();
    await expect(page.getByText('30 → 0 min', {exact: true})).toBeVisible();
    await expect(page.getByText('Cancel this meeting', {exact: true})).toBeVisible();
    await expect(page.locator('.nobs-meeting-aside .nobs-meeting-brief')).toBeVisible();
    await expect(page.locator('.nobs-preparation .nobs-swarm li')).toHaveCount(30);
    await expect(page.getByText(/Attendee agents worked for 15 minutes/i)).toBeVisible();
    await expect(page.locator('.nobs-preparation .nobs-agent-avatar.is-github .icon-github')).toBeVisible();
    await expect(page.locator('.nobs-preparation .nobs-agent-avatar.is-personal img').first()).toBeVisible();

    await page.getByRole('button', {name: /Atlas launch readiness/}).click();
    await page.getByRole('button', {name: 'Prepare meeting'}).click();
    await expect(page.getByText('60 → 15 min', {exact: true})).toBeVisible();
    await expect(page.getByText('Security boundary enforced', {exact: true})).toBeVisible();
    await expect(page.getByText('Gemini Code Assist', {exact: true}).first()).toBeVisible();
});

test('exposes OOO in the native account menu', async ({page}) => {
    await login(page, 'maya');
    await page.getByRole('button', {name: "User's account menu"}).click();
    await expect(page.getByRole('menuitem', {name: /OOO mode/})).toBeVisible();
});

test('keeps Calendar responsive without horizontal page overflow', async ({page}) => {
    await login(page, 'maya');
    await page.goto('/acme/nobs/calendar');
    await expect(page.locator('.nobs-calendar__identity strong')).toHaveText('Calendar');
    await expect(page.getByRole('application', {name: 'channel sidebar region'})).toBeVisible();
    for (const viewport of [
        {width: 1440, height: 900},
        {width: 1024, height: 600},
        {width: 768, height: 1024},
        {width: 390, height: 844},
    ]) {
        await page.setViewportSize(viewport);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    }
});

test('preserves native search, threads, reactions, files, and post actions', async ({page}) => {
    await login(page, 'maya');

    await expect(page.getByRole('button', {name: /Search/})).toBeVisible();
    await expect(page.locator('#sidebar-threads-button')).toBeVisible();
    const firstPost = page.locator('#postListContent .post:visible, [data-testid="post"]:visible').filter({hasText: 'Why is Atlas delayed?'}).last();
    await expect(firstPost).toBeVisible();
    await firstPost.hover();
    await expect(page.locator('[aria-label*="reaction" i]:visible, [data-testid*="reaction"]:visible').first()).toBeVisible();
    expect(await page.locator('[aria-label*="file" i], input[type="file"]').count()).toBeGreaterThan(0);
});
