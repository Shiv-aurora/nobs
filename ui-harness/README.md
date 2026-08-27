# NoPing UI harness

This directory is a browser validation harness for the **same API contracts and CSS used by the Mattermost React plugin**. It is not a production client and is not deployed in the judging path.

It exists so the product can be inspected against the live FastAPI service before a Mattermost server is available. The final client is `plugin/webapp/src/`, registered as the Mattermost `/noping` route.
