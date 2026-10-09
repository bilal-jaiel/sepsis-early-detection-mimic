import pandas as pd
import streamlit as st
import plotly.express as px

from omop_db import (
    get_overview_counts,
    get_event_type_distribution,
    get_top_concepts,
    get_all_patient_selector_options,
    get_patient_timeline,
    get_waveform_concepts,
    get_waveform_data_multi,
    get_patient_demographics_by_subject,
    get_patient_summary_by_subject,
    get_patient_clinical_counts,
    get_patient_visits_by_subject,
    get_patient_notes,
    get_patient_medications,
    get_patient_conditions,
    get_patient_observations,
)


st.set_page_config(
    page_title="OMOP Clinical + Waveform Explorer",
    page_icon="🩺",
    layout="wide",
)

st.title("🩺 OMOP Clinical + Waveform Explorer")
st.caption("Interactive GUI for MIMIC-IV OMOP clinical data and waveform-derived features")


# ============================================================
# HELPERS
# ============================================================

DEFAULT_ANONYMIZED_START = pd.Timestamp("2140-01-01 00:00:00")
DEFAULT_ANONYMIZED_END = pd.Timestamp("2200-12-31 23:59:59")


def safe_datetime(value, fallback=None):
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return fallback
    return dt


def sort_by_datetime(df, datetime_col):
    if df is None or len(df) == 0:
        return df

    if datetime_col not in df.columns:
        return df.reset_index(drop=True)

    out = df.copy()
    out[datetime_col] = pd.to_datetime(out[datetime_col], errors="coerce")

    return (
        out
        .sort_values(datetime_col, ascending=True)
        .reset_index(drop=True)
    )


def apply_time_window(df, datetime_col, start_datetime, end_datetime):
    if df is None or len(df) == 0:
        return df

    if datetime_col not in df.columns:
        return df.reset_index(drop=True)

    out = df.copy()
    out[datetime_col] = pd.to_datetime(out[datetime_col], errors="coerce")

    if start_datetime is not None and end_datetime is not None:
        out = out[
            (out[datetime_col] >= start_datetime)
            & (out[datetime_col] <= end_datetime)
        ]

    return out.reset_index(drop=True)


def show_active_time_window(start_datetime, end_datetime):
    if start_datetime is not None and end_datetime is not None:
        if start_datetime > end_datetime:
            st.error("Start date/time must be before end date/time.")
            st.stop()

        st.info(f"Time window active: {start_datetime} → {end_datetime}")


def combine_time_ranges(*ranges):
    starts = []
    ends = []

    for start, end in ranges:
        start = safe_datetime(start)
        end = safe_datetime(end)

        if start is not None:
            starts.append(start)

        if end is not None:
            ends.append(end)

    final_start = min(starts) if starts else DEFAULT_ANONYMIZED_START
    final_end = max(ends) if ends else DEFAULT_ANONYMIZED_END

    return final_start, final_end


def get_patient_default_time_range(subject_id):
    summary, _ = get_patient_summary_by_subject(subject_id)
    visits, _ = get_patient_visits_by_subject(subject_id)

    summary_start = None
    summary_end = None
    visits_start = None
    visits_end = None

    if len(summary):
        summary_start = summary.iloc[0].get("first_event")
        summary_end = summary.iloc[0].get("last_event")

    if len(visits):
        visits["visit_start_datetime"] = pd.to_datetime(
            visits["visit_start_datetime"],
            errors="coerce",
        )
        visits["visit_end_datetime"] = pd.to_datetime(
            visits["visit_end_datetime"],
            errors="coerce",
        )

        visits_start = visits["visit_start_datetime"].min()
        visits_end = visits["visit_end_datetime"].max()

    return combine_time_ranges(
        (summary_start, summary_end),
        (visits_start, visits_end),
    )


