# CRUSH.md

Repo: Go API Gateway with OIDC (gorilla/mux, coreos/oidc). No Cursor/Copilot rules found.

Commands
- Build: go build ./...
- Run: go run .
- Test all: go test ./...
- Test verbose: go test -v ./...
- Test single package: go test ./...
- Test single file: go test -run TestOIDCFLow -v
- Lint (go vet): go vet ./...
- Format: go fmt ./...
- Mod tidy: go mod tidy
- Docker build: docker build -t api-gateway:local .
- Docker run: docker run --rm -p 8080:8080 -e OIDC_CLIENT_ID=... -e OIDC_CLIENT_SECRET=... -e OIDC_PROVIDER_URL=... api-gateway:local

Code style
- Imports: std -> third-party -> local; use goimports/go fmt; group with blank lines; no unused imports.
- Formatting: go fmt enforced; 120-col guideline; prefer short var names for short scopes.
- Types: prefer concrete types at package boundaries; use struct tags json:"..."; avoid interface{}; return (T, error).
- Naming: MixedCaps (Exported) and mixedCaps (unexported); constants ALL_CAPS not used, use CamelCase; handlers end with Handler.
- Errors: return wrapped errors with fmt.Errorf("context: %w", err); never panic in request path; use http.Error with proper status.
- Context: pass context.Context from request; avoid background contexts except at startup.
- HTTP: set HttpOnly/Secure cookies where applicable; validate state param; avoid leaking sensitive data in logs.
- Config: read from env; validate required vars at startup; avoid default secrets.
- Testing: use t.Helper for helpers; table-driven tests when applicable; name tests TestXxx; use t.Setenv for env.
- Security: do not log tokens/secrets; verify ID token audience/issuer; use TLS in production behind a proxy.
