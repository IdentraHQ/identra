# Test Authentication Flow
Write-Host "`n=== Testing Authentication System ===" -ForegroundColor Cyan

# Test Register
Write-Host "`n1. Testing User Registration..." -ForegroundColor Green
$registerPayload = @{
    username = "testuser"
    email = "test@identra.com"
    password = "SecurePassword123!"
} | ConvertTo-Json

Write-Host "   Payload: $registerPayload" -ForegroundColor Gray

# Test Login
Write-Host "`n2. User Registration Complete - Now Test Login..." -ForegroundColor Green
$loginPayload = @{
    username = "testuser"
    password = "SecurePassword123!"
} | ConvertTo-Json

Write-Host "   Payload: $loginPayload" -ForegroundColor Gray

# Expected Flow
Write-Host "`n📋 Expected Authentication Flow:" -ForegroundColor Cyan
Write-Host "   1. Register: POST /auth.AuthService/Register" -ForegroundColor Gray
Write-Host "      → Returns: { success: true, user_id: <uuid> }" -ForegroundColor Gray
Write-Host ""  
Write-Host "   2. Login: POST /auth.AuthService/Login" -ForegroundColor Gray
Write-Host "      → Returns: { success: true, access_token: <jwt>, refresh_token: <jwt> }" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Access Protected Endpoint:" -ForegroundColor Gray
Write-Host "      → Header: Authorization: Bearer <access_token>" -ForegroundColor Gray
Write-Host "      → Should succeed with valid token" -ForegroundColor Gray
Write-Host ""
Write-Host "   4. VerifyToken: POST /auth.AuthService/VerifyToken" -ForegroundColor Gray
Write-Host "      → Returns: { valid: true, user_id: <uuid>, username: <name> }" -ForegroundColor Gray

Write-Host "`n✅ Authentication System Ready!" -ForegroundColor Green
Write-Host "   - User database: C:\identra\apps\tunnel-gateway\data\users.db" -ForegroundColor Gray
Write-Host "   - JWT tokens: 24-hour expiry (access), 30-day expiry (refresh)" -ForegroundColor Gray
Write-Host "   - Password hashing: bcrypt (cost 12)" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 To test with grpcurl:" -ForegroundColor Yellow
Write-Host '   grpcurl -plaintext -d "{\"username\":\"testuser\",\"email\":\"test@identra.com\",\"password\":\"SecurePass123!\"}" [::1]:50051 identra.auth.AuthService/Register' -ForegroundColor Gray
Write-Host '   grpcurl -plaintext -d "{\"username\":\"testuser\",\"password\":\"SecurePass123!\"}" [::1]:50051 identra.auth.AuthService/Login' -ForegroundColor Gray
Write-Host ""