def extend_range_with_dataframe(base_start, base_end, df, datetime_cols):
    ranges = [(base_start, base_end)]

    if df is not None and len(df):
        for col in datetime_cols:
            if col in df.columns:
                temp = pd.to_datetime(df[col], errors="coerce")
                ranges.append((temp.min(), temp.max()))

    return combine_time_ranges(*ranges)


def render_time_window_filter(prefix, title, default_start_datetime, default_end_datetime):
    st.sidebar.divider()
    st.sidebar.markdown(f"### {title}")

    use_filter = st.sidebar.checkbox(
        "Filter by date/time",
        value=False,
        key=f"{prefix}_use_time_window",
    )

    if not use_filter:
        return None, None

    default_start_datetime = safe_datetime(
        default_start_datetime,
        DEFAULT_ANONYMIZED_START,
    )

    default_end_datetime = safe_datetime(
        default_end_datetime,
        DEFAULT_ANONYMIZED_END,
    )

    start_date = st.sidebar.date_input(
        "Start date",
        value=default_start_datetime.date(),
        key=f"{prefix}_start_date",
    )

    start_time = st.sidebar.time_input(
        "Start time",
        value=default_start_datetime.time(),
        key=f"{prefix}_start_time",
    )

    end_date = st.sidebar.date_input(
        "End date",
        value=default_end_datetime.date(),
        key=f"{prefix}_end_date",
    )

    end_time = st.sidebar.time_input(
        "End time",
        value=default_end_datetime.time(),
        key=f"{prefix}_end_time",
    )

    return (
        pd.Timestamp.combine(start_date, start_time),
        pd.Timestamp.combine(end_date, end_time),
    )


# ============================================================
# GLOBAL SIDEBAR
# ============================================================

st.sidebar.header("🔎 Patient")

patient_options, _ = get_all_patient_selector_options(limit=1000)

patient_options["label"] = patient_options.apply(
    lambda r: (
        f"{int(r['display_patient_id'])}"
        f"{' 📈 waveform' if r['has_waveform'] else ''}"
    ),
    axis=1,
)

selected_label = st.sidebar.selectbox(
    "Patient",
    patient_options["label"].tolist(),
    index=0,
)

selected_row = patient_options.loc[
    patient_options["label"] == selected_label
].iloc[0]

subject_id = int(selected_row["display_patient_id"])
has_waveform = bool(selected_row["has_waveform"])
mapped = bool(selected_row["has_omop_mapping"])
omop_person_id = selected_row["omop_person_id"]

patient_first_datetime, patient_last_datetime = get_patient_default_time_range(subject_id)

if has_waveform:
    st.sidebar.success("Waveform available")
else:
    st.sidebar.info("No waveform data")

if mapped and pd.notna(omop_person_id):
    st.sidebar.success(f"Mapped person_id: {int(omop_person_id)}")

row_limit = st.sidebar.slider(
    "Row limit",
    min_value=100,
    max_value=3000,
    value=500,
    step=100,
)


pages = [
    "🏠 Overview",
    "👤 Patient Explorer",
    "🕒 Clinical Timeline",
    "📈 Waveform Analytics",
    "💊 Medications",
    "🩺 Conditions",
    "📝 Doctor Notes",
]

page = st.segmented_control(
    "Section",
    pages,
    default="🏠 Overview",
    label_visibility="collapsed",
)

st.divider()


# ============================================================
# OVERVIEW
# ============================================================

