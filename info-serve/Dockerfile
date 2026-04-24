FROM golang:1.24-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o info-serve ./cmd/server \
    && CGO_ENABLED=0 GOOS=linux go build -o create-admin ./cmd/create-admin

FROM alpine:3.21

RUN apk add --no-cache ca-certificates

WORKDIR /app

COPY --from=builder /app/info-serve .
COPY --from=builder /app/create-admin .

EXPOSE 8080

CMD ["./info-serve"]
