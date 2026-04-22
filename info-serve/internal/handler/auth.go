package handler

import (
	"encoding/json"
	"net/http"
	"net/mail"
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

// Register 完成邮箱和密码的基础校验，并返回稳定接口契约。
//
// 当前阶段暂不写库，后续接入 user_account 表时复用相同校验逻辑。
func Register(w http.ResponseWriter, r *http.Request) {
	var req RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}

	email := strings.ToLower(strings.TrimSpace(req.Email))
	if _, err := mail.ParseAddress(email); err != nil {
		response.BadRequest(w, "邮箱格式不正确")
		return
	}
	if len(req.Password) < 8 {
		response.BadRequest(w, "密码长度至少8位")
		return
	}
	if _, err := auth.HashPassword(req.Password); err != nil {
		response.BadRequest(w, "密码处理失败")
		return
	}

	response.Created(w, RegisterResponse{Email: email, Role: "user"})
}
