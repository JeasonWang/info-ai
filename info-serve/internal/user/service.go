package user

import (
	"context"
	"encoding/json"
	"errors"
)

var ErrInvalidInput = errors.New("参数不合法")
var ErrPreferenceNotFound = errors.New("偏好不存在")

const HomeFilterPreferenceKey = "home_filter"

type Store interface {
	ListFavoriteEventIDs(ctx context.Context, userID int64) ([]int64, error)
	ListFavoriteEvents(ctx context.Context, userID int64, limit int) ([]FavoriteEventItem, error)
	AddFavoriteEvent(ctx context.Context, userID int64, eventID int64) error
	RemoveFavoriteEvent(ctx context.Context, userID int64, eventID int64) error
	GetPreference(ctx context.Context, userID int64, key string) (string, error)
	SetPreference(ctx context.Context, userID int64, key string, value string) error
	ListReadHistory(ctx context.Context, userID int64, limit int) ([]ReadHistoryItem, error)
	RecordReadHistory(ctx context.Context, userID int64, eventID *int64, infoID *int64) error
}

type Service struct {
	store Store
}

type HomeFilterPreference struct {
	CategoryCode string `json:"category_code"`
	Sort         string `json:"sort"`
	Keyword      string `json:"keyword"`
}

type ReadHistoryItem struct {
	ItemType      string `json:"item_type"`
	EventID       *int64 `json:"event_id,omitempty"`
	InfoID        *int64 `json:"info_id,omitempty"`
	Title         string `json:"title"`
	Subtitle      string `json:"subtitle"`
	SourceLabel   string `json:"source_label"`
	ReadAt        string `json:"read_at"`
	TargetPath    string `json:"target_path"`
	PrimaryRemark string `json:"primary_remark"`
}

type FavoriteEventItem struct {
	ID             int64  `json:"id"`
	Title          string `json:"title"`
	OneLineSummary string `json:"one_line_summary"`
	CategoryName   string `json:"category_name"`
	SourceLabel    string `json:"source_label"`
	FavoritedAt    string `json:"favorited_at"`
	TargetPath     string `json:"target_path"`
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

func (s *Service) ListFavoriteEventIDs(ctx context.Context, userID int64) ([]int64, error) {
	if userID < 1 {
		return nil, ErrInvalidInput
	}
	return s.store.ListFavoriteEventIDs(ctx, userID)
}

func (s *Service) ListFavoriteEvents(ctx context.Context, userID int64, limit int) ([]FavoriteEventItem, error) {
	if userID < 1 {
		return nil, ErrInvalidInput
	}
	if limit < 1 {
		limit = 20
	}
	if limit > 50 {
		limit = 50
	}
	return s.store.ListFavoriteEvents(ctx, userID, limit)
}

func (s *Service) AddFavoriteEvent(ctx context.Context, userID int64, eventID int64) error {
	if userID < 1 || eventID < 1 {
		return ErrInvalidInput
	}
	return s.store.AddFavoriteEvent(ctx, userID, eventID)
}

func (s *Service) RemoveFavoriteEvent(ctx context.Context, userID int64, eventID int64) error {
	if userID < 1 || eventID < 1 {
		return ErrInvalidInput
	}
	return s.store.RemoveFavoriteEvent(ctx, userID, eventID)
}

func (s *Service) GetHomeFilterPreference(ctx context.Context, userID int64) (HomeFilterPreference, error) {
	if userID < 1 {
		return HomeFilterPreference{}, ErrInvalidInput
	}

	value, err := s.store.GetPreference(ctx, userID, HomeFilterPreferenceKey)
	if errors.Is(err, ErrPreferenceNotFound) {
		return defaultHomeFilterPreference(), nil
	}
	if err != nil {
		return HomeFilterPreference{}, err
	}

	var preference HomeFilterPreference
	if err := json.Unmarshal([]byte(value), &preference); err != nil {
		return defaultHomeFilterPreference(), nil
	}
	return normalizeHomeFilterPreference(preference), nil
}

func (s *Service) SaveHomeFilterPreference(ctx context.Context, userID int64, preference HomeFilterPreference) (HomeFilterPreference, error) {
	if userID < 1 {
		return HomeFilterPreference{}, ErrInvalidInput
	}

	normalized := normalizeHomeFilterPreference(preference)
	payload, err := json.Marshal(normalized)
	if err != nil {
		return HomeFilterPreference{}, err
	}
	if err := s.store.SetPreference(ctx, userID, HomeFilterPreferenceKey, string(payload)); err != nil {
		return HomeFilterPreference{}, err
	}
	return normalized, nil
}

func defaultHomeFilterPreference() HomeFilterPreference {
	return HomeFilterPreference{CategoryCode: "all", Sort: "composite", Keyword: ""}
}

func normalizeHomeFilterPreference(preference HomeFilterPreference) HomeFilterPreference {
	if preference.CategoryCode == "" {
		preference.CategoryCode = "all"
	}
	if preference.Sort != "latest" {
		preference.Sort = "composite"
	}
	preference.Keyword = truncateRunes(preference.Keyword, 100)
	return preference
}

func truncateRunes(value string, limit int) string {
	runes := []rune(value)
	if len(runes) <= limit {
		return value
	}
	return string(runes[:limit])
}

func (s *Service) ListReadHistory(ctx context.Context, userID int64, limit int) ([]ReadHistoryItem, error) {
	if userID < 1 {
		return nil, ErrInvalidInput
	}
	if limit < 1 {
		limit = 20
	}
	if limit > 50 {
		limit = 50
	}
	return s.store.ListReadHistory(ctx, userID, limit)
}

func (s *Service) RecordReadHistory(ctx context.Context, userID int64, eventID *int64, infoID *int64) error {
	if userID < 1 {
		return ErrInvalidInput
	}
	hasEvent := eventID != nil && *eventID > 0
	hasInfo := infoID != nil && *infoID > 0
	if hasEvent == hasInfo {
		return ErrInvalidInput
	}
	return s.store.RecordReadHistory(ctx, userID, eventID, infoID)
}
