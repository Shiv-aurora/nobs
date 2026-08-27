SHELL := /bin/bash
PLUGIN_ID := com.noping.enterprise
PLUGIN_VERSION := $(shell python3 -c 'import json; print(json.load(open("plugin.json")).get("version", "0.1.0"))')
DIST_DIR := dist
BUNDLE := $(DIST_DIR)/$(PLUGIN_ID)-$(PLUGIN_VERSION).tar.gz
GO ?= go
NPM ?= npm

.PHONY: all clean check test webapp server bundle dev-bundle

all: check bundle

check:
	$(GO) fmt ./...
	$(GO) test ./...
	cd webapp && $(NPM) run typecheck

# npm ci is intentionally separate so CI and Codex can cache dependencies.
webapp:
	cd webapp && $(NPM) run build

server:
	mkdir -p server/dist
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 $(GO) build -trimpath -ldflags='-s -w' -o server/dist/plugin-linux-amd64 ./server
	CGO_ENABLED=0 GOOS=linux GOARCH=arm64 $(GO) build -trimpath -ldflags='-s -w' -o server/dist/plugin-linux-arm64 ./server
	CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 $(GO) build -trimpath -ldflags='-s -w' -o server/dist/plugin-darwin-amd64 ./server
	CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 $(GO) build -trimpath -ldflags='-s -w' -o server/dist/plugin-darwin-arm64 ./server
	CGO_ENABLED=0 GOOS=windows GOARCH=amd64 $(GO) build -trimpath -ldflags='-s -w' -o server/dist/plugin-windows-amd64.exe ./server

bundle: webapp server
	mkdir -p $(DIST_DIR)
	tar --sort=name --mtime='UTC 2026-08-03' --owner=0 --group=0 --numeric-owner \
		-czf $(BUNDLE) plugin.json assets server/dist webapp/dist
	@echo "Built $(BUNDLE)"

# Build only the current Linux architecture for fast local/Codex iteration.
dev-bundle: webapp
	mkdir -p server/dist $(DIST_DIR)
	CGO_ENABLED=0 $(GO) build -trimpath -o server/dist/plugin-linux-amd64 ./server
	tar -czf $(BUNDLE) plugin.json assets server/dist webapp/dist
	@echo "Built $(BUNDLE)"

clean:
	rm -rf $(DIST_DIR) server/dist webapp/dist
