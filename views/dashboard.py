"""History dashboard: list, search, create, edit, listen to, export and delete transcriptions."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

import streamlit as st

from stt.app_context import flash, get_repository, speak
from stt.database import SOURCES, TITLE_MAX_LENGTH, Transcription
from stt.languages import LANGUAGE_OPTIONS, storage_label

TABLE_KEY = "history_table"
LANGUAGE_VALUES = [storage_label(codes) for codes in LANGUAGE_OPTIONS.values()]
PREVIEW_LENGTH = 120

repo = get_repository()


# -- Formatting helpers ---------------------------------------------------------------
def _fmt_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return f"{value:%d %b %Y, %H:%M} UTC"


def _fmt_duration(seconds: float | None) -> str:
    if not seconds:
        return "-"
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _preview(text: str) -> str:
    return text if len(text) <= PREVIEW_LENGTH else text[:PREVIEW_LENGTH].rstrip() + "..."


def _to_csv(records: list[Transcription]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "title", "text", "language", "source", "duration_seconds", "created_at", "updated_at"])
    for r in records:
        writer.writerow([r.id, r.title, r.text, r.language, r.source, r.duration_seconds, r.created_at, r.updated_at])
    return buffer.getvalue()


def _language_options(current: str) -> list[str]:
    return LANGUAGE_VALUES if current in LANGUAGE_VALUES else [*LANGUAGE_VALUES, current]


# -- Create -----------------------------------------------------------------------------
def _render_create_form() -> None:
    with st.expander("➕ Add a transcription manually"):
        with st.form("create_form", clear_on_submit=True):
            title = st.text_input("Title", max_chars=TITLE_MAX_LENGTH)
            text = st.text_area("Text", height=120)
            language = st.selectbox("Language", LANGUAGE_VALUES)
            if st.form_submit_button("Create", type="primary"):
                try:
                    repo.create(title=title, text=text, language=language, source="manual")
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    flash("Transcription created.")
                    st.rerun()


# -- Update / Delete --------------------------------------------------------------------
@st.dialog("Delete transcription?")
def _confirm_delete(record: Transcription) -> None:
    st.write(f"This permanently deletes **{record.title}**. This cannot be undone.")
    delete_col, cancel_col = st.columns(2)
    if delete_col.button("Delete", type="primary", width="stretch"):
        if repo.delete(record.id):
            flash("Transcription deleted.", icon="🗑️")
        st.session_state.pop(TABLE_KEY, None)  # clear the stale row selection
        st.rerun()
    if cancel_col.button("Cancel", width="stretch"):
        st.rerun()


def _render_record_editor(record: Transcription) -> None:
    st.subheader(f"✏️ {record.title}")
    st.caption(
        f"#{record.id} · {record.source} · {record.language} · {record.word_count} words · "
        f"created {_fmt_datetime(record.created_at)} · updated {_fmt_datetime(record.updated_at)}"
    )

    with st.form(f"edit_form_{record.id}"):
        title = st.text_input("Title", value=record.title, max_chars=TITLE_MAX_LENGTH)
        text = st.text_area("Text", value=record.text, height=200)
        options = _language_options(record.language)
        language = st.selectbox("Language", options, index=options.index(record.language))
        if st.form_submit_button("💾 Save changes", type="primary"):
            try:
                repo.update(record.id, title=title, text=text, language=language)
            except ValueError as exc:
                st.error(str(exc))
            else:
                flash("Changes saved.")
                st.rerun()

    listen_col, download_col, delete_col = st.columns(3)
    play = listen_col.button("🔊 Listen", width="stretch")
    download_col.download_button(
        "⬇️ Download .txt", record.text, file_name=f"transcription-{record.id}.txt", width="stretch"
    )
    if delete_col.button("🗑️ Delete", width="stretch"):
        _confirm_delete(record)

    if play:
        try:
            st.audio(speak(record.text), format="audio/mp3", autoplay=True)
        except Exception as exc:
            st.error(f"Text-to-Speech failed: {exc}")


# -- Page -------------------------------------------------------------------------------
st.title("📚 Transcription History")

search_col, source_col = st.columns([3, 1])
search = search_col.text_input("Search", placeholder="Search titles and text...", label_visibility="collapsed")
source = source_col.selectbox("Source", ["All sources", *SOURCES], label_visibility="collapsed")

stats = repo.stats()
records = repo.list(search=search, source=None if source == "All sources" else source)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total saved", stats.total)
m2.metric("Added this week", stats.last_7_days)
m3.metric("Words (shown)", sum(r.word_count for r in records))
m4.metric("Audio (shown)", _fmt_duration(sum(r.duration_seconds or 0 for r in records)))

_render_create_form()

if not records:
    st.info("No transcriptions yet. Record one on the Live Transcription page." if stats.total == 0
            else "No transcriptions match your filters.")
    st.stop()

rows = [
    {
        "ID": r.id,
        "Title": r.title,
        "Preview": _preview(r.text),
        "Language": r.language,
        "Source": r.source,
        "Words": r.word_count,
        "Duration": _fmt_duration(r.duration_seconds),
        "Created": _fmt_datetime(r.created_at),
    }
    for r in records
]
event = st.dataframe(
    rows,
    key=TABLE_KEY,
    on_select="rerun",
    selection_mode="single-row",
    hide_index=True,
    width="stretch",
    column_config={"Preview": st.column_config.TextColumn(width="large")},
)
st.download_button("⬇️ Export all as CSV", _to_csv(records), file_name="transcriptions.csv", mime="text/csv")

selected_rows = event.selection.rows
if selected_rows and selected_rows[0] < len(records):
    st.divider()
    _render_record_editor(records[selected_rows[0]])
else:
    st.caption("Select a row in the table to view, edit, listen to or delete a transcription.")
