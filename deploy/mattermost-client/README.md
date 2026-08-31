# NoBS native web client

The production image keeps the official Mattermost Team Edition server binary
and replaces only its bundled web client with a client compiled from the pinned
11.10.1 source revision.

- Upstream revision: `f9deca984f8a8d38a5f5e50600b45e22c90ebca1`
- Branding changes are applied by `apply_branding.py`, which fails closed when
  expected upstream source markers drift.
- NoBS uses the repository's gradient `logo.png` and renders the product name as accessible text. The retired raster wordmark is intentionally not a build input.
- Visible product copy says NoBS while plugin IDs and image names retain `noping` for compatibility.
- Apache and upstream notice files remain packaged at `/mattermost/NOTICE-*`.

Build from the repository root:

```sh
docker build -f deploy/mattermost-client/Dockerfile -t noping-mattermost:11.10.1-0.3.0 .
```
