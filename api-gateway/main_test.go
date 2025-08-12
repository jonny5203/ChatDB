package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestAuthMiddleware(t *testing.T) {

	// Create a new request
	req, err := http.NewRequest("GET", "/mock", nil)
	if err != nil {
		t.Fatal(err)
	}

	// Create a new recorder
	rr := httptest.NewRecorder()

	// Configure minimal env for router
	t.Setenv("OIDC_CLIENT_ID", "test")
	t.Setenv("OIDC_CLIENT_SECRET", "test")
	// Use an httptest server to satisfy discovery calls
	var srv *httptest.Server
	srv = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/.well-known/openid-configuration" {
			w.Header().Set("Content-Type", "application/json")
			w.Write([]byte(`{"issuer":"` + srv.URL + `","authorization_endpoint":"` + srv.URL + `/auth","token_endpoint":"` + srv.URL + `/token","jwks_uri":"` + srv.URL + `/keys"}`))
			return
		}
		if r.URL.Path == "/keys" {
			w.Header().Set("Content-Type", "application/json")
			w.Write([]byte(`{"keys":[]}`))
			return
		}
		http.NotFound(w, r)
	}))
	defer srv.Close()
	t.Setenv("OIDC_PROVIDER_URL", srv.URL)

	// Create a new router
	r, err := createRouter("")
	if err != nil {
		t.Fatal(err)
	}

	// Serve the request
	r.ServeHTTP(rr, req)

	// Check the status code
	if status := rr.Code; status != http.StatusUnauthorized {
		t.Errorf("handler returned wrong status code: got %v want %v",
			status, http.StatusUnauthorized)
	}

	// Create a new request with a valid token
	req, err = http.NewRequest("GET", "/mock", nil)
	if err != nil {
		t.Fatal(err)
	}
	req.AddCookie(&http.Cookie{Name: "id_token", Value: "eyJhbGciOiJSUzI1NiIsImtpZCI6ImtleTEifQ.eyJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjgwODAiLCJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyNDI2MjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"})

	// Create a new recorder
	rr = httptest.NewRecorder()

	// Serve the request
	r.ServeHTTP(rr, req)

	// With a fake token and empty JWKS, expect unauthorized
	if status := rr.Code; status != http.StatusUnauthorized {
		t.Errorf("handler returned wrong status code: got %v want %v",
			status, http.StatusUnauthorized)
	}
}
