package user

import (
	"context"
	"errors"
)

var ErrInvalidInput = errors.New("参数不合法")

type Store interface {
	ListFavoriteEventIDs(ctx context.Context, userID int64) ([]int64, error)
	AddFavoriteEvent(ctx context.Context, userID int64, eventID int64) error
	RemoveFavoriteEvent(ctx context.Context, userID int64, eventID int64) error
}

type Service struct {
	store Store
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
