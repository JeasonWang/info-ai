package user

import (
	"context"
	"testing"
)

func TestServiceManagesFavoriteEventIDs(t *testing.T) {
	service := NewService(NewMemoryStore())

	if err := service.AddFavoriteEvent(context.Background(), 7, 101); err != nil {
		t.Fatalf("AddFavoriteEvent returned error: %v", err)
	}
	if err := service.AddFavoriteEvent(context.Background(), 7, 202); err != nil {
		t.Fatalf("AddFavoriteEvent returned error: %v", err)
	}

	ids, err := service.ListFavoriteEventIDs(context.Background(), 7)
	if err != nil {
		t.Fatalf("ListFavoriteEventIDs returned error: %v", err)
	}
	if len(ids) != 2 || ids[0] != 202 || ids[1] != 101 {
		t.Fatalf("ids = %+v, want [202 101]", ids)
	}

	if err := service.RemoveFavoriteEvent(context.Background(), 7, 202); err != nil {
		t.Fatalf("RemoveFavoriteEvent returned error: %v", err)
	}
	ids, _ = service.ListFavoriteEventIDs(context.Background(), 7)
	if len(ids) != 1 || ids[0] != 101 {
		t.Fatalf("ids after remove = %+v, want [101]", ids)
	}
}

func TestServiceRejectsInvalidFavoriteInput(t *testing.T) {
	service := NewService(NewMemoryStore())

	if err := service.AddFavoriteEvent(context.Background(), 0, 1); err == nil {
		t.Fatal("AddFavoriteEvent accepted invalid user id")
	}
	if err := service.AddFavoriteEvent(context.Background(), 1, 0); err == nil {
		t.Fatal("AddFavoriteEvent accepted invalid event id")
	}
}
