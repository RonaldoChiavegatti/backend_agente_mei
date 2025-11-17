#!/usr/bin/env bash
set -euo pipefail

# Smoke script using curl to validate the public API flow:
# register -> login -> profile -> billing -> upload (with polling) -> chat.
#
# Configuration via environment variables (with defaults in parentheses):
#   SMOKE_BASE_URL      Base URL for the API gateway (http://localhost:8000/api)
#   SMOKE_AGENT_ID      UUID of the agent to use for chat (required)
#   SMOKE_DOCUMENT_TYPE Document type for upload (NOTA_FISCAL_EMITIDA)
#   SMOKE_POLL_ATTEMPTS Number of polling attempts for the upload job (10)
#   SMOKE_POLL_DELAY    Seconds between polling attempts (1)

BASE_URL=${SMOKE_BASE_URL:-"http://localhost:8000/api"}
AGENT_ID=${SMOKE_AGENT_ID:-""}
DOCUMENT_TYPE=${SMOKE_DOCUMENT_TYPE:-"NOTA_FISCAL_EMITIDA"}
POLL_ATTEMPTS=${SMOKE_POLL_ATTEMPTS:-10}
POLL_DELAY=${SMOKE_POLL_DELAY:-1}

if [[ -z "$AGENT_ID" ]]; then
  echo "SMOKE_AGENT_ID is required" >&2
  exit 1
fi

command -v jq >/dev/null 2>&1 || {
  echo "jq is required for this script" >&2
  exit 1
}

unique_suffix=$(uuidgen | tr 'A-Z' 'a-z' | cut -c1-8)
EMAIL="smoke_${unique_suffix}@example.com"
PASSWORD="SmokeTest!123"
AUTH_HEADER=""
USER_ID=""

echo "[register] Creating user $EMAIL..."
REGISTER_RESPONSE=$(curl -sS -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Smoke Tester","email":"'"$EMAIL"'","password":"'"$PASSWORD"'"}')
USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.id')
echo "[register] ok -> user_id=$USER_ID"

echo "[login] Requesting token..."
LOGIN_RESPONSE=$(curl -sS -X POST "$BASE_URL/auth/login" \
  -d "username=$EMAIL" -d "password=$PASSWORD")
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
echo "[login] ok"

echo "[profile] Fetching profile..."
PROFILE_RESPONSE=$(curl -sS -H "$AUTH_HEADER" "$BASE_URL/auth/profile")
CREATED_AT=$(echo "$PROFILE_RESPONSE" | jq -r '.created_at')
echo "[profile] ok -> created_at=$CREATED_AT"

echo "[billing] Checking balance..."
BILLING_RESPONSE=$(curl -sS -H "$AUTH_HEADER" "$BASE_URL/billing/balance/$USER_ID")
BALANCE=$(echo "$BILLING_RESPONSE" | jq -r '.balance')
echo "[billing] ok -> balance=$BALANCE"

echo "[upload] Sending document..."
UPLOAD_RESPONSE=$(curl -sS -X POST "$BASE_URL/documents/upload" \
  -H "$AUTH_HEADER" \
  -F "file=@-;filename=smoke.txt;type=text/plain" \
  -F "document_type=$DOCUMENT_TYPE" <<< "Smoke test document")
JOB_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.id')
JOB_STATUS=$(echo "$UPLOAD_RESPONSE" | jq -r '.status')
echo "[upload] ok -> job_id=$JOB_ID, status=$JOB_STATUS"

echo "[upload] Polling job status..."
for ((attempt=1; attempt<=POLL_ATTEMPTS; attempt++)); do
  JOB_RESPONSE=$(curl -sS -H "$AUTH_HEADER" "$BASE_URL/documents/jobs/$JOB_ID")
  JOB_STATUS=$(echo "$JOB_RESPONSE" | jq -r '.status')
  UPDATED_AT=$(echo "$JOB_RESPONSE" | jq -r '.updated_at')
  echo "  attempt $attempt -> status=$JOB_STATUS"
  if [[ "$JOB_STATUS" == "concluido" || "$JOB_STATUS" == "falhou" ]]; then
    break
  fi
  sleep "$POLL_DELAY"
done

echo "[upload] completed -> status=$JOB_STATUS, updated_at=$UPDATED_AT"

if [[ "$JOB_STATUS" == "falhou" ]]; then
  echo "Job failed" >&2
  exit 1
fi

echo "[chat] Sending message to agent..."
CHAT_PAYLOAD=$(jq -n --arg agent "$AGENT_ID" --arg msg "Teste rápido de fumo" '{agent_id:$agent, user_message:$msg, conversation_history:[]}')
CHAT_RESPONSE=$(curl -sS -X POST "$BASE_URL/agent/chat" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "$CHAT_PAYLOAD")
ASSISTANT_MESSAGE=$(echo "$CHAT_RESPONSE" | jq -r '.assistant_message')
echo "[chat] ok -> assistant_message=$ASSISTANT_MESSAGE"

echo "All smoke steps completed successfully."
