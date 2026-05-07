package transporthttp

import (
	"net/http"
	"net/url"
	"strings"
)

var allowedBrowserOrigins = map[string]bool{
	"http://localhost":      true,
	"http://127.0.0.1":      true,
	"http://localhost:5173": true,
	"http://127.0.0.1:5173": true,
	"http://localhost:5174": true,
	"http://127.0.0.1:5174": true,
	"http://localhost:5175": true,
	"http://127.0.0.1:5175": true,
	"http://localhost:8081": true,
	"http://127.0.0.1:8081": true,
}

// isAllowedBrowserOrigin 允许本地开发端口自动变化，避免 Vite 端口被占用后切到 5176/5177 时触发跨域。
func isAllowedBrowserOrigin(origin string) bool {
	if allowedBrowserOrigins[origin] {
		return true
	}
	parsed, err := url.Parse(origin)
	if err != nil {
		return false
	}
	host := strings.ToLower(parsed.Hostname())
	return parsed.Scheme == "http" && (host == "localhost" || host == "127.0.0.1" || host == "::1")
}

// withCORS 允许本地用户端和管理后台跨端口访问 info-serve。
func withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if isAllowedBrowserOrigin(origin) {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Vary", "Origin")
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Requested-With")
		}
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
