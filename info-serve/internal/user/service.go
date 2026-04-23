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
	AddFavoriteEvent(ctx context.Context, userID int64, eventID int64) error
	RemoveFavoriteEvent(ctx context.Context, userID int64, eventID int64) error
	GetPreference(ctx context.Context, userID int64, key string) (string, error)
	SetPreference(ctx context.Context, userID int64, key string, value string) error
}

type Service struct {
	store Store
}

type HomeFilterPreference struct {
	CategoryCode string `json:"category_code"`
	Sort         string `json:"sort"`
	Keyword      string `json:"keyword"`
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
