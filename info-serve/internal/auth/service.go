package auth

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"net/mail"
	"strings"
	"time"
)

var (
	ErrEmailAlreadyExists = errors.New("邮箱已注册")
	ErrUserNotFound       = errors.New("用户不存在")
	ErrInvalidCredentials = errors.New("邮箱或密码错误")
	ErrSessionNotFound    = errors.New("会话不存在")
	ErrInvalidInput       = errors.New("参数不合法")
)

// User 是鉴权层使用的用户摘要。
type User struct {
	ID           int64
	Email        string
	PasswordHash string
	Role         string
	Status       string
}

// PublicUser 是返回给前端的安全用户信息，不包含密码哈希。
type PublicUser struct {
	ID     int64  `json:"id"`
	Email  string `json:"email"`
	Role   string `json:"role"`
	Status string `json:"status"`
}

// CreateUserParams 是创建用户时写入存储层的数据。
type CreateUserParams struct {
	Email        string
	PasswordHash string
	Role         string
}

// CreateSessionParams 是创建登录会话时写入存储层的数据。
type CreateSessionParams struct {
	UserID    int64
	Email     string
	TokenHash string
	ExpiresAt time.Time
}

// Store 定义鉴权服务依赖的数据存储能力。
type Store interface {
	CreateUser(ctx context.Context, params CreateUserParams) (User, error)
	FindUserByEmail(ctx context.Context, email string) (User, error)
	CreateSession(ctx context.Context, params CreateSessionParams) error
	FindUserBySessionTokenHash(ctx context.Context, tokenHash string) (User, error)
	RevokeSession(ctx context.Context, tokenHash string) error
}

// Service 封装注册、登录、会话校验等鉴权业务规则。
type Service struct {
	store Store
}

// RegisterInput 是邮箱注册入参。
type RegisterInput struct {
	Email    string
	Password string
}

// LoginInput 是邮箱登录入参。
type LoginInput struct {
	Email    string
	Password string
}

// LoginResult 是登录成功返回值。
type LoginResult struct {
	Token string     `json:"token"`
	User  PublicUser `json:"user"`
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

func (s *Service) Register(ctx context.Context, input RegisterInput) (PublicUser, error) {
	email, err := normalizeEmail(input.Email)
	if err != nil {
		return PublicUser{}, err
	}
	if len(input.Password) < 8 {
		return PublicUser{}, ErrInvalidInput
	}
	passwordHash, err := HashPassword(input.Password)
	if err != nil {
		return PublicUser{}, err
	}
	user, err := s.store.CreateUser(ctx, CreateUserParams{
		Email:        email,
		PasswordHash: passwordHash,
		Role:         "user",
	})
	if err != nil {
		return PublicUser{}, err
	}
	return toPublicUser(user), nil
}

func (s *Service) Login(ctx context.Context, input LoginInput) (LoginResult, error) {
	email, err := normalizeEmail(input.Email)
	if err != nil {
		return LoginResult{}, ErrInvalidCredentials
	}
	user, err := s.store.FindUserByEmail(ctx, email)
	if err != nil {
		return LoginResult{}, ErrInvalidCredentials
	}
	if user.Status != "active" || !CheckPasswordHash(input.Password, user.PasswordHash) {
		return LoginResult{}, ErrInvalidCredentials
	}
	token, tokenHash, err := generateSessionToken()
	if err != nil {
		return LoginResult{}, err
	}
	err = s.store.CreateSession(ctx, CreateSessionParams{
		UserID:    user.ID,
		Email:     user.Email,
		TokenHash: tokenHash,
		ExpiresAt: time.Now().Add(7 * 24 * time.Hour),
	})
	if err != nil {
		return LoginResult{}, err
	}
	return LoginResult{Token: token, User: toPublicUser(user)}, nil
}

func (s *Service) CurrentUser(ctx context.Context, token string) (PublicUser, error) {
	token = strings.TrimSpace(token)
	if token == "" {
		return PublicUser{}, ErrSessionNotFound
	}
	user, err := s.store.FindUserBySessionTokenHash(ctx, hashToken(token))
	if err != nil {
		return PublicUser{}, err
	}
	return toPublicUser(user), nil
}

func (s *Service) Logout(ctx context.Context, token string) error {
	token = strings.TrimSpace(token)
	if token == "" {
		return ErrSessionNotFound
	}
	return s.store.RevokeSession(ctx, hashToken(token))
}

func normalizeEmail(email string) (string, error) {
	normalized := strings.ToLower(strings.TrimSpace(email))
	if _, err := mail.ParseAddress(normalized); err != nil {
		return "", ErrInvalidInput
	}
	return normalized, nil
}

func toPublicUser(user User) PublicUser {
	return PublicUser{
		ID:     user.ID,
		Email:  user.Email,
		Role:   user.Role,
		Status: user.Status,
	}
}

func generateSessionToken() (string, string, error) {
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", "", err
	}
	token := hex.EncodeToString(raw)
	return token, hashToken(token), nil
}

func hashToken(token string) string {
	sum := sha256.Sum256([]byte(token))
	return hex.EncodeToString(sum[:])
}