if page == "🏠 Overview":
    st.subheader("Dataset overview")

    counts, t_counts = get_overview_counts()
    event_dist, t_event = get_event_type_distribution()
    top_concepts, t_top = get_top_concepts(20)

    counts_dict = dict(zip(counts["label"], counts["value"]))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Patients", f"{int(counts_dict.get('Patients', 0)):,}")
    c2.metric("Events", f"{int(counts_dict.get('Events', 0)):,}")
    c3.metric("Waveform events", f"{int(counts_dict.get('Waveform Events', 0)):,}")
    c4.metric("Concepts", f"{int(counts_dict.get('Concepts', 0)):,}")

    st.caption(f"Loaded in {(t_counts + t_event + t_top):.3f} s")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Event type distribution")
        event_dist = event_dist.reset_index(drop=True)
        st.dataframe(event_dist, use_container_width=True)

        fig = px.bar(
            event_dist,
            x="event_type",
            y="n_events",
            text="n_events",
            title="Events by type",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Top concepts")
        top_concepts = top_concepts.reset_index(drop=True)
        st.dataframe(top_concepts, use_container_width=True)

        fig = px.bar(
            top_concepts,
            x="n_events",
            y="concept_name",
            color="event_type",
            orientation="h",
            title="Top concepts",
        )
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# PATIENT EXPLORER
# ============================================================

elif page == "👤 Patient Explorer":
    st.subheader("Patient identification card")
    st.caption(
        "This page identifies the selected patient and summarizes what data exists for them. "
        "It is intentionally not chronological."
    )

    demo, t_demo = get_patient_demographics_by_subject(subject_id)
    summary, t_summary = get_patient_summary_by_subject(subject_id)
    clinical_counts, t_counts = get_patient_clinical_counts(subject_id)
    visits, t_visits = get_patient_visits_by_subject(subject_id)
    observations, t_obs = get_patient_observations(subject_id, limit=50)

    visits = sort_by_datetime(visits, "visit_start_datetime")
    observations = sort_by_datetime(observations, "event_datetime")

    st.caption(f"Loaded in {(t_demo + t_summary + t_counts + t_visits + t_obs):.3f} s")

    birth_year = "Unknown"
    gender = "Unknown"
    race = "Unknown"
    ethnicity = "Unknown"

    if len(demo):
        d = demo.iloc[0]
        birth_year = d.get("year_of_birth", "Unknown")
        gender = d.get("gender_source_value", "Unknown")
        race = d.get("race_source_value", "Unknown")
        ethnicity = d.get("ethnicity_source_value", "Unknown")

    st.markdown("### Identity")

    id_col1, id_col2, id_col3 = st.columns([1.4, 1.4, 1.2])

    with id_col1:
        st.metric("Displayed patient ID", subject_id)
        st.metric("OMOP person_id", int(omop_person_id) if pd.notna(omop_person_id) else "Missing")

    with id_col2:
        st.metric("Year of birth", birth_year)
        st.metric("Gender", gender)

    with id_col3:
        st.metric("Waveform available", "Yes" if has_waveform else "No")
        st.metric("OMOP mapped", "Yes" if mapped else "No")

    st.markdown("### Demographic details")

    demo_cards = pd.DataFrame(
        [
            {"field": "Subject ID", "value": subject_id},
            {"field": "OMOP person_id", "value": int(omop_person_id) if pd.notna(omop_person_id) else None},
            {"field": "Year of birth", "value": birth_year},
            {"field": "Gender", "value": gender},
            {"field": "Race", "value": race},
            {"field": "Ethnicity", "value": ethnicity},
            {"field": "Has waveform data", "value": has_waveform},
        ]
    ).reset_index(drop=True)

    st.dataframe(demo_cards, use_container_width=True, hide_index=True)

    st.markdown("### Data availability")

    if len(clinical_counts):
        clinical_counts = clinical_counts.reset_index(drop=True)
        counts_dict = clinical_counts.set_index("label")["value"].to_dict()

        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Visits", f"{int(counts_dict.get('Visits', 0)):,}")
        c2.metric("Care units", f"{int(counts_dict.get('Care units', 0)):,}")
        c3.metric("Medications", f"{int(counts_dict.get('Medications', 0)):,}")
        c4.metric("Conditions", f"{int(counts_dict.get('Conditions', 0)):,}")
        c5.metric("Procedures", f"{int(counts_dict.get('Procedures', 0)):,}")
        c6.metric("Observations", f"{int(counts_dict.get('Observations', 0)):,}")
        c7.metric("Notes", f"{int(counts_dict.get('Doctor notes', 0)):,}")

        st.dataframe(clinical_counts, use_container_width=True, hide_index=True)
    else:
        st.info("No clinical table counts found.")

    st.markdown("### Longitudinal coverage")

    if len(summary):
        s = summary.iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total longitudinal events", f"{int(s['total_events']):,}")
        c2.metric("Clinical events", f"{int(s['non_waveform_events']):,}")
        c3.metric("Waveform events", f"{int(s['waveform_events']):,}")
        c4.metric("Concepts", f"{int(s['concepts']):,}")

        coverage = pd.DataFrame(
            [
                {"field": "First available patient event", "value": patient_first_datetime},
                {"field": "Last available patient event", "value": patient_last_datetime},
                {"field": "Longitudinal first event", "value": s["first_event"]},
                {"field": "Longitudinal last event", "value": s["last_event"]},
            ]
        ).reset_index(drop=True)

        st.dataframe(coverage, use_container_width=True, hide_index=True)
    else:
        st.warning("No longitudinal events found.")

    st.markdown("### Additional observations")

    if len(observations):
        display_obs_cols = [
        "event_datetime",
        "observation_value",
        "observation_type",
        "value_as_string",
        "value_as_number",
        "observation_source_value",
        "mapped_concept_name",
        "vocabulary_id",
     ]

        st.dataframe(
            observations[[c for c in display_obs_cols if c in observations.columns]].reset_index(drop=True),
            use_container_width=True,
        )
    else:
        st.info("No additional observations found.")

    st.markdown("### Hospital visits")

    if len(visits):
        st.dataframe(visits.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No OMOP visit_occurrence rows found.")


# ============================================================
# CLINICAL TIMELINE
# ============================================================

elif page == "🕒 Clinical Timeline":
    st.sidebar.divider()
    st.sidebar.header("🕒 Timeline filters")
    st.sidebar.caption("Spunta o togli gli eventi da mostrare nella timeline clinica.")

    timeline_event_types = {
        "admission": "Hospital admissions",
        "discharge": "Hospital discharges",
        "care_unit_start": "Care unit starts",
        "care_unit_end": "Care unit ends",
        "measurement": "Clinical measurements",
        "drug_exposure": "Medication administrations",
        "condition_occurrence": "Conditions / diagnoses",
        "procedure_occurrence": "Procedures",
    }

    for event_type in timeline_event_types:
        key = f"timeline_filter_{event_type}"
        if key not in st.session_state:
            st.session_state[key] = True

    col_a, col_b = st.sidebar.columns(2)

    with col_a:
        if st.button("Select all", use_container_width=True):
            for event_type in timeline_event_types:
                st.session_state[f"timeline_filter_{event_type}"] = True
            st.rerun()

    with col_b:
        if st.button("Clear all", use_container_width=True):
            for event_type in timeline_event_types:
                st.session_state[f"timeline_filter_{event_type}"] = False
            st.rerun()

    selected_event_types = []

    for event_type, label in timeline_event_types.items():
        checked = st.sidebar.checkbox(
            label,
            key=f"timeline_filter_{event_type}",
        )

        if checked:
            selected_event_types.append(event_type)

    timeline_start_datetime, timeline_end_datetime = render_time_window_filter(
        "timeline",
        "Time window",
        patient_first_datetime,
        patient_last_datetime,
    )

    st.subheader(f"Clinical Timeline — selected patient {subject_id}")
    st.caption("Detailed chronological list of hospital events. Waveform and observations are excluded.")

    show_active_time_window(timeline_start_datetime, timeline_end_datetime)

    if not selected_event_types:
        st.warning("Select at least one event type from the checklist on the left.")
    else:
        timeline, t_timeline = get_patient_timeline(
            person_id=subject_id,
            event_types=selected_event_types,
            limit=row_limit,
            start_datetime=timeline_start_datetime,
            end_datetime=timeline_end_datetime,
        )

        st.caption(f"Loaded in {t_timeline:.3f} s")

        if len(timeline) == 0:
            st.info("No clinical events found.")
        else:
            timeline = sort_by_datetime(timeline, "event_datetime")

            display_cols = [
                "event_datetime",
                "event_type",
                "concept_name",
                "value_numeric",
                "unit_name",
                "value_text",
                "source_value",
                "visit_occurrence_id",
            ]

            timeline_display = timeline[[c for c in display_cols if c in timeline.columns]].reset_index(drop=True)

            st.dataframe(
                timeline_display,
                use_container_width=True,
            )

            fig = px.scatter(
                timeline,
                x="event_datetime",
                y="event_type",
                color="event_type",
                hover_data=[
                    "concept_name",
                    "value_numeric",
                    "unit_name",
                    "source_value",
                ],
                title="Patient clinical timeline",
            )

            st.plotly_chart(fig, use_container_width=True)

            csv = timeline.to_csv(index=False).encode("utf-8")

            st.download_button(
                "⬇️ Download timeline CSV",
                csv,
                file_name=f"patient_{subject_id}_clinical_timeline.csv",
                mime="text/csv",
            )


# ============================================================
# WAVEFORM ANALYTICS
# ============================================================

elif page == "📈 Waveform Analytics":
    st.subheader(f"Waveform-derived feature analytics — selected patient {subject_id}")

    if not has_waveform:
        st.info("This patient has no waveform-derived data.")
    else:
        waveform_concepts, t_concepts = get_waveform_concepts()
        concept_options = waveform_concepts["concept_name"].tolist()

        preferred_keywords = [
            "HRV",
            "Heart Rate Variability",
            "RMSSD",
            "SDNN",
            "Respiratory Rate",
            "Respiration",
            "Blood Pressure",
            "Mean Arterial",
            "Pleth",
            "Oxygen",
            "SpO2",
        ]

        default_features = []

        for keyword in preferred_keywords:
            for name in concept_options:
                if keyword.lower() in name.lower() and name not in default_features:
                    default_features.append(name)
                    break
            if len(default_features) >= 2:
                break

        if not default_features and concept_options:
            default_features = concept_options[: min(2, len(concept_options))]

        selected_waveform_features = st.multiselect(
            "Waveform features to visualize",
            concept_options,
            default=default_features,
        )

        if not selected_waveform_features:
            st.warning("Select at least one waveform feature.")
        else:
            raw_waveform_limit = max(row_limit * 20, 3000)

            waveform_df, t_wave = get_waveform_data_multi(
                person_id=subject_id,
                concept_names=selected_waveform_features,
                limit=raw_waveform_limit,
            )

            st.caption(f"Loaded in {(t_concepts + t_wave):.3f} s")

            if len(waveform_df) == 0:
                st.info("No waveform data found for the selected features.")
            else:
                waveform_df = sort_by_datetime(waveform_df, "event_datetime")

                wf_start, wf_end = extend_range_with_dataframe(
                    patient_first_datetime,
                    patient_last_datetime,
                    waveform_df,
                    ["event_datetime"],
                )

                waveform_start_datetime, waveform_end_datetime = render_time_window_filter(
                    "waveform",
                    "Waveform time window",
                    wf_start,
                    wf_end,
                )

                show_active_time_window(waveform_start_datetime, waveform_end_datetime)

                waveform_df = apply_time_window(
                    waveform_df,
                    "event_datetime",
                    waveform_start_datetime,
                    waveform_end_datetime,
                )

                if len(waveform_df) == 0:
                    st.info("No waveform data found inside the selected time window.")
                else:
                    waveform_df = sort_by_datetime(waveform_df, "event_datetime")

                    waveform_agg = (
                        waveform_df
                        .set_index("event_datetime")
                        .groupby("concept_name")
                        .resample("5min")["value_numeric"]
                        .agg(["count", "mean", "min", "max"])
                        .reset_index()
                    )

                    waveform_agg = waveform_agg[waveform_agg["count"] > 0]
                    waveform_agg = sort_by_datetime(waveform_agg, "event_datetime")
                    waveform_agg = waveform_agg.head(row_limit).reset_index(drop=True)

                    waveform_agg.insert(0, "include", True)

                    st.markdown("### 5-minute aggregated waveform data")
                    st.caption(
                        "Uncheck rows you want to exclude from the summary and from the chart."
                    )

                    edited_waveform_agg = st.data_editor(
                        waveform_agg,
                        use_container_width=True,
                        hide_index=False,
                        column_config={
                            "include": st.column_config.CheckboxColumn(
                                "Include",
                                help="If unchecked, this 5-minute window is excluded from the chart and summary.",
                                default=True,
                            ),
                            "event_datetime": st.column_config.DatetimeColumn(
                                "event_datetime",
                            ),
                            "concept_name": st.column_config.TextColumn(
                                "concept_name",
                                disabled=True,
                            ),
                            "count": st.column_config.NumberColumn(
                                "count",
                                disabled=True,
                            ),
                            "mean": st.column_config.NumberColumn(
                                "mean",
                                disabled=True,
                            ),
                            "min": st.column_config.NumberColumn(
                                "min",
                                disabled=True,
                            ),
                            "max": st.column_config.NumberColumn(
                                "max",
                                disabled=True,
                            ),
                        },
                        disabled=[
                            "event_datetime",
                            "concept_name",
                            "count",
                            "mean",
                            "min",
                            "max",
                        ],
                        key=f"waveform_editor_{subject_id}_{'_'.join(selected_waveform_features)}",
                    )

                    waveform_plot_df = edited_waveform_agg[
                        edited_waveform_agg["include"] == True
                    ].copy()

                    waveform_plot_df = waveform_plot_df.drop(columns=["include"])
                    waveform_plot_df = sort_by_datetime(waveform_plot_df, "event_datetime")

                    if len(waveform_plot_df) == 0:
                        st.warning("All waveform windows are unchecked. Select at least one row to show the chart and summary.")
                    else:
                        summary_df = (
                            waveform_plot_df.groupby("concept_name")["mean"]
                            .agg(["count", "mean", "min", "max"])
                            .reset_index()
                        )

                        summary_df.columns = [
                            "concept_name",
                            "n_5min_windows",
                            "mean",
                            "min",
                            "max",
                        ]

                        st.markdown("### Selected feature summary")
                        st.dataframe(
                            summary_df.reset_index(drop=True),
                            use_container_width=True,
                        )

                        fig = px.line(
                            waveform_plot_df,
                            x="event_datetime",
                            y="mean",
                            color="concept_name",
                            markers=False,
                            title=f"Selected waveform-derived features over time ({len(waveform_plot_df)} included 5-minute rows)",
                            labels={
                                "event_datetime": "Time",
                                "mean": "5-minute average",
                                "concept_name": "Feature",
                            },
                        )

                        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# MEDICATIONS
# ============================================================

elif page == "💊 Medications":
    st.subheader(f"Medication timeline — selected patient {subject_id}")

    meds, t_meds = get_patient_medications(subject_id, limit=row_limit)

    st.caption(f"Loaded in {t_meds:.3f} s")

    if len(meds) == 0:
        st.info("No medication events found.")
    else:
        meds = sort_by_datetime(meds, "start_datetime")
        meds["end_datetime"] = pd.to_datetime(meds["end_datetime"], errors="coerce")

        med_start, med_end = extend_range_with_dataframe(
            patient_first_datetime,
            patient_last_datetime,
            meds,
            ["start_datetime", "end_datetime"],
        )

        meds_start_datetime, meds_end_datetime = render_time_window_filter(
            "medications",
            "Medication time window",
            med_start,
            med_end,
        )

        show_active_time_window(meds_start_datetime, meds_end_datetime)

        meds = apply_time_window(
            meds,
            "start_datetime",
            meds_start_datetime,
            meds_end_datetime,
        )

        if len(meds) == 0:
            st.info("No medication events found inside the selected time window.")
        else:
            meds = sort_by_datetime(meds, "start_datetime")

            st.dataframe(meds.reset_index(drop=True), use_container_width=True)

            med_counts = (
                meds["medication_name"]
                .fillna("Unknown")
                .value_counts()
                .reset_index()
            )

            med_counts.columns = ["drug", "count"]

            fig = px.bar(
                med_counts.head(20),
                x="count",
                y="drug",
                orientation="h",
                title="Top medications for selected patient",
            )

            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# CONDITIONS
# ============================================================

elif page == "🩺 Conditions":
    st.subheader(f"Condition timeline — selected patient {subject_id}")

    conditions, t_cond = get_patient_conditions(subject_id, limit=row_limit)

    st.caption(f"Loaded in {t_cond:.3f} s")

    if len(conditions) == 0:
        st.info("No condition events found.")
    else:
        conditions = sort_by_datetime(conditions, "event_datetime")

        cond_start, cond_end = extend_range_with_dataframe(
            patient_first_datetime,
            patient_last_datetime,
            conditions,
            ["event_datetime"],
        )

        conditions_start_datetime, conditions_end_datetime = render_time_window_filter(
            "conditions",
            "Condition time window",
            cond_start,
            cond_end,
        )

        show_active_time_window(conditions_start_datetime, conditions_end_datetime)

        conditions = apply_time_window(
            conditions,
            "event_datetime",
            conditions_start_datetime,
            conditions_end_datetime,
        )

        if len(conditions) == 0:
            st.info("No condition events found inside the selected time window.")
        else:
            conditions = sort_by_datetime(conditions, "event_datetime")

            st.dataframe(conditions.reset_index(drop=True), use_container_width=True)

            cond_counts = conditions["concept_name"].value_counts().reset_index()
            cond_counts.columns = ["condition", "count"]

            fig = px.bar(
                cond_counts.head(20),
                x="count",
                y="condition",
                orientation="h",
                title="Top conditions for selected patient",
            )

            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# DOCTOR NOTES
# ============================================================

elif page == "📝 Doctor Notes":
    st.subheader(f"Doctor Notes — selected patient {subject_id}")

    notes_key = f"notes_visible_count_{subject_id}"

    if notes_key not in st.session_state:
        st.session_state[notes_key] = 7

    try:
        notes, t_notes = get_patient_notes(
            subject_id,
            limit=st.session_state[notes_key],
            offset=0,
        )

        st.caption(f"Loaded in {t_notes:.3f} s")

        if len(notes) == 0:
            st.info("No doctor notes found for this patient.")
        else:
            notes = sort_by_datetime(notes, "note_datetime")

            notes_start, notes_end = extend_range_with_dataframe(
                patient_first_datetime,
                patient_last_datetime,
                notes,
                ["note_datetime"],
            )

            notes_start_datetime, notes_end_datetime = render_time_window_filter(
                "notes",
                "Notes time window",
                notes_start,
                notes_end,
            )

            show_active_time_window(notes_start_datetime, notes_end_datetime)

            notes = apply_time_window(
                notes,
                "note_datetime",
                notes_start_datetime,
                notes_end_datetime,
            )

            if len(notes) == 0:
                st.info("No doctor notes found inside the selected time window.")
            else:
                notes = sort_by_datetime(notes, "note_datetime")

                for _, note in notes.iterrows():
                    title = note["note_title"] if pd.notna(note["note_title"]) else "Clinical note"
                    note_time = note["note_datetime"] if pd.notna(note["note_datetime"]) else "Unknown date"

                    with st.expander(f"{note_time} — {title}"):
                        if pd.notna(note.get("note_source_value")):
                            st.caption(str(note["note_source_value"]))

                        if pd.notna(note.get("note_text")):
                            st.write(str(note["note_text"])
)
                        else:
                            st.info("Empty note text.")

            if st.button("Load 7 more notes"):
                st.session_state[notes_key] += 7
                st.rerun()

    except Exception as e:
        st.error("Could not load notes.")
        st.exception(e)