package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"fmt"
	"strings"

	"crypto/pbkdf2"
)

const (
	passwordAlgorithm = "pbkdf2_sha256"
	passwordIter      = 210000
	passwordSaltBytes = 16
	passwordKeyBytes  = 32
)

// HashPassword 生成带算法、迭代次数、盐值的密码哈希。
//
// 第一阶段避免引入外部依赖，使用 Go 标准库 PBKDF2；后续如果统一安全库，
// 可以在不改变调用方的前提下替换为 bcrypt 或 argon2。
func HashPassword(password string) (string, error) {
	salt := make([]byte, passwordSaltBytes)
	if _, err := rand.Read(salt); err != nil {
		return "", err
	}
	key, err := pbkdf2.Key(sha256.New, password, salt, passwordIter, passwordKeyBytes)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf(
		"%s$%d$%s$%s",
		passwordAlgorithm,
		passwordIter,
		base64.RawStdEncoding.EncodeToString(salt),
		base64.RawStdEncoding.EncodeToString(key),
	), nil
}

// CheckPasswordHash 使用常量时间比较校验密码，避免时序侧信道。
func CheckPasswordHash(password string, encoded string) bool {
	parts := strings.Split(encoded, "$")
	if len(parts) != 4 || parts[0] != passwordAlgorithm {
		return false
	}

	var iter int
	if _, err := fmt.Sscanf(parts[1], "%d", &iter); err != nil {
		return false
	}
	salt, err := base64.RawStdEncoding.DecodeString(parts[2])
	if err != nil {
		return false
	}
	expected, err := base64.RawStdEncoding.DecodeString(parts[3])
	if err != nil {
		return false
	}
	actual, err := pbkdf2.Key(sha256.New, password, salt, iter, len(expected))
	if err != nil {
		return false
	}
	return subtle.ConstantTimeCompare(actual, expected) == 1
}
