package response

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestErrorHelpersReturnAccurateStatusCodes(t *testing.T) {
	cases := []struct {
		name       string
		write      func(http.ResponseWriter, string)
		wantStatus int
		wantCode   int
	}{
		{name: "not found", write: NotFound, wantStatus: http.StatusNotFound, wantCode: 404},
		{name: "internal server error", write: InternalServerError, wantStatus: http.StatusInternalServerError, wantCode: 500},
	}

	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			res := httptest.NewRecorder()

			item.write(res, "出错了")

			if res.Code != item.wantStatus {
				t.Fatalf("status = %d, want %d", res.Code, item.wantStatus)
			}
			var body Body
			if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
				t.Fatalf("invalid json: %v", err)
			}
			if body.Code != item.wantCode || body.Message != "出错了" {
				t.Fatalf("body = %+v", body)
			}
		})
	}
}
