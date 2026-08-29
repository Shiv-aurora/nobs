#!/usr/bin/env python3
"""Apply the reviewable NoBS source overlay to a pinned Mattermost checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


EXPECTED_COMMIT = "f9deca984f8a8d38a5f5e50600b45e22c90ebca1"


def require_text(path: Path, needle: str) -> str:
    value = path.read_text()
    if needle not in value:
        raise SystemExit(f"upstream drift: {path} no longer contains {needle!r}")
    return value


def replace_once(path: Path, old: str, new: str) -> None:
    value = require_text(path, old)
    if value.count(old) != 1:
        raise SystemExit(f"upstream drift: expected one occurrence in {path}, found {value.count(old)}")
    path.write_text(value.replace(old, new))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--overrides", required=True, type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    git_head = source / ".git" / "HEAD"
    if not git_head.exists():
        raise SystemExit("source must be a git checkout")

    # Docker performs the authoritative commit assertion. This marker makes the
    # overlay contract explicit for local drift checks as well.
    contract = source / "webapp" / "channels" / "package.json"
    require_text(contract, '"name": "mattermost-webapp"')

    channels = source / "webapp" / "channels"
    images = channels / "src" / "images" / "noping"
    images.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.assets / "logo.png", images / "logo.png")
    shutil.copy2(args.assets / "text-logo.png", images / "text-logo.png")

    root = channels / "src" / "root.html"
    root_text = require_text(root, "<title>Mattermost</title>")
    root_text = root_text.replace("<title>Mattermost</title>", "<title>NoBS</title>")
    root_text = root_text.replace("<title>NoBS</title>", "<script src='/static/nobs-route-alias.js'></script>\n    <title>NoBS</title>")
    root_text = root_text.replace("content='Mattermost'", "content='NoBS'")
    for size in (16, 24, 32, 64, 96):
        root_text = root_text.replace(
            f'/static/images/favicon/favicon-default-{size}x{size}.png',
            '/static/images/noping/logo.png',
        )
    root.write_text(root_text)

    webpack = channels / "webpack.config.js"
    webpack_text = require_text(webpack, "name: 'Mattermost'")
    webpack_text = webpack_text.replace(
        "const MiniCssExtractPlugin = require('mini-css-extract-plugin');",
        "const MiniCssExtractPlugin = require('mini-css-extract-plugin');\nconst TerserPlugin = require('terser-webpack-plugin');",
    )
    webpack_text = webpack_text.replace("name: 'Mattermost'", "name: 'NoBS'")
    webpack_text = webpack_text.replace("short_name: 'Mattermost'", "short_name: 'NoBS'")
    webpack_text = webpack_text.replace(
        "description: 'Mattermost is an open source, self-hosted Slack-alternative'",
        "description: 'NoBS brings personal agents to workplace messaging and meetings'",
    )
    webpack_text = webpack_text.replace(
        "{from: 'src/images/favicon', to: 'images/favicon'},",
        "{from: 'src/images/favicon', to: 'images/favicon'},\n                {from: 'src/images/noping', to: 'images/noping'},\n                {from: 'src/nobs-route-alias.js', to: 'nobs-route-alias.js'},",
    )
    webpack_text = webpack_text.replace(
        "src: path.resolve('src/images/favicon/android-chrome-192x192.png')",
        "src: path.resolve('src/images/noping/logo.png')",
    )
    # The upstream build embeds the wall clock in its initial-load telemetry.
    # Pin it so two clean builds of the same source and overlay are identical.
    timestamp = "const buildTimestamp = Date.now();"
    if timestamp not in webpack_text:
        raise SystemExit("upstream drift: webpack build timestamp declaration changed")
    webpack_text = webpack_text.replace(timestamp, "const buildTimestamp = 0;")
    config_start = """var config = {
    entry: ['./src/root.tsx'],"""
    deterministic_config_start = """var config = {
    // Keep module discovery deterministic. The upstream graph contains CSS
    // order conflicts whose winner otherwise depends on worker timing.
    parallelism: 1,
    entry: ['./src/root.tsx'],"""
    if config_start not in webpack_text:
        raise SystemExit("upstream drift: webpack config root changed")
    webpack_text = webpack_text.replace(config_start, deterministic_config_start)
    # The default production minimizer uses every available CPU. On the
    # 8-GiB Docker builder this can exhaust memory as multiple terser and image
    # workers peak together. Serial workers keep the artifact identical while
    # making clean builds reliable.
    default_minimizers = """        minimizer: [
            '...',
            new ImageMinimizerPlugin({
                minimizer: {"""
    bounded_minimizers = """        minimizer: [
            new TerserPlugin({parallel: 1}),
            new ImageMinimizerPlugin({
                concurrency: 1,
                minimizer: {"""
    if default_minimizers not in webpack_text:
        raise SystemExit("upstream drift: webpack production minimizers changed")
    webpack_text = webpack_text.replace(default_minimizers, bounded_minimizers)
    webpack.write_text(webpack_text)
    shutil.copy2(args.overrides / "nobs_route_alias.js", channels / "src" / "nobs-route-alias.js")

    # mini-css-extract-plugin resolves conflicting upstream CSS order by the
    # insertion order of Sets and chunk groups. Those orders can differ across
    # otherwise identical clean builds. Sort both inputs and equal-index ties
    # by stable identifiers before the plugin applies its existing algorithm.
    css_plugin = source / "webapp" / "node_modules" / "mini-css-extract-plugin" / "dist" / "index.js"
    css_text = require_text(css_plugin, "const modulesList = [...modules];")
    css_text = css_text.replace(
        "const modulesList = [...modules];",
        "const modulesList = [...modules].sort((a, b) => a.readableIdentifier(requestShortener).localeCompare(b.readableIdentifier(requestShortener)));",
    )
    css_text = css_text.replace(
        "const modulesByChunkGroup = Array.from(chunk.groupsIterable, chunkGroup => {",
        "const chunkGroupKey = chunkGroup => modulesList.map(module => { const index = chunkGroup.getModulePostOrderIndex(module); return index === undefined ? '' : `${String(index).padStart(10, '0')}:${module.readableIdentifier(requestShortener)}`; }).filter(Boolean).sort().join('|');\n    const modulesByChunkGroup = Array.from(chunk.groupsIterable).sort((a, b) => chunkGroupKey(a).localeCompare(chunkGroupKey(b))).map(chunkGroup => {",
    )
    equal_index_sort = ".filter(item => item.index !== undefined).sort((a, b) => b.index - a.index).map(item => item.module);"
    if equal_index_sort not in css_text:
        raise SystemExit("upstream drift: mini-css module ordering changed")
    css_text = css_text.replace(
        equal_index_sort,
        ".filter(item => item.index !== undefined).sort((a, b) => (b.index - a.index) || a.module.readableIdentifier(requestShortener).localeCompare(b.module.readableIdentifier(requestShortener))).map(item => item.module);",
    )
    css_plugin.write_text(css_text)

    branding = channels / "src" / "components" / "global_header" / "left_controls" / "product_menu" / "product_branding_team_edition" / "product_branding_free_edition.tsx"
    branding.write_text((args.overrides / "product_branding_free_edition.tsx").read_text())

    loading_dir = channels / "src" / "components" / "initial_loading_screen"
    (loading_dir / "initial_loading_screen_template.html").write_text((args.overrides / "initial_loading_screen_template.html").read_text())
    (loading_dir / "initial_loading_screen.css").write_text((args.overrides / "initial_loading_screen.css").read_text())
    (channels / "src" / "components" / "header_footer_route" / "header.tsx").write_text((args.overrides / "header.tsx").read_text())

    # Keep the normal credential form, but make the public demo repeatable in
    # one click. The plugin creates a short-lived session for a configured,
    # non-admin demo user so no password is embedded in the browser bundle.
    login = channels / "src" / "components" / "login" / "login.tsx"
    replace_once(
        login,
        """                                                <SaveButton
                                                    extraClasses='login-body-card-form-button-submit large'
                                                    saving={isWaiting}
                                                    onClick={preSubmit}
                                                    defaultMessage={formatMessage({id: 'login.logIn', defaultMessage: 'Log in'})}
                                                    savingMessage={formatMessage({id: 'login.logingIn', defaultMessage: 'Logging in…'})}
                                                />
""",
        """                                                <SaveButton
                                                    extraClasses='login-body-card-form-button-submit large'
                                                    saving={isWaiting}
                                                    onClick={preSubmit}
                                                    defaultMessage={formatMessage({id: 'login.logIn', defaultMessage: 'Log in'})}
                                                    savingMessage={formatMessage({id: 'login.logingIn', defaultMessage: 'Logging in…'})}
                                                />
                                                <div className='nobs-demo-login-divider'><span>or</span></div>
                                                <form
                                                    method='post'
                                                    action='/plugins/com.noping.enterprise/api/v1/demo-login'
                                                >
                                                <button
                                                    type='submit'
                                                    className='nobs-demo-login-button'
                                                    disabled={isWaiting}
                                                >
                                                    <span>Enter demo workspace</span>
                                                    <small>No password needed</small>
                                                </button>
                                                </form>
""",
    )

    # Team-scoped plugin routes normally replace ChannelController entirely,
    # which also removes the real workspace sidebar. Calendar is a native
    # NoBS destination, so keep the upstream Sidebar mounted and place the
    # plugin view in the existing center grid area.
    team_controller = channels / "src" / "components" / "team_controller" / "team_controller.tsx"
    replace_once(
        team_controller,
        "import ProductPluggable from 'components/product_pluggable';\n",
        "import ProductPluggable from 'components/product_pluggable';\nimport Sidebar from 'components/sidebar';\n",
    )
    replace_once(
        team_controller,
        """                    render={() => (
                        <Pluggable
                            pluggableName={'NeedsTeamComponent'}
                            pluggableId={plugin.id}
                            css={{gridArea: 'center'}}
                        />
                    )}
""",
        """                    render={() => (
                        <>
                            <Sidebar/>
                            <Pluggable
                                pluggableName={'NeedsTeamComponent'}
                                pluggableId={plugin.id}
                                css={{gridArea: 'center'}}
                            />
                        </>
                    )}
        """,
    )

    # GlobalThreadsLink normally derives its URL from the nearest channel
    # route match. On a team-scoped plugin route that match includes the plugin
    # path, so keep the destination anchored to the current team instead.
    global_threads = channels / "src" / "components" / "threading" / "global_threads_link" / "global_threads_link.tsx"
    replace_once(
        global_threads,
        "import {Link, useRouteMatch, useLocation, matchPath} from 'react-router-dom';\n",
        "import {Link, useLocation, matchPath} from 'react-router-dom';\n",
    )
    replace_once(global_threads, "    const {url} = useRouteMatch();\n", "")
    replace_once(
        global_threads,
        "                    to={`${url}/threads`}\n",
        "                    to={`/${pathname.split('/').filter(Boolean)[0]}/threads`}\n",
    )

    # Calendar is a first-class destination beside Threads. Patch the pinned
    # native sidebar instead of introducing a second navigation shell.
    sidebar = channels / "src" / "components" / "sidebar" / "sidebar_list" / "sidebar_list.tsx"
    replace_once(
        sidebar,
        "import React, {lazy} from 'react';\n",
        "import React, {lazy} from 'react';\nimport {Link} from 'react-router-dom';\n",
    )
    replace_once(
        sidebar,
        """                <GlobalThreadsLink/>
                <DraftsLink/>
""",
        """                <GlobalThreadsLink/>
                {this.props.currentTeam?.name && (
                    <ul className='SidebarGlobalThreads NavGroupContent nav nav-pills__container nobs-calendar-link'>
                        <li
                            id='sidebar-calendar-button'
                            className={classNames('SidebarChannel', {active: window.location.pathname.includes('/nobs/calendar')})}
                            tabIndex={-1}
                        >
                            <Link
                                to={`/${this.props.currentTeam.name}/com.noping.enterprise/calendar`}
                                id='sidebarItem_calendar'
                                draggable='false'
                                className='SidebarLink sidebar-item'
                                tabIndex={0}
                            >
                                <span className='icon'><i className='icon-calendar-outline'/></span>
                                <div className='SidebarChannelLinkLabel_wrapper'>
                                    <span className='SidebarChannelLinkLabel sidebar-item__name'>Calendar</span>
                                </div>
                            </Link>
                        </li>
                    </ul>
                )}
                <DraftsLink/>
""",
    )

    # NoBS is a browser-first web product. Skip the upstream first-visit
    # desktop-app chooser and continue directly to the requested web route.
    landing = channels / "src" / "components" / "linking_landing_page" / "linking_landing_page.tsx"
    replace_once(
        landing,
        """    componentDidMount() {
        if (this.checkLandingPreferenceApp()) {
            this.openMattermostApp();
        }

        window.addEventListener('beforeunload', this.clearLandingPreferenceIfNotChecked);
    }
""",
        """    componentDidMount() {
        this.openInBrowser();
    }
""",
    )

    styles = channels / "src" / "sass" / "styles.scss"
    styles_text = styles.read_text()
    marker = "@include meta.load-css('widgets/module');"
    if marker not in styles_text:
        raise SystemExit("upstream drift: styles.scss insertion marker changed")
    styles.write_text(styles_text.replace(marker, marker + "\n@include meta.load-css('noping-brand');"))
    shutil.copy2(args.overrides / "_noping-brand.scss", channels / "src" / "sass" / "_noping-brand.scss")

    # Keep upstream notices intact while replacing common default copy on normal
    # user routes. Translation ids and code identifiers intentionally remain.
    user_roots = [
        channels / "src" / "components",
        channels / "src" / "i18n" / "en.json",
    ]
    for root_path in user_roots:
        files = [root_path] if root_path.is_file() else root_path.rglob("*")
        for path in files:
            if path.suffix not in {".ts", ".tsx", ".json", ".html"} or ".test." in path.name:
                continue
            text = path.read_text()
            if "Mattermost" not in text:
                continue
            # Copyright headers, URLs, imports and identifiers are not product
            # strings. Replace only a standalone capitalized product name.
            lines = []
            for line in text.splitlines(keepends=True):
                if "Copyright" in line or "http" in line or line.lstrip().startswith("import "):
                    lines.append(line)
                else:
                    lines.append(re.sub(r"(?<![A-Za-z0-9_])Mattermost(?![A-Za-z0-9_])", "NoBS", line))
            path.write_text("".join(lines))

    manifest = {
        "upstream_commit": EXPECTED_COMMIT,
        "assets": {
            name: hashlib.sha256((args.assets / name).read_bytes()).hexdigest()
            for name in ("logo.png", "text-logo.png")
        },
    }
    (source / "webapp" / "noping-overlay.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
