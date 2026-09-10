FROM golang:1.27.0-alpine AS builder

WORKDIR /app

# Cache go.mod and go.sum
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o collector ./main.go

# Final image
FROM alpine:latest

# Install ca-certificates if needed
RUN apk add --no-cache ca-certificates

# Set working directory
WORKDIR /app

# Copy the compiled binary from builder
COPY --from=builder /app/collector .

# Command to run
CMD ["./collector"]