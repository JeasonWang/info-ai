package user

import (
	"context"
	"sort"
	"sync"
)

type MemoryStore struct {
	mu        sync.Mutex
	favorites map[int64]map[int64]bool
	prefs     map[int64]map[string]string
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{
		favorites: map[int64]map[int64]bool{},
		prefs:     map[int64]map[string]string{},
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
