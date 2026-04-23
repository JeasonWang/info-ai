package transporthttp

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"

	"info-serve/internal/auth"
	"info-serve/internal/response"
	"info-serve/internal/user"
)

type UserHandler struct {
	authService *auth.Service
	userService *user.Service
}

type favoriteRequest struct {
	EventID int64 `json:"event_id"`
}

func NewUserHandler(authService *auth.Service, userService *user.Service) *UserHandler {
	return &UserHandler{authService: authService, userService: userService}
}

func (h *UserHandler) FavoriteEventIDs(w http.ResponseWriter, r *http.Request) {
	currentUser, ok := h.currentUser(w, r)
	if !ok {
		return
	}
	ids, err := h.userService.ListFavoriteEventIDs(r.Context(), currentUser.ID)
	if err != nil {
		response.InternalServerError(w, "收藏列表查询失败")
		return
	}
	response.OK(w, map[string][]int64{"event_ids": ids})
}

func (h *UserHandler) AddFavoriteEvent(w http.ResponseWriter, r *http.Request) {
	currentUser, ok := h.currentUser(w, r)
	if !ok {
		return
	}
	var req favoriteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}
	if err := h.userService.AddFavoriteEvent(r.Context(), currentUser.ID, req.EventID); err != nil {
		writeUserError(w, err, "收藏失败")
		return
	}
	response.OK(w, map[string]any{"event_id": req.EventID, "favorited": true})
}

func (h *UserHandler) RemoveFavoriteEvent(w http.ResponseWriter, r *http.Request) {
	currentUser, ok := h.currentUser(w, r)
	if !ok {
		return
	}
	eventID, err := strconv.ParseInt(r.PathValue("event_id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "事件ID不正确")
		return
	}
	if err := h.userService.RemoveFavoriteEvent(r.Context(), currentUser.ID, eventID); err != nil {
		writeUserError(w, err, "取消收藏失败")
		return
	}
	response.OK(w, map[string]any{"event_id": eventID, "favorited": false})
}

func (h *UserHandler) HomeFilterPreference(w http.ResponseWriter, r *http.Request) {
	currentUser, ok := h.currentUser(w, r)
	if !ok {
		return
	}
	preference, err := h.userService.GetHomeFilterPreference(r.Context(), currentUser.ID)
	if err != nil {
		writeUserError(w, err, "筛选偏好查询失败")
		return
	}
	response.OK(w, preference)
}

func (h *UserHandler) SaveHomeFilterPreference(w http.ResponseWriter, r *http.Request) {
	currentUser, ok := h.currentUser(w, r)
	if !ok {
		return
	}
	var req user.HomeFilterPreference
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}
	preference, err := h.userService.SaveHomeFilterPreference(r.Context(), currentUser.ID, req)
	if err != nil {
		writeUserError(w, err, "筛选偏好保存失败")
		return
	}
	response.OK(w, preference)
}

func (h *UserHandler) currentUser(w http.ResponseWriter, r *http.Request) (auth.PublicUser, bool) {
	currentUser, err := h.authService.CurrentUser(r.Context(), bearerToken(r))
	if err != nil {
		response.Unauthorized(w, "请先登录")
		return auth.PublicUser{}, false
	}
	return currentUser, true
}

func writeUserError(w http.ResponseWriter, err error, fallback string) {
	switch {
	case errors.Is(err, user.ErrInvalidInput):
		response.BadRequest(w, "用户参数不合法")
	default:
		response.InternalServerError(w, fallback)
	}
}
