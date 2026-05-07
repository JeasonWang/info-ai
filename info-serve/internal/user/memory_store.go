package user

import (
	"context"
	"sort"
	"strconv"
	"sync"
)

type MemoryStore struct {
	mu        sync.Mutex
	favorites map[int64]map[int64]bool
	prefs     map[int64]map[string]string
	history   map[int64][]ReadHistoryItem
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{
		favorites: map[int64]map[int64]bool{},
		prefs:     map[int64]map[string]string{},
		history:   map[int64][]ReadHistoryItem{},
	}
}

func (s *MemoryStore) ListFavoriteEventIDs(ctx context.Context, userID int64) ([]int64, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	result := []int64{}
	for eventID := range s.favorites[userID] {
		result = append(result, eventID)
	}
	sort.Slice(result, func(i int, j int) bool {
		return result[i] > result[j]
	})
	return result, nil
}

func (s *MemoryStore) ListFavoriteEvents(ctx context.Context, userID int64, limit int) ([]FavoriteEventItem, error) {
	ids, err := s.ListFavoriteEventIDs(ctx, userID)
	if err != nil {
		return nil, err
	}
	if len(ids) > limit {
		ids = ids[:limit]
	}
	items := make([]FavoriteEventItem, 0, len(ids))
	for _, id := range ids {
		items = append(items, FavoriteEventItem{
			ID:             id,
			Title:          "收藏事件",
			OneLineSummary: "",
			CategoryName:   "",
			SourceLabel:    "",
			FavoritedAt:    "2026-04-24 00:00:00",
			TargetPath:     "/events/" + strconv.FormatInt(id, 10),
		})
	}
	return items, nil
}

func (s *MemoryStore) AddFavoriteEvent(ctx context.Context, userID int64, eventID int64) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.favorites[userID] == nil {
		s.favorites[userID] = map[int64]bool{}
	}
	s.favorites[userID][eventID] = true
	return nil
}

func (s *MemoryStore) RemoveFavoriteEvent(ctx context.Context, userID int64, eventID int64) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.favorites[userID], eventID)
	return nil
}

func (s *MemoryStore) GetPreference(ctx context.Context, userID int64, key string) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	value, ok := s.prefs[userID][key]
	if !ok {
		return "", ErrPreferenceNotFound
	}
	return value, nil
}

func (s *MemoryStore) SetPreference(ctx context.Context, userID int64, key string, value string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.prefs[userID] == nil {
		s.prefs[userID] = map[string]string{}
	}
	s.prefs[userID][key] = value
	return nil
}

func (s *MemoryStore) ListReadHistory(ctx context.Context, userID int64, limit int) ([]ReadHistoryItem, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	items := s.history[userID]
	if len(items) <= limit {
		result := make([]ReadHistoryItem, len(items))
		copy(result, items)
		return result, nil
	}
	result := make([]ReadHistoryItem, limit)
	copy(result, items[:limit])
	return result, nil
}

func (s *MemoryStore) RecordReadHistory(ctx context.Context, userID int64, eventID *int64, infoID *int64) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	items := s.history[userID]
	filtered := items[:0]
	for _, item := range items {
		if eventID != nil && item.EventID != nil && *item.EventID == *eventID {
			continue
		}
		if infoID != nil && item.InfoID != nil && *item.InfoID == *infoID {
			continue
		}
		filtered = append(filtered, item)
	}

	entry := ReadHistoryItem{ReadAt: "2026-04-24 00:00:00"}
	if eventID != nil {
		entry.ItemType = "event"
		entry.EventID = eventID
		entry.Title = "事件"
		entry.TargetPath = "/events/1"
	} else {
		entry.ItemType = "info"
		entry.InfoID = infoID
		entry.Title = "资讯"
		entry.TargetPath = "/info/1"
	}

	s.history[userID] = append([]ReadHistoryItem{entry}, filtered...)
	return nil
}
