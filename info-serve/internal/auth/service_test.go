package auth

import (
	"context"
	"errors"
	"testing"
)

type fakeStore struct {
	nextID      int64
	usersByMail map[string]User
	sessions    map[string]User
	revoked     map[string]bool
}

func newFakeStore() *fakeStore {
	return &fakeStore{
		nextID:      1,
		usersByMail: map[string]User{},
		sessions:    map[string]User{},
		revoked:     map[string]bool{},
	}
}

func (s *fakeStore) CreateUser(ctx context.Context, params CreateUserParams) (User, error) {
	if _, exists := s.usersByMail[params.Email]; exists {
		return User{}, ErrEmailAlreadyExists
	}
	user := User{
		ID:           s.nextID,
		Email:        params.Email,
		PasswordHash: params.PasswordHash,
		Role:         params.Role,
		Status:       "active",
	}
	s.nextID++
	s.usersByMail[user.Email] = user
	return user, nil
}

func (s *fakeStore) FindUserByEmail(ctx context.Context, email string) (User, error) {
	user, exists := s.usersByMail[email]
	if !exists {
		return User{}, ErrUserNotFound
	}
	return user, nil
}

func (s *fakeStore) CreateSession(ctx context.Context, params CreateSessionParams) error {
	user, exists := s.usersByMail[params.Email]
	if !exists {
		return ErrUserNotFound
	}
	s.sessions[params.TokenHash] = user
	return nil
}

func (s *fakeStore) FindUserBySessionTokenHash(ctx context.Context, tokenHash string) (User, error) {
	if s.revoked[tokenHash] {
		return User{}, ErrSessionNotFound
	}
	user, exists := s.sessions[tokenHash]
	if !exists {
		return User{}, ErrSessionNotFound
	}
	return user, nil
}

func (s *fakeStore) RevokeSession(ctx context.Context, tokenHash string) error {
	if _, exists := s.sessions[tokenHash]; !exists {
		return ErrSessionNotFound
	}
	s.revoked[tokenHash] = true
	return nil
}

func TestServiceRegisterNormalizesEmailAndRejectsDuplicate(t *testing.T) {
	service := NewService(newFakeStore())

	user, err := service.Register(context.Background(), RegisterInput{
		Email:    " USER@Example.COM ",
		Password: "StrongerPass123",
	})
	if err != nil {
		t.Fatalf("Register returned error: %v", err)
	}
	if user.Email != "user@example.com" {
		t.Fatalf("email = %q, want normalized user@example.com", user.Email)
	}
	if user.Role != "user" {
		t.Fatalf("role = %q, want user", user.Role)
	}

	_, err = service.Register(context.Background(), RegisterInput{
		Email:    "user@example.com",
		Password: "AnotherPass123",
	})
	if !errors.Is(err, ErrEmailAlreadyExists) {
		t.Fatalf("duplicate register error = %v, want ErrEmailAlreadyExists", err)
	}
}

func TestServiceLoginCreatesTokenAndCurrentUserCanReadIt(t *testing.T) {
	store := newFakeStore()
	service := NewService(store)
	registered, err := service.Register(context.Background(), RegisterInput{
		Email:    "user@example.com",
		Password: "StrongerPass123",
	})
	if err != nil {
		t.Fatalf("Register returned error: %v", err)
	}

	login, err := service.Login(context.Background(), LoginInput{
		Email:    "user@example.com",
		Password: "StrongerPass123",
	})
	if err != nil {
		t.Fatalf("Login returned error: %v", err)
	}
	if login.Token == "" {
		t.Fatal("login token should not be empty")
	}
	if login.User.ID != registered.ID {
		t.Fatalf("login user id = %d, want %d", login.User.ID, registered.ID)
	}

	current, err := service.CurrentUser(context.Background(), login.Token)
	if err != nil {
		t.Fatalf("CurrentUser returned error: %v", err)
	}
	if current.Email != "user@example.com" {
		t.Fatalf("current email = %q", current.Email)
	}
}

func TestServiceRejectsWrongPassword(t *testing.T) {
	service := NewService(newFakeStore())
	_, err := service.Register(context.Background(), RegisterInput{
		Email:    "user@example.com",
		Password: "StrongerPass123",
	})
	if err != nil {
		t.Fatalf("Register returned error: %v", err)
	}

	_, err = service.Login(context.Background(), LoginInput{
		Email:    "user@example.com",
		Password: "wrong-password",
	})
	if !errors.Is(err, ErrInvalidCredentials) {
		t.Fatalf("wrong password error = %v, want ErrInvalidCredentials", err)
	}
}
