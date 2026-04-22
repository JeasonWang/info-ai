package auth

import (
	"context"
	"sync"
)

// MemoryStore 是本地开发和路由测试使用的内存存储。
//
// 正式运行时会替换为 MySQL 存储；保留该实现可以让接口测试不依赖数据库。
type MemoryStore struct {
	mu          sync.Mutex
	nextID      int64
	usersByMail map[string]User
	sessions    map[string]User
	revoked     map[string]bool
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{
		nextID:      1,
		usersByMail: map[string]User{},
		sessions:    map[string]User{},
		revoked:     map[string]bool{},
	}
}

func (s *MemoryStore) CreateUser(ctx context.Context, params CreateUserParams) (User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
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

func (s *MemoryStore) FindUserByEmail(ctx context.Context, email string) (User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	user, exists := s.usersByMail[email]
	if !exists {
		return User{}, ErrUserNotFound
	}
	return user, nil
}

func (s *MemoryStore) CreateSession(ctx context.Context, params CreateSessionParams) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	user, exists := s.usersByMail[params.Email]
	if !exists {
		return ErrUserNotFound
	}
	s.sessions[params.TokenHash] = user
	return nil
}

func (s *MemoryStore) FindUserBySessionTokenHash(ctx context.Context, tokenHash string) (User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.revoked[tokenHash] {
		return User{}, ErrSessionNotFound
	}
	user, exists := s.sessions[tokenHash]
	if !exists {
		return User{}, ErrSessionNotFound
	}
	return user, nil
}

func (s *MemoryStore) RevokeSession(ctx context.Context, tokenHash string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.sessions[tokenHash]; !exists {
		return ErrSessionNotFound
	}
	s.revoked[tokenHash] = true
	return nil
}
