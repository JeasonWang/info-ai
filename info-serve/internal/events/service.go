package events

import (
	"context"
	"strings"
)

// Store 定义事件读取所需的数据访问能力。
type Store interface {
	ListEvents(ctx context.Context, params ListEventsParams) (EventPage, error)
	GetEventDetail(ctx context.Context, id int64) (EventDetail, error)
}

// Service 封装用户侧事件读取规则。
type Service struct {
	store Store
}

type ListEventsParams struct {
	CategoryCode string
	ChannelCode  string
	Keyword      string
	Sort         string
	Page         int
	PageSize     int
}

type EventCategory struct {
	Code         string `json:"code"`
	Name         string `json:"name"`
	DisplayOrder int    `json:"display_order"`
}

type CategoryBrief struct {
	Code string `json:"code"`
	Name string `json:"name"`
}

type EventListItem struct {
	ID                   int64         `json:"id"`
	RepresentativeInfoID *int64        `json:"representative_info_id"`
	Title                string        `json:"title"`
	OneLineSummary       string        `json:"one_line_summary"`
	PrimaryCategory      CategoryBrief `json:"primary_category"`
	HeatScore            int           `json:"heat_score"`
	FreshnessScore       int           `json:"freshness_score"`
	CompositeScore       int           `json:"composite_score"`
	LastUpdatedAt        string        `json:"last_updated_at"`
	SourceCount          int           `json:"source_count"`
	SourceBadges         []string      `json:"source_badges"`
	NewUpdateCount       int           `json:"new_update_count"`
}

type EventPage struct {
	Total    int             `json:"total"`
	Page     int             `json:"page"`
	PageSize int             `json:"page_size"`
	Items    []EventListItem `json:"items"`
}

type EventCore struct {
	ID              int64         `json:"id"`
	Title           string        `json:"title"`
	OneLineSummary  string        `json:"one_line_summary"`
	PrimaryCategory CategoryBrief `json:"primary_category"`
	HeatScore       int           `json:"heat_score"`
	FreshnessScore  int           `json:"freshness_score"`
	CompositeScore  int           `json:"composite_score"`
	SourceCount     int           `json:"source_count"`
	LastUpdatedAt   string        `json:"last_updated_at"`
}

type TimelineItem struct {
	ID         int64   `json:"id"`
	OccurredAt string  `json:"occurred_at"`
	Summary    string  `json:"summary"`
	Confidence float64 `json:"confidence"`
}

type SourceView struct {
	ChannelName string `json:"channel_name"`
	Summary     string `json:"summary"`
}

type RepresentativeSource struct {
	InfoID      int64  `json:"info_id"`
	Title       string `json:"title"`
	ChannelName string `json:"channel_name"`
	SourceURL   string `json:"source_url"`
	EventTime   string `json:"event_time"`
}

type TechTopic struct {
	TopicType string `json:"topic_type"`
	Count     int    `json:"count"`
}

type TechContext struct {
	Topics   []TechTopic `json:"topics"`
	Entities []string    `json:"entities"`
	Keywords []string    `json:"keywords"`
}

type EventDetail struct {
	Event                 EventCore              `json:"event"`
	Timeline              []TimelineItem         `json:"timeline"`
	Summaries             map[string]string      `json:"summaries"`
	SourceViews           []SourceView           `json:"source_views"`
	RepresentativeSources []RepresentativeSource `json:"representative_sources"`
	TechContext           TechContext            `json:"tech_context"`
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

func EventCategories() []EventCategory {
	return []EventCategory{
		{Code: "all", Name: "全网", DisplayOrder: 0},
		{Code: "tech", Name: "科技", DisplayOrder: 1},
		{Code: "economy", Name: "财经", DisplayOrder: 2},
		{Code: "sports", Name: "体育", DisplayOrder: 3},
		{Code: "international", Name: "国际", DisplayOrder: 4},
	}
}

func (s *Service) ListEvents(ctx context.Context, params ListEventsParams) (EventPage, error) {
	params.CategoryCode = strings.TrimSpace(params.CategoryCode)
	if params.CategoryCode == "" {
		params.CategoryCode = "all"
	}
	params.ChannelCode = strings.TrimSpace(params.ChannelCode)
	params.Sort = strings.TrimSpace(params.Sort)
	if params.Sort != "latest" {
		params.Sort = "composite"
	}
	if params.Page < 1 {
		params.Page = 1
	}
	if params.PageSize < 1 {
		params.PageSize = 10
	}
	if params.PageSize > 50 {
		params.PageSize = 50
	}
	page, err := s.store.ListEvents(ctx, params)
	if err != nil {
		return EventPage{}, err
	}
	for index := range page.Items {
		if page.Items[index].SourceBadges == nil {
			page.Items[index].SourceBadges = []string{}
		}
	}
	return page, nil
}

func (s *Service) GetEventDetail(ctx context.Context, id int64) (EventDetail, error) {
	return s.store.GetEventDetail(ctx, id)
}
