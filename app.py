import streamlit as st
import sqlite3
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="AI Document Verification System",
    page_icon="",
    layout="wide"
)
DB_PATH = Path(__file__).with_name("verification_history.db")
# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
.stApp {
    background-color: #f4f7fc;
}
.main-title {
    color: #174a91;
    font-size: 30px;
    font-weight: 800;
}
.subtitle {
    color: #64748b;
    font-size: 15px;
}
.metric-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #dbe5f2;
    text-align: center;
}
.metric-number {
    font-size: 32px;
    font-weight: bold;
}
.metric-label {
    color: #64748b;
    font-size: 14px;
}
div.stButton > button[kind="primary"] {
    background-color: #2164df;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)
# ---------------- DATABASE ----------------
def get_connection():
    return sqlite3.connect(DB_PATH)
def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                name TEXT,
                document_id TEXT,
                email TEXT,
                phone TEXT,
                status TEXT NOT NULL,
                reason TEXT,
                verified_at TEXT NOT NULL
            )
        """)
def save_record(filename, data, status, reason):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO history
            (filename, name, document_id, email, phone,
             status, reason, verified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            data.get("Name", ""),
            data.get("Document ID", ""),
            data.get("Email", ""),
            data.get("Phone", ""),
            status,
            reason,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
def get_history():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM history ORDER BY id DESC", conn
        )
initialize_database()
# ---------------- TEXT PROCESSING ----------------
def extract_information(text):
    def get_value(pattern):
        match = re.search(
            pattern, text, re.IGNORECASE | re.MULTILINE
        )
        return match.group(1).strip() if match else ""
    name = get_value(r"^\s*Name\s*:\s*(.+?)\s*$")
    document_id = get_value(
        r"^\s*(?:Document ID|ID)\s*:\s*([A-Za-z0-9-]+)"
    )
    email = get_value(
        r"^\s*Email\s*:\s*([^\s]+)\s*$"
    )
    phone = get_value(
        r"^\s*Phone\s*:\s*([0-9+\-() ]+)\s*$"
    )
    return {
        "Name": name,
        "Document ID": document_id,
        "Email": email,
        "Phone": phone
    }
# ---------------- DOCUMENT VERIFICATION ----------------
def verify_document(data):
    checks = {
        "Name is present": bool(data["Name"]),
        "Document ID is valid": bool(
            re.fullmatch(
                r"[A-Za-z0-9-]+", data["Document ID"]
            )
        ),
        "Email format is valid": bool(
            re.fullmatch(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                data["Email"]
            )
        ),
        "Phone contains 10 digits": bool(
            re.fullmatch(
                r"\d{10}",
                re.sub(r"\D", "", data["Phone"])
            )
        )
    }
    failures = [
        label for label, passed in checks.items()
        if not passed
    ]
    status = "Verified" if not failures else "Not Verified"
    reason = (
        "All required checks passed."
        if not failures
        else "Failed checks: " + ", ".join(failures)
    )
    return checks, status, reason
# ---------------- SESSION STATE ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "processed_uploads" not in st.session_state:
    st.session_state.processed_uploads = set()
# ---------------- LOGIN PAGE ----------------
if not st.session_state.logged_in:
    left, right = st.columns([1, 1.2], gap="large")
    with left:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<h1 style='color:#174a91'>"
            " AI-Based Automated Document Verification"
            "</h1>",
            unsafe_allow_html=True
        )
        st.write(
            "Information Extraction and Document Verification System"
        )
        st.info(
            "Upload documents, extract important information, "
            "validate details, and view verification history."
        )
    with right:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("##  Login")
            st.write("Enter your credentials to continue.")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input(
                    "Password", type="password"
                )
                login_button = st.form_submit_button(
                    "Login",
                    type="primary",
                    use_container_width=True
                )
            if login_button:
                if username == "admin" and password == "admin":
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            st.caption(
                "Demo login: username admin / password admin"
            )
    st.stop()
# ---------------- SIDEBAR NAVIGATION ----------------
with st.sidebar:
    st.markdown("##  AI Document Verification")
    st.caption("Information Extraction System")
    st.divider()
    page = st.radio(
        "Navigation",
        ["Dashboard", "Upload & Verify", "History"],
        label_visibility="collapsed"
    )
    st.divider()
    st.write(f" {st.session_state.username}")
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.last_result = None
        st.session_state.processed_uploads = set()
        st.rerun()
# ---------------- LOAD HISTORY ----------------
history = get_history()
total = len(history)
verified_count = int(
    (history["status"] == "Verified").sum()
) if total else 0
failed_count = int(
    (history["status"] == "Not Verified").sum()
) if total else 0
# ---------------- HEADER ----------------
st.markdown(
    "<div class='main-title'>"
    "AI-Based Automated Document Verification"
    "</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div class='subtitle'>"
    "Information Extraction and Document Verification System"
    "</div>",
    unsafe_allow_html=True
)
st.divider()
# ---------------- DASHBOARD ----------------
if page == "Dashboard":
    st.subheader("Welcome, Admin!")
    st.write("Overview of your document verification activity.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""<div class="metric-card">
            <div class="metric-label">📄 Total Documents</div>
            <div class="metric-number" style="color:#2164df">
            {total}</div>
            </div>""",
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"""<div class="metric-card">
            <div class="metric-label">✅ Verified</div>
            <div class="metric-number" style="color:#168447">
            {verified_count}</div>
            </div>""",
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"""<div class="metric-card">
            <div class="metric-label">❌ Not Verified</div>
            <div class="metric-number" style="color:#dc3545">
            {failed_count}</div>
            </div>""",
            unsafe_allow_html=True
        )
    st.subheader("Verification Statistics")
    if total > 0:
        chart_data = pd.DataFrame({
            "Status": ["Verified", "Not Verified"],
            "Documents": [verified_count, failed_count]
        }).set_index("Status")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Documents by Status**")
            st.bar_chart(chart_data)
        with col2:
            st.markdown("**Verification Percentages**")
            st.dataframe(
                pd.DataFrame({
                    "Status": ["Verified", "Not Verified"],
                    "Count": [verified_count, failed_count],
                    "Percentage": [
                        f"{verified_count / total * 100:.1f}%",
                        f"{failed_count / total * 100:.1f}%"
                    ]
                }),
                hide_index=True,
                use_container_width=True
            )
        st.subheader("Recent Verification History")
        st.dataframe(
            history[[
                "verified_at",
                "filename",
                "document_id",
                "status",
                "reason"
            ]].head(5),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info(
            "No documents processed yet. Open Upload & Verify "
            "to process your first document."
        )
# ---------------- UPLOAD AND VERIFY ----------------
elif page == "Upload & Verify":
    st.subheader(" Upload a Document")
    st.write(
        "Upload a text file. After verification, click "
        "'Upload Another Document' to select another file."
    )
    # A new key resets the file uploader when the user
    # clicks the Upload Another Document button.
    uploaded_file = st.file_uploader(
        "Choose a text document",
        type=["txt"],
        key=f"document_upload_{st.session_state.upload_key}"
    )
    if uploaded_file is not None:
        try:
            text_content = uploaded_file.getvalue().decode(
                "utf-8-sig"
            )
            st.subheader(" Document Content")
            st.text_area(
                "Uploaded text",
                value=text_content,
                height=220,
                disabled=True,
                key=f"content_{st.session_state.upload_key}"
            )
            # Identify this upload so the same file is not
            # recorded repeatedly during Streamlit reruns.
            upload_signature = (
                st.session_state.upload_key,
                uploaded_file.name,
                uploaded_file.getvalue()
            )
            if upload_signature not in st.session_state.processed_uploads:
                if st.button(
                    "Verify Document",
                    type="primary",
                    key=f"verify_{st.session_state.upload_key}"
                ):
                    data = extract_information(text_content)
                    checks, status, reason = verify_document(data)
                    save_record(
                        uploaded_file.name,
                        data,
                        status,
                        reason
                    )
                    st.session_state.last_result = {
                        "filename": uploaded_file.name,
                        "data": data,
                        "checks": checks,
                        "status": status,
                        "reason": reason
                    }
                    st.session_state.processed_uploads.add(
                        upload_signature
                    )
                    st.rerun()
            # Show the latest result only for the current upload.
            result = st.session_state.last_result
            if (
                result is not None
                and result["filename"] == uploaded_file.name
                and upload_signature in st.session_state.processed_uploads
            ):
                st.divider()
                st.subheader(" Extracted Information")
                st.write(f"**File:** {result['filename']}")
                st.table(
                    pd.DataFrame(
                        list(result["data"].items()),
                        columns=["Field", "Extracted Value"]
                    )
                )
                st.subheader("🛡️ Verification Result")
                if result["status"] == "Verified":
                    st.success("✅ Document Verified")
                else:
                    st.error("❌ Document Not Verified")
                st.write(result["reason"])
                st.subheader("Validation Checks")
                for label, passed in result["checks"].items():
                    if passed:
                        st.success(f"✓ {label}")
                    else:
                        st.error(f"✗ {label}")
                st.divider()
                # NEW BUTTON: RESET UPLOADER FOR NEXT DOCUMENT
                if st.button(
                    " Upload Another Document",
                    type="primary",
                    key="upload_another_document"
                ):
                    st.session_state.upload_key += 1
                    st.session_state.last_result = None
                    st.rerun()
                st.info(
                    "Your verification has been saved in History. "
                    "You can now upload another document."
                )
        except UnicodeDecodeError:
            st.error(
                "Unable to read this file. Please upload a "
                "UTF-8 encoded .txt document."
            )
# ---------------- VERIFICATION HISTORY ----------------
elif page == "History":
    st.subheader(" Verification History")
    st.write("Summary of all previously processed documents.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Documents", total)
    c2.metric("✅ Verified", verified_count)
    c3.metric("❌ Not Verified", failed_count)
    if total > 0:
        st.subheader("Verification Summary")
        summary = pd.DataFrame({
            "Status": ["Verified", "Not Verified"],
            "Count": [verified_count, failed_count]
        }).set_index("Status")
        st.bar_chart(summary)
        st.subheader("All Verification Records")
        search = st.text_input(
            "Search by filename or document ID"
        )
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Verified", "Not Verified"]
        )
        filtered = history.copy()
        if search:
            mask = (
                filtered["filename"].str.contains(
                    search, case=False, na=False
                )
                | filtered["document_id"].str.contains(
                    search, case=False, na=False
                )
            )
            filtered = filtered[mask]
        if status_filter != "All":
            filtered = filtered[
                filtered["status"] == status_filter
            ]
        display_columns = [
            "id",
            "verified_at",
            "filename",
            "name",
            "document_id",
            "email",
            "phone",
            "status",
            "reason"
        ]
        st.dataframe(
            filtered[display_columns],
            hide_index=True,
            use_container_width=True
        )
        if st.button("Clear All History"):
            with get_connection() as conn:
                conn.execute("DELETE FROM history")
            st.session_state.last_result = None
            st.session_state.processed_uploads = set()
            st.rerun()
    else:
        st.info(
            "History is empty. Upload and verify documents "
            "to see the results here."
        )
