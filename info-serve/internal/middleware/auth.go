package middleware

import (
	"net/http"
	"strings"

	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/response"
)

// RequireAdmin 强制管理接口必须由管理员或运营角色访问。
func RequireAdmin(service *auth.Service, next http.HandlerFunc) http.HandlerFunc {
	return RequireAdminWithAudit(service, nil, next)
}

// RequireAdminWithAudit 强制管理鉴权，并在通过鉴权后写入操作审计。
func RequireAdminWithAudit(service *auth.Service, auditService *audit.Service, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := service.CurrentUser(r.Context(), bearerToken(r))
		if err != nil {
			response.Unauthorized(w, "请先登录")
			return
		}
		if user.Role != "admin" && user.Role != "operator" {
			response.Forbidden(w, "没有管理权限")
			return
		}
		_ = auditService.Record(r.Context(), audit.RecordInput{
			AdminUserID: user.ID,
			Action:      r.Method + " " + r.URL.Path,
			TargetType:  "admin_api",
			TargetID:    r.URL.Path,
			IPAddress:   clientIP(r),
		})
		next(w, r)
	}
}

func bearerToken(r *http.Request) string {
	header := strings.TrimSpace(r.Header.Get("Authorization"))
	if !strings.HasPrefix(header, "Bearer ") {
		return ""
	}
	return strings.TrimSpace(strings.TrimPrefix(header, "Bearer "))
}

func clientIP(r *http.Request) string {
	forwarded := strings.TrimSpace(r.Header.Get("X-Forwarded-For"))
	if forwarded != "" {
		return strings.TrimSpace(strings.Split(forwarded, ",")[0])
	}
	return r.RemoteAddr
}
