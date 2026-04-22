package handler

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"info-serve/internal/auth"
	"info-serve/internal/response"
)

// RegisterRequest 是邮箱注册接口的请求参数。
type RegisterRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

// RegisterResponse 是注册接口第一阶段返回给前端的用户摘要。
type RegisterResponse struct {
	Email string `json:"email"`
	Role  string `json:"role"`
}

// AuthHandler 承载鉴权相关 HTTP 接口。
type AuthHandler struct {
	service *auth.Service
}

func NewAuthHandler(service *auth.Service) *AuthHandler {
	return &AuthHandler{service: service}
}

// Register 完成邮箱注册，并通过服务层写入用户存储。
func (h *AuthHandler) Register(w http.ResponseWriter, r *http.Request) {
	var req RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}

	user, err := h.service.Register(r.Context(), auth.RegisterInput{
		Email:    req.Email,
		Password: req.Password,
	})
	if errors.Is(err, auth.ErrEmailAlreadyExists) {
		response.Conflict(w, "邮箱已注册")
		return
	}
	if errors.Is(err, auth.ErrInvalidInput) {
		response.BadRequest(w, "邮箱格式不正确")
		return
	}
	if err != nil {
		response.InternalServerError(w, "注册失败")
		return
	}

	response.Created(w, user)
}

// Login 完成邮箱密码登录，并返回会话 token。
func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var req RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}

	result, err := h.service.Login(r.Context(), auth.LoginInput{
		Email:    req.Email,
		Password: req.Password,
	})
	if errors.Is(err, auth.ErrInvalidCredentials) {
		response.Unauthorized(w, "邮箱或密码错误")
		return
	}
	if err != nil {
		response.InternalServerError(w, "登录失败")
		return
	}
	response.OK(w, result)
}

// Me 返回当前登录用户。
func (h *AuthHandler) Me(w http.ResponseWriter, r *http.Request) {
	user, err := h.service.CurrentUser(r.Context(), bearerToken(r))
	if err != nil {
		response.Unauthorized(w, "请先登录")
		return
	}
	response.OK(w, user)
}

// Logout 注销当前会话。
func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	if err := h.service.Logout(r.Context(), bearerToken(r)); err != nil {
		response.Unauthorized(w, "请先登录")
		return
	}
	response.OK(w, map[string]bool{"revoked": true})
}

func bearerToken(r *http.Request) string {
	header := strings.TrimSpace(r.Header.Get("Authorization"))
	if !strings.HasPrefix(header, "Bearer ") {
		return ""
	}
	return strings.TrimSpace(strings.TrimPrefix(header, "Bearer "))
}
