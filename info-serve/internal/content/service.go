package content

import (
	"context"
	"strings"
)

// Store 瀹氫箟鐢ㄦ埛渚у唴瀹硅鍙栨墍闇€鐨勬暟鎹闂兘鍔涖€?
type Store interface {
 	ListCategories(ctx context.Context) ([]Category, error)
 	ListChannels(ctx context.Context, categoryID int64) ([]Channel, error)
 	ListInfos(ctx context.Context, params ListInfoParams) (InfoPage, error)
 	GetInfoDetail(ctx context.Context, id int64) (InfoItem, error)
 	GetStats(ctx context.Context) (Stats, error)
 	GetDailyBriefs(ctx context.Context, limit int, offset int) (DailyBriefPage, error)
 	GetDailyBriefByDate(ctx context.Context, date string) (DailyBriefItem, error)
}

// Service 灏佽鐢ㄦ埛渚у唴瀹硅鍙栬鍒欍€?
type Service struct {
	store Store
}

type Category struct {
	ID          int64  `json:"id"`
	Name        string `json:"name"`
	Code        string `json:"code"`
	Description string `json:"description"`
	CreatedAt   string `json:"created_at"`
	UpdatedAt   string `json:"updated_at"`
}

type Channel struct {
	ID            int64  `json:"id"`
	Name          string `json:"name"`
	Code          string `json:"code"`
	BaseURL       string `json:"base_url"`
	CategoryID    int64  `json:"category_id"`
	CategoryName  string `json:"category_name"`
	CrawlInterval int    `json:"crawl_interval"`
	IsActive      int    `json:"is_active"`
	CreatedAt     string `json:"created_at"`
	UpdatedAt     string `json:"updated_at"`
}

type InfoItem struct {
	ID                  int64    `json:"id"`
	Title               string   `json:"title"`
	Content             string   `json:"content"`
	CategoryID          int64    `json:"category_id"`
	CategoryName        string   `json:"category_name"`
	ChannelID           int64    `json:"channel_id"`
	ChannelName         string   `json:"channel_name"`
	SourceID            string   `json:"source_id"`
	SourceURL           string   `json:"source_url"`
	EventTime           string   `json:"event_time"`
	CoreEntity          string   `json:"core_entity"`
	Location            string   `json:"location"`
	IndicatorName       string   `json:"indicator_name"`
	IndicatorValue      string   `json:"indicator_value"`
	DetailFetchStatus   string   `json:"detail_fetch_status"`
	DetailFetchError    string   `json:"detail_fetch_error"`
	DetailStrategy      string   `json:"detail_strategy"`
	DetailScore         int      `json:"detail_score"`
	DetailContentLength int      `json:"detail_content_length"`
	DetailFetchedAt     string   `json:"detail_fetched_at"`
	QualityLevel        string   `json:"quality_level"`
	QualitySummary      string   `json:"quality_summary"`
	NeedsAttention      bool     `json:"needs_attention"`
	AttentionPriority   int      `json:"attention_priority"`
	TechTopicType       string   `json:"tech_topic_type"`
	TechEntities        []string `json:"tech_entities"`
	TechKeywords        []string `json:"tech_keywords"`
	CreatedAt           string   `json:"created_at"`
	UpdatedAt           string   `json:"updated_at"`
}

type ListInfoParams struct {
	CategoryID int64
	ChannelID  int64
	Keyword    string
	Page       int
	PageSize   int
}

type InfoPage struct {
	Total    int        `json:"total"`
	Page     int        `json:"page"`
	PageSize int        `json:"page_size"`
	Items    []InfoItem `json:"items"`
}

type Stats struct {
	Total      int             `json:"total"`
	Categories []CategoryStats `json:"categories"`
}

