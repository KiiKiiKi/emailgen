import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests
import time

# --- Config ---
SPREADSHEET_NAME = "Contact Creation"
HUNTER_URL = "https://api.hunter.io/v2/email-verifier"
REQUEST_TIMEOUT = 15  # seconds
THROTTLE_SECONDS = 0.4  # be nice to APIs; adjust if you hit quotas

# --- Secrets (validate early) ---
def get_secret(path, key_chain):
    try:
        v = path
        for k in key_chain:
            v = v[k]
        if not v:
            raise KeyError(f"Empty secret for {'.'.join(key_chain)}")
        return v
    except Exception as e:
        st.error(f"Missing/invalid secret: {'.'.join(key_chain)} → {e}")
        st.stop()

HUNTER_API_KEY = get_secret(st.secrets, ["hunter", "api_key"])
SERVICE_ACCOUNT_INFO = get_secret(st.secrets, ["google_sheets"])

# --- Google Sheets client ---
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(SERVICE_ACCOUNT_INFO), scope)
    return gspread.authorize(creds)

def run_email_verifier_ui():
    log = st.container()
    with st.spinner("Connecting to Google Sheets..."):
        try:
            client = get_gspread_client()
            spreadsheet = client.open(SPREADSHEET_NAME)
        except Exception as e:
            st.exception(e)
            return {"ok": False, "msg": "Failed to open spreadsheet."}

    try:
        generated_sheet = spreadsheet.worksheet("Generated")
        validation_sheet = spreadsheet.worksheet("Validation")
        history_sheet = spreadsheet.worksheet("History")
    except Exception as e:
        st.exception(e)
        return {"ok": False, "msg": "One or more worksheets are missing (Generated/Validation/History)."}

    # Ensure headers
    validation_headers = [
        "first_name","last_name","email","current_company","current_position",
        "about","skills_1","skills_2","skills_3","url","match_status","status","score"
    ]
    try:
        if not validation_sheet.row_values(1):
            validation_sheet.append_row(validation_headers)
        if not history_sheet.row_values(1):
            history_sheet.append_row(validation_headers)
    except Exception as e:
        st.exception(e)
        return {"ok": False, "msg": "Failed ensuring headers."}

    data = generated_sheet.get_all_values()
    if not data or len(data) == 1:
        st.info("No rows in ‘Generated’ to verify.")
        return {"ok": True, "verified": 0, "skipped": 0}

    headers = data[0]
    rows = data[1:]

    # Column index lookups
    try:
        email_col_index = headers.index("email")
    except ValueError:
        st.error("‘email’ column not found in ‘Generated’.")
        return {"ok": False, "msg": "Email column missing."}

    # Already processed emails
    history_data = history_sheet.get_all_values()[1:]  # skip header
    hist_email_idx = validation_headers.index("email")
    history_emails = {r[hist_email_idx].strip() for r in history_data if len(r) > hist_email_idx and r[hist_email_idx]}

    rows_to_verify = []
    for r in rows:
        if len(r) > email_col_index:
            email = r[email_col_index].strip()
            if email and email not in history_emails:
                rows_to_verify.append(r)
        # else: silently ignore malformed row

    if not rows_to_verify:
        st.info("No new emails to verify (all are already in History).")
        return {"ok": True, "verified": 0, "skipped": len(rows)}

    st.write(f"Found **{len(rows_to_verify)}** new emails to verify.")

    verification_results = []
    errors = []
    for r in rows_to_verify:
        email = r[email_col_index].strip()
        with st.status(f"Verifying {email}…", expanded=False) as status:
            try:
                resp = requests.get(
                    HUNTER_URL,
                    params={"email": email, "api_key": HUNTER_API_KEY},
                    timeout=REQUEST_TIMEOUT,
                )
                status.update(label=f"HTTP {resp.status_code} for {email}")
                # Show raw text if non-JSON to help debugging
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    status.update(state="error")
                    errors.append((email, f"Non-JSON response: {resp.text[:300]}"))
                    continue

                payload = resp.json()
                if "data" in payload:
                    status_val = payload["data"].get("status", "unknown")
                    score_val = payload["data"].get("score", "unknown")
                    # Make the row length match Validation columns:
                    # pad/truncate to first 11 cols, then add status & score
                    base = (r + [""] * 11)[:11]
                    verification_results.append(base + [status_val, score_val])
                    status.update(state="complete")
                elif "errors" in payload:
                    status.update(state="error")
                    errors.append((email, json.dumps(payload["errors"])[:300]))
                else:
                    status.update(state="error")
                    errors.append((email, f"Unexpected payload: {json.dumps(payload)[:300]}"))

            except requests.Timeout:
                errors.append((email, "Request timed out"))
            except Exception as e:
                errors.append((email, f"Exception: {e}"))
        time.sleep(THROTTLE_SECONDS)

    st.write(f"Verified successfully: **{len(verification_results)}**")
    if errors:
        with st.expander("Show errors"):
            for em, err in errors:
                st.write(f"- {em}: {err}")

    # Write to Validation & History only if we have results
    if verification_results:
        try:
            validation_sheet.append_rows(verification_results, value_input_option="RAW")
            history_sheet.append_rows(verification_results, value_input_option="RAW")
            st.success("Updated ‘Validation’ and ‘History’.")
        except Exception as e:
            st.exception(e)
            return {"ok": False, "msg": "Failed writing to Validation/History."}

        # Clear Generated and restore header
        try:
            generated_sheet.clear()
            generated_sheet.append_row(headers)
            st.info("Cleared ‘Generated’ and restored header.")
        except Exception as e:
            st.warning(f"Could not clear ‘Generated’: {e}")

    return {
        "ok": True,
        "verified": len(verification_results),
        "errors": len(errors),
    }

# --- UI Button ---
if st.button("Run Email Verifier"):
    result = run_email_verifier_ui()
    if result and result.get("ok"):
        st.toast(f"Done. Verified: {result.get('verified', 0)}; Errors: {result.get('errors', 0)}")


