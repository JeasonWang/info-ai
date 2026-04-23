package transporthttp_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"info-serve/internal/content"
	transporthttp "info-serve/internal/transport/http"
)

type stubContentStore struct{}

func (s stubContentStore) ListCategories(ctx context.Context) ([]content.Category, error) {
	return []content.Category{{ID: 1, Name: "科技", Code: "tech", Description: "科技热点"}}, nil
}

func (s stubContentStore) ListChannels(ctx context.Context, categoryID int64) ([]content.Channel, error) {
	return []content.Channel{{ID: 2, Name: "CSDN", Code: "csdn", CategoryID: categoryID, CategoryName: "科技", IsActive: 1}}, nil
}

func (s stubContentStore) ListInfos(ctx context.Context, params content.ListInfoParams) (content.InfoPage, error) {
	return content.InfoPage{
		Total:    1,
		Page:     params.Page,
		PageSize: params.PageSize,
		Items:    []content.InfoItem{{ID: 7, Title: "OpenAI 发布开发者工具更新", CategoryName: "科技"}},
	}, nil
}

func (s stubContentStore) GetInfoDetail(ctx context.Context, id int64) (content.InfoItem, error) {
	return content.InfoItem{
		ID:                id,
		Title:             "OpenAI 发布开发者工具更新",
		Content:           "开发者工具更新详情。",
		CategoryID:        1,
		CategoryName:      "科技",
		ChannelID:         2,
		ChannelName:       "CSDN",
		SourceURL:         "https://example.com/openai",
		DetailFetchStatus: "complete",
		DetailScore:       92,
		TechEntities:      []string{"OpenAI"},
		TechKeywords:      []string{"API"},
	}, nil
}

func (s stubContentStore) GetStats(ctx context.Context) (content.Stats, error) {
	return content.Stats{Total: 12, Categories: []content.CategoryStats{{Name: "科技", Count: 5}}}, nil
}

func TestV1ContentRoutesReturnUserFacingData(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{
		Content: content.NewService(stubContentStore{}),
	})

	cases := []struct {
		path string
		key  string
	}{
		{path: "/api/v1/categories", key: "code"},
		{path: "/api/v1/channels?category_id=1", key: "category_name"},
		{path: "/api/v1/infos?category_id=1&page=2&page_size=5", key: "items"},
		{path: "/api/v1/infos/7", key: "title"},
		{path: "/api/v1/stats", key: "total"},
	}

	for _, item := range cases {
		req := httptest.NewRequest(http.MethodGet, item.path, nil)
		res := httptest.NewRecorder()
		r.ServeHTTP(res, req)
		if res.Code != http.StatusOK {
			t.Fatalf("%s status = %d, want %d, body=%s", item.path, res.Code, http.StatusOK, res.Body.String())
		}
		var body struct {
			Data any `json:"data"`
		}
		if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
			t.Fatalf("invalid json for %s: %v", item.path, err)
		}
		if body.Data == nil {
			t.Fatalf("%s missing data key %s", item.path, item.key)
		}
	}
}
