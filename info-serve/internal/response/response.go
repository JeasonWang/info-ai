package response

import (
	"encoding/json"
	"net/http"
)

// Body 是 info-serve 对外 API 的统一响应结构。
type Body struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// JSON 写入统一 JSON 响应。
func JSON(w http.ResponseWriter, statusCode int, body Body) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(body)
}

// OK 写入成功响应。
func OK(w http.ResponseWriter, data interface{}) {
	JSON(w, http.StatusOK, Body{Code: 0, Message: "success", Data: data})
}

// Created 写入创建成功响应。
func Created(w http.ResponseWriter, data interface{}) {
	JSON(w, http.StatusCreated, Body{Code: 0, Message: "success", Data: data})
}

// BadRequest 写入参数错误响应。
func BadRequest(w http.ResponseWriter, message string) {
	JSON(w, http.StatusBadRequest, Body{Code: 400, Message: message})
}

func Unauthorized(w http.ResponseWriter, message string) {
	JSON(w, http.StatusUnauthorized, Body{Code: 401, Message: message})
}

func Forbidden(w http.ResponseWriter, message string) {
	JSON(w, http.StatusForbidden, Body{Code: 403, Message: message})
}

func Conflict(w http.ResponseWriter, message string) {
	JSON(w, http.StatusConflict, Body{Code: 409, Message: message})
}
