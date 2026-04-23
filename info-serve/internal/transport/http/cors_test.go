package transporthttp

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRouterAllowsBrowserCorsPreflight(t *testing.T) {
	router := NewRouter(Services{})
	req := httptest.NewRequest(http.MethodOptions, "/api/v1/categories", nil)
	req.Header.Set("Origin", "http://127.0.0.1:5173")
	req.Header.Set("Access-Control-Request-Method", http.MethodGet)
	res := httptest.NewRecorder()

	router.ServeHTTP(res, req)

	if res.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusNoContent)
	}
	if res.Header().Get("Access-Control-Allow-Origin") != "http://127.0.0.1:5173" {
		t.Fatalf("allow origin = %q", res.Header().Get("Access-Control-Allow-Origin"))
	}
	if res.Header().Get("Access-Control-Allow-Headers") == "" {
		t.Fatal("expected Access-Control-Allow-Headers")
	}
}

func TestRouterAddsCorsHeadersToAPIResponses(t *testing.T) {
	router := NewRouter(Services{})
	req := httptest.NewRequest(http.MethodGet, "/api/v1/categories", nil)
	req.Header.Set("Origin", "http://localhost:5173")
	res := httptest.NewRecorder()

	router.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
	if res.Header().Get("Access-Control-Allow-Origin") != "http://localhost:5173" {
		t.Fatalf("allow origin = %q", res.Header().Get("Access-Control-Allow-Origin"))
	}
}