type CategoryStats struct {
	Name  string `json:"name"`
	Count int    `json:"count"`
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

func (s *Service) ListCategories(ctx context.Context) ([]Category, error) {
	return s.store.ListCategories(ctx)
}

func (s *Service) ListChannels(ctx context.Context, categoryID int64) ([]Channel, error) {
	if categoryID < 0 {
		categoryID = 0
	}
	return s.store.ListChannels(ctx, categoryID)
}

func (s *Service) ListInfos(ctx context.Context, params ListInfoParams) (InfoPage, error) {
	if params.CategoryID < 0 {
		params.CategoryID = 0
	}
	if params.ChannelID < 0 {
		params.ChannelID = 0
	}
	params.Keyword = strings.TrimSpace(params.Keyword)
	if params.Page < 1 {
		params.Page = 1
	}
	if params.PageSize < 1 {
		params.PageSize = 10
	}
	if params.PageSize > 50 {
		params.PageSize = 50
	}
	return s.store.ListInfos(ctx, params)
}

func (s *Service) GetInfoDetail(ctx context.Context, id int64) (InfoItem, error) {
	return s.store.GetInfoDetail(ctx, id)
}

func ApplyInfoQuality(item *InfoItem) {
	contentLength := item.DetailContentLength
	if contentLength == 0 {
		contentLength = len([]rune(strings.TrimSpace(item.Content)))
	}
	status := strings.TrimSpace(item.DetailFetchStatus)

	switch {
	case status == "complete" && item.DetailScore >= 80 && contentLength >= 120:
		item.QualityLevel = "excellent"
		item.QualitySummary = "璇︽儏瀹屾暣搴﹂珮锛屽彲浣滀负浜嬩欢鍒嗘瀽鐨勬牳蹇冩潵婧愩€?
		item.NeedsAttention = false
		item.AttentionPriority = 0
	case status == "complete" && item.DetailScore >= 60 && contentLength >= 80:
		item.QualityLevel = "usable"
		item.QualitySummary = "璇︽儏鍙敤锛屼絾浠嶅缓璁户缁瀵熸洿澶氭潵婧愩€?
		item.NeedsAttention = false
		item.AttentionPriority = 0
	case status == "failed" || status == "list_only" || status == "pending" || item.DetailScore < 60 || contentLength < 80:
		item.QualityLevel = "weak"
		item.QualitySummary = "璇︽儏璐ㄩ噺鍋忓急锛岀郴缁熼渶瑕佺户缁ˉ鍋挎姄鍙栥€?
		item.NeedsAttention = true
		item.AttentionPriority = infoAttentionPriority(status, item.DetailScore, contentLength)
	default:
		item.QualityLevel = "usable"
		item.QualitySummary = "璇︽儏鍩烘湰鍙敤锛屽悗缁細闅忔柊澧炴潵婧愮户缁牎鍑嗐€?
		item.NeedsAttention = false
		item.AttentionPriority = 0
	}
}

func infoAttentionPriority(status string, detailScore int, contentLength int) int {
	switch {
	case status == "failed":
		return 88
	case status == "list_only":
		return 84
	case status == "pending":
		return 70
	case contentLength == 0:
		return 90
	case contentLength < 80:
		return 76
	case detailScore < 60:
		return 68
	default:
		return 50
	}
}

func (s *Service) GetStats(ctx context.Context) (Stats, error) {
	return s.store.GetStats(ctx)
}

func SplitCSV(raw string) []string {
	items := []string{}
	for _, part := range strings.Split(raw, ",") {
		value := strings.TrimSpace(part)
		if value != "" {
			items = append(items, value)
		}
	}
	return items
}
type DailyBriefItem struct {
	ID        int64  `json:"id"`
	BriefDate string `json:"brief_date"`
	Headline  string `json:"headline"`
	Summary   string `json:"summary"`
	Content   string `json:"content"`
	Status    string `json:"status"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

type DailyBriefPage struct {
	Total int              `json:"total"`
	Items []DailyBriefItem `json:"items"`
}

func (s *Service) DailyBriefs(ctx context.Context, limit int, offset int) (DailyBriefPage, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	if offset < 0 {
		offset = 0
	}
	return s.store.GetDailyBriefs(ctx, limit, offset)
}

func (s *Service) DailyBriefByDate(ctx context.Context, date string) (DailyBriefItem, error) {
	return s.store.GetDailyBriefByDate(ctx, date)
}
