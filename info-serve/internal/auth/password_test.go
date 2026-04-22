package auth

import "testing"

func TestPasswordHashCanBeVerified(t *testing.T) {
	hash, err := HashPassword("StrongerPass123")
	if err != nil {
		t.Fatalf("HashPassword returned error: %v", err)
	}

	if hash == "StrongerPass123" {
		t.Fatal("password hash must not equal plain password")
	}
	if !CheckPasswordHash("StrongerPass123", hash) {
		t.Fatal("expected password to verify")
	}
	if CheckPasswordHash("wrong-password", hash) {
		t.Fatal("wrong password should not verify")
	}
}
