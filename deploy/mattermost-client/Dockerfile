# syntax=docker/dockerfile:1.7

ARG MATTERMOST_VERSION=11.10.1
ARG MATTERMOST_COMMIT=f9deca984f8a8d38a5f5e50600b45e22c90ebca1

FROM --platform=$BUILDPLATFORM node:24-bookworm-slim AS webapp
ARG MATTERMOST_COMMIT

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --filter=blob:none https://github.com/mattermost/mattermost.git . \
    && git checkout --detach "${MATTERMOST_COMMIT}" \
    && test "$(git rev-parse HEAD)" = "${MATTERMOST_COMMIT}"

# Keep dependency installation in its own cached layer. The overlay changes
# frequently while the pinned upstream lockfile does not.
WORKDIR /src/webapp
RUN npm ci --no-audit --no-fund

# Release verification passes different nonces to rerun the overlay and
# compiler from the same pristine pinned checkout/dependency layer.
ARG REPRO_NONCE=0
RUN test -n "${REPRO_NONCE}"

COPY deploy/mattermost-client/apply_branding.py /noping/apply_branding.py
COPY deploy/mattermost-client/overrides /noping/overrides
COPY plugin/webapp/src/assets/logo.png /noping/assets/logo.png
COPY plugin/webapp/src/assets/text-logo.png /noping/assets/text-logo.png

RUN python3 /noping/apply_branding.py --source /src --assets /noping/assets --overrides /noping/overrides
WORKDIR /src/webapp
# `npm ci` has already built the pinned platform workspaces. Rebuilding all of
# them concurrently with `channels` introduces a race where webpack can read a
# partially rewritten component CSS bundle. Build only the branded client here
# so clean checkouts produce byte-identical assets.
RUN npm run build --workspace=channels

FROM mattermost/mattermost-team-edition:${MATTERMOST_VERSION}
COPY --from=webapp --chown=mattermost:mattermost /src/webapp/channels/dist/ /mattermost/client/
COPY --from=webapp /src/LICENSE.txt /mattermost/NOTICE-NOPING-UPSTREAM-LICENSE.txt
COPY --from=webapp /src/NOTICE.txt /mattermost/NOTICE-NOPING-UPSTREAM.txt
