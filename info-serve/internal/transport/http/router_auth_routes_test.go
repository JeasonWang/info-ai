package transporthttp_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	transporthttp "info-serve/internal/transport/http"
)

func TestHealthRoute(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}

	var body map[string]any
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json response: %v", err)
	}
	if body["code"] != float64(0) {
		t.Fatalf("code = %v, want 0", body["code"])
	}
}

func TestRegisterRejectsInvalidEmail(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	payload := bytes.NewBufferString(`{"email":"not-email","password":"StrongerPass123"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/auth/register", payload)
	req.Header.Set("Content-Type", "application/json")
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusBadRequest)
	}
}

func TestRegisterAcceptsEmailAndPasswordContract(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	payload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/auth/register", payload)
	req.Header.Set("Content-Type", "application/json")
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusCreated {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusCreated)
	}

	var body map[string]any
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json response: %v", err)
	}
	if body["code"] != float64(0) {
		t.Fatalf("code = %v, want 0", body["code"])
	}
}

func TestLoginAndMeUseBearerSession(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	registerPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d, want %d", registerRes.Code, http.StatusCreated)
	}

	loginPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/auth/login", loginPayload)
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	r.ServeHTTP(loginRes, loginReq)
	if loginRes.Code != http.StatusOK {
		t.Fatalf("login status = %d, want %d", loginRes.Code, http.StatusOK)
	}

	var loginBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	if err := json.Unmarshal(loginRes.Body.Bytes(), &loginBody); err != nil {
		t.Fatalf("invalid login json: %v", err)
	}
	if loginBody.Data.Token == "" {
		t.Fatal("login token should not be empty")
	}

	meReq := httptest.NewRequest(http.MethodGet, "/api/me", nil)
	meReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	meRes := httptest.NewRecorder()
	r.ServeHTTP(meRes, meReq)
	if meRes.Code != http.StatusOK {
		t.Fatalf("me status = %d, want %d", meRes.Code, http.StatusOK)
	}
}

func TestUserFavoriteRoutesUseBearerSession(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	registerPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d", registerRes.Code)
	}

	loginPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", loginPayload)
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	r.ServeHTTP(loginRes, loginReq)

	var loginBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	_ = json.Unmarshal(loginRes.Body.Bytes(), &loginBody)

	addReq := httptest.NewRequest(http.MethodPost, "/api/v1/me/favorites", bytes.NewBufferString(`{"event_id":101}`))
	addReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	addReq.Header.Set("Content-Type", "application/json")
	addRes := httptest.NewRecorder()
	r.ServeHTTP(addRes, addReq)
	if addRes.Code != http.StatusOK {
		t.Fatalf("add favorite status = %d, body=%s", addRes.Code, addRes.Body.String())
	}

	listReq := httptest.NewRequest(http.MethodGet, "/api/v1/me/favorites", nil)
	listReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	listRes := httptest.NewRecorder()
	r.ServeHTTP(listRes, listReq)
	if listRes.Code != http.StatusOK {
		t.Fatalf("list favorites status = %d, body=%s", listRes.Code, listRes.Body.String())
	}
	var listBody struct {
		Data struct {
			EventIDs []int64 `json:"event_ids"`
		} `json:"data"`
	}
	if err := json.Unmarshal(listRes.Body.Bytes(), &listBody); err != nil {
		t.Fatalf("invalid favorites json: %v", err)
	}
	if len(listBody.Data.EventIDs) != 1 || listBody.Data.EventIDs[0] != 101 {
		t.Fatalf("favorite ids = %+v", listBody.Data.EventIDs)
	}

	removeReq := httptest.NewRequest(http.MethodDelete, "/api/v1/me/favorites/101", nil)
	removeReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	removeRes := httptest.NewRecorder()
	r.ServeHTTP(removeRes, removeReq)
	if removeRes.Code != http.StatusOK {
		t.Fatalf("remove favorite status = %d, body=%s", removeRes.Code, removeRes.Body.String())
	}
}

func TestUserHomeFilterPreferenceRoutesUseBearerSession(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	registerPayload := bytes.NewBufferString(`{"email":"preference@example.com","password":"StrongerPass123"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d", registerRes.Code)
	}

	loginPayload := bytes.NewBufferString(`{"email":"preference@example.com","password":"StrongerPass123"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", loginPayload)
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	r.ServeHTTP(loginRes, loginReq)

	var loginBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	_ = json.Unmarshal(loginRes.Body.Bytes(), &loginBody)

	saveReq := httptest.NewRequest(http.MethodPut, "/api/v1/me/preferences/home-filter", bytes.NewBufferString(`{"category_code":"sports","sort":"latest","keyword":"NBA"}`))
	saveReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	saveReq.Header.Set("Content-Type", "application/json")
	saveRes := httptest.NewRecorder()
	r.ServeHTTP(saveRes, saveReq)
	if saveRes.Code != http.StatusOK {
		t.Fatalf("save preference status = %d, body=%s", saveRes.Code, saveRes.Body.String())
	}

	getReq := httptest.NewRequest(http.MethodGet, "/api/v1/me/preferences/home-filter", nil)
	getReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	getRes := httptest.NewRecorder()
	r.ServeHTTP(getRes, getReq)
	if getRes.Code != http.StatusOK {
		t.Fatalf("get preference status = %d, body=%s", getRes.Code, getRes.Body.String())
	}

	var getBody struct {
		Data struct {
			CategoryCode string `json:"category_code"`
			Sort         string `json:"sort"`
			Keyword      string `json:"keyword"`
		} `json:"data"`
	}
	if err := json.Unmarshal(getRes.Body.Bytes(), &getBody); err != nil {
		t.Fatalf("invalid preference json: %v", err)
	}
	if getBody.Data.CategoryCode != "sports" || getBody.Data.Sort != "latest" || getBody.Data.Keyword != "NBA" {
		t.Fatalf("home filter preference = %+v", getBody.Data)
	}
}

func TestUserReadHistoryRoutesUseBearerSession(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	registerPayload := bytes.NewBufferString(`{"email":"history@example.com","password":"StrongerPass123"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d", registerRes.Code)
	}

	loginPayload := bytes.NewBufferString(`{"email":"history@example.com","password":"StrongerPass123"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", loginPayload)
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	r.ServeHTTP(loginRes, loginReq)

	var loginBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	_ = json.Unmarshal(loginRes.Body.Bytes(), &loginBody)

	recordEventReq := httptest.NewRequest(http.MethodPost, "/api/v1/me/read-history", bytes.NewBufferString(`{"event_id":101}`))
	recordEventReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	recordEventReq.Header.Set("Content-Type", "application/json")
	recordEventRes := httptest.NewRecorder()
	r.ServeHTTP(recordEventRes, recordEventReq)
	if recordEventRes.Code != http.StatusOK {
		t.Fatalf("record event history status = %d, body=%s", recordEventRes.Code, recordEventRes.Body.String())
	}

	recordInfoReq := httptest.NewRequest(http.MethodPost, "/api/v1/me/read-history", bytes.NewBufferString(`{"info_id":7}`))
	recordInfoReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	recordInfoReq.Header.Set("Content-Type", "application/json")
	recordInfoRes := httptest.NewRecorder()
	r.ServeHTTP(recordInfoRes, recordInfoReq)
	if recordInfoRes.Code != http.StatusOK {
		t.Fatalf("record info history status = %d, body=%s", recordInfoRes.Code, recordInfoRes.Body.String())
	}

	listReq := httptest.NewRequest(http.MethodGet, "/api/v1/me/read-history", nil)
	listReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	listRes := httptest.NewRecorder()
	r.ServeHTTP(listRes, listReq)
	if listRes.Code != http.StatusOK {
		t.Fatalf("list read history status = %d, body=%s", listRes.Code, listRes.Body.String())
	}

	var listBody struct {
		Data []struct {
			ItemType string `json:"item_type"`
			EventID  *int64 `json:"event_id"`
			InfoID   *int64 `json:"info_id"`
		} `json:"data"`
	}
	if err := json.Unmarshal(listRes.Body.Bytes(), &listBody); err != nil {
		t.Fatalf("invalid history json: %v", err)
	}
	if len(listBody.Data) != 2 {
		t.Fatalf("history size = %d, want 2", len(listBody.Data))
	}
	if listBody.Data[0].ItemType != "info" || listBody.Data[0].InfoID == nil || *listBody.Data[0].InfoID != 7 {
		t.Fatalf("first history item = %+v", listBody.Data[0])
	}
	if listBody.Data[1].ItemType != "event" || listBody.Data[1].EventID == nil || *listBody.Data[1].EventID != 101 {
		t.Fatalf("second history item = %+v", listBody.Data[1])
	}
}

func TestAdminHealthRequiresAdminRole(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	registerPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d, want %d", registerRes.Code, http.StatusCreated)
	}

	loginPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/auth/login", loginPayload)
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	r.ServeHTTP(loginRes, loginReq)

	var loginBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	_ = json.Unmarshal(loginRes.Body.Bytes(), &loginBody)

	adminReq := httptest.NewRequest(http.MethodGet, "/api/admin/health", nil)
	adminReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	adminRes := httptest.NewRecorder()
	r.ServeHTTP(adminRes, adminReq)
	if adminRes.Code != http.StatusForbidden {
		t.Fatalf("admin health status = %d, want %d", adminRes.Code, http.StatusForbidden)
	}
}
