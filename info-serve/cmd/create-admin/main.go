package main

import (
	"context"
	"database/sql"
	"flag"
	"fmt"
	"log"
	"strings"

	_ "github.com/go-sql-driver/mysql"

	"info-serve/internal/auth"
	"info-serve/internal/config"
	"info-serve/internal/repository"
)

func main() {
	email := flag.String("email", "", "管理员邮箱")
	password := flag.String("password", "", "管理员密码")
	flag.Parse()

	normalizedEmail := strings.ToLower(strings.TrimSpace(*email))
	if normalizedEmail == "" || len(*password) < 8 {
		log.Fatal("必须提供管理员邮箱，且密码长度至少8位")
	}

	cfg := config.Load()
	db, err := sql.Open("mysql", cfg.MySQLDSN)
	if err != nil {
		log.Fatalf("MySQL 配置无效：%v", err)
	}
	defer db.Close()

	passwordHash, err := auth.HashPassword(*password)
	if err != nil {
		log.Fatalf("密码哈希生成失败：%v", err)
	}

	user, err := repository.UpsertAdminAccount(context.Background(), db, normalizedEmail, passwordHash)
	if err != nil {
		log.Fatalf("管理员账号初始化失败：%v", err)
	}

	fmt.Printf("管理员账号已初始化：id=%d email=%s role=%s\n", user.ID, user.Email, user.Role)
}
