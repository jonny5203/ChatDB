package main

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"

	"github.com/coreos/go-oidc/v3/oidc"
	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
	"golang.org/x/oauth2"
)

type Route struct {
	Path          string `json:"path"`
	DownstreamURL string `json:"downstream_url"`
}

func authMiddleware(verifier *oidc.IDTokenVerifier) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			cookie, err := r.Cookie("id_token")
			if err != nil {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			if _, err := verifier.Verify(r.Context(), cookie.Value); err != nil {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func main() {
	_ = godotenv.Load()
	r, err := createRouter("")
	if err != nil {
		log.Fatal(err)
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Fatal(http.ListenAndServe(":"+port, r))
}

func createRouter(routesPath string) (http.Handler, error) {
	if routesPath == "" {
		routesPath = "./routes.json"
	}

	ctx := context.Background()
	clientID := os.Getenv("OIDC_CLIENT_ID")
	clientSecret := os.Getenv("OIDC_CLIENT_SECRET")
	providerURL := os.Getenv("OIDC_PROVIDER_URL")

	provider, err := oidc.NewProvider(ctx, providerURL)
	if err != nil {
		return nil, fmt.Errorf("failed to create OIDC provider: %w", err)
	}

	verifier := provider.Verifier(&oidc.Config{ClientID: clientID})

	oauth2Config := oauth2.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		RedirectURL:  "http://localhost:8080/callback",
		Endpoint:     provider.Endpoint(),
		Scopes:       []string{oidc.ScopeOpenID, "profile", "email"},
	}

	b, err := ioutil.ReadFile(routesPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read routes file: %w", err)
	}

	var routes []Route
	if err := json.Unmarshal(b, &routes); err != nil {
		return nil, fmt.Errorf("failed to unmarshal routes: %w", err)
	}

	r := mux.NewRouter()
	auth := authMiddleware(verifier)

	for _, route := range routes {
		downstreamURL, err := url.Parse(route.DownstreamURL)
		if err != nil {
			return nil, fmt.Errorf("failed to parse downstream URL: %w", err)
		}
		proxy := httputil.NewSingleHostReverseProxy(downstreamURL)
		if route.Path == "/mock" {
			r.Handle(route.Path, auth(proxy))
		} else {
			r.Handle(route.Path, proxy)
		}
	}

	r.HandleFunc("/login", func(w http.ResponseWriter, r *http.Request) {
		b := make([]byte, 32)
		if _, err := rand.Read(b); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		state := base64.StdEncoding.EncodeToString(b)
		http.SetCookie(w, &http.Cookie{Name: "state", Value: state, HttpOnly: true})
		http.Redirect(w, r, oauth2Config.AuthCodeURL(state), http.StatusFound)
	})

	r.HandleFunc("/callback", func(w http.ResponseWriter, r *http.Request) {
		state, err := r.Cookie("state")
		if err != nil {
			http.Error(w, "state not found", http.StatusBadRequest)
			return
		}
		if r.URL.Query().Get("state") != state.Value {
			http.Error(w, "state did not match", http.StatusBadRequest)
			return
		}
		oauth2Token, err := oauth2Config.Exchange(ctx, r.URL.Query().Get("code"))
		if err != nil {
			http.Error(w, "Failed to exchange token: "+err.Error(), http.StatusInternalServerError)
			return
		}
		rawIDToken, ok := oauth2Token.Extra("id_token").(string)
		if !ok {
			http.Error(w, "No id_token field in oauth2 token.", http.StatusInternalServerError)
			return
		}
		if _, err = verifier.Verify(ctx, rawIDToken); err != nil {
			http.Error(w, "Failed to verify ID Token: "+err.Error(), http.StatusInternalServerError)
			return
		}
		http.SetCookie(w, &http.Cookie{Name: "id_token", Value: rawIDToken, HttpOnly: true})
		http.Redirect(w, r, "/", http.StatusFound)
	})

	return r, nil
}
