package user

import (
	"context"
	"strings"
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

func TestServiceManagesHomeFilterPreference(t *testing.T) {
	service := NewService(NewMemoryStore())

	defaultPreference, err := service.GetHomeFilterPreference(context.Background(), 7)
	if err != nil {
		t.Fatalf("GetHomeFilterPreference returned error: %v", err)
	}
	if defaultPreference.CategoryCode != "all" || defaultPreference.Sort != "composite" || defaultPreference.Keyword != "" {
		t.Fatalf("default preference = %+v", defaultPreference)
	}

	saved, err := service.SaveHomeFilterPreference(context.Background(), 7, HomeFilterPreference{
		CategoryCode: "sports",
		Sort:         "latest",
		Keyword:      "NBA",
	})
	if err != nil {
		t.Fatalf("SaveHomeFilterPreference returned error: %v", err)
	}
	if saved.CategoryCode != "sports" || saved.Sort != "latest" || saved.Keyword != "NBA" {
		t.Fatalf("saved preference = %+v", saved)
	}

	loaded, err := service.GetHomeFilterPreference(context.Background(), 7)
	if err != nil {
		t.Fatalf("GetHomeFilterPreference after save returned error: %v", err)
	}
	if loaded != saved {
		t.Fatalf("loaded preference = %+v, want %+v", loaded, saved)
	}
}

func TestServiceTruncatesHomeFilterKeywordByCharacters(t *testing.T) {
	service := NewService(NewMemoryStore())
	longKeyword := strings.Repeat("人工智能", 40)

	saved, err := service.SaveHomeFilterPreference(context.Background(), 7, HomeFilterPreference{
		CategoryCode: "tech",
		Sort:         "latest",
		Keyword:      longKeyword,
	})
	if err != nil {
		t.Fatalf("SaveHomeFilterPreference returned error: %v", err)
	}
	if len([]rune(saved.Keyword)) != 100 {
		t.Fatalf("keyword length = %d, want 100", len([]rune(saved.Keyword)))
	}
}
