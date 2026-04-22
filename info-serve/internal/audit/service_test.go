package audit

import (
	"context"
	"testing"
)

type fakeStore struct {
	records []RecordInput
}

func (s *fakeStore) CreateAuditLog(ctx context.Context, input RecordInput) error {
	s.records = append(s.records, input)
	return nil
}

func TestServiceRecordsAdminAction(t *testing.T) {
	store := &fakeStore{}
	service := NewService(store)

	err := service.Record(context.Background(), RecordInput{
		AdminUserID: 7,
		Action:      "GET /api/admin/overview",
		TargetType:  "admin_api",
		TargetID:    "/api/admin/overview",
		IPAddress:   "127.0.0.1",
	})
	if err != nil {
		t.Fatalf("Record returned error: %v", err)
	}
	if len(store.records) != 1 {
		t.Fatalf("records len = %d, want 1", len(store.records))
	}
	if store.records[0].AdminUserID != 7 {
		t.Fatalf("admin_user_id = %d, want 7", store.records[0].AdminUserID)
	}
}
