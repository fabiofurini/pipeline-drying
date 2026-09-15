"""Streamlit interface for the dry-air and vacuum drying engines.

Run with:  streamlit run app/streamlit_app.py

The page is bilingual (English / Italian). Every string a visitor sees comes
from `i18n.py`; the solver modules stay English-only, since they are read by
whoever maintains the physics rather than by the people using the page.

Layout: inputs in the left sidebar, results on the right. Nothing is computed
until the Run button is pressed, because a dry-air case on a fine grid can take
minutes and recomputing on every widget change would make the page unusable.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from i18n import LANGUAGES, t, warning_text  # noqa: E402
from pipeline_drying.economics import CostModel, air_campaign_cost  # noqa: E402
from pipeline_drying.io_schema import (  # noqa: E402
    AcceptanceConfig,
    AirDryingCaseConfig,
    DryAirEquipmentConfig,
    InitialAtmosphereConfig,
    InitialWaterConfig,
    PipelineConfig,
    SimulationConfig,
    ThermalConfig,
    VacuumAcceptanceConfig,
    VacuumDryingCaseConfig,
    VacuumEquipmentConfig,
    VacuumSimulationConfig,
)
from pipeline_drying.models.air_1d import run_air_drying  # noqa: E402
from pipeline_drying.models.vacuum_lumped import run_vacuum_drying  # noqa: E402
from pipeline_drying.reporting import summary_text, vacuum_summary_text  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
# demo_air.yaml rather than literature_air.yaml: the 50 km literature case
# needs far longer than its own horizon to dry, so a visitor's first click
# would return "not reached".
AIR_EXAMPLE = EXAMPLES / "demo_air.yaml"
VACUUM_EXAMPLE = EXAMPLES / "literature_vacuum.yaml"


def contiguous_spans(mask: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) index pairs of each contiguous True run in a boolean mask."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate(([idx[0]], idx[breaks + 1]))
    ends = np.concatenate((idx[breaks], [idx[-1]]))
    return list(zip(starts.tolist(), ends.tolist()))


st.set_page_config(page_title="Pipeline Drying Simulator", page_icon="💧", layout="wide")

if "air_example" not in st.session_state:
    st.session_state["air_example"] = AirDryingCaseConfig.from_yaml(AIR_EXAMPLE)
    st.session_state["vacuum_example"] = VacuumDryingCaseConfig.from_yaml(VACUUM_EXAMPLE)
air_example = st.session_state["air_example"]
vacuum_example = st.session_state["vacuum_example"]

with st.sidebar:
    language = st.selectbox("Language / Lingua", list(LANGUAGES), index=0)
lang = LANGUAGES[language]

st.title(t("title", lang))
st.caption(t("subtitle", lang))
with st.expander(t("about", lang)):
    st.markdown(t("about_text", lang))

with st.sidebar:
    process = st.radio(t("process", lang), [t("dry_air", lang), t("vacuum", lang)],
                       horizontal=True, help=t("process_help", lang))
    is_air = process == t("dry_air", lang)
    # Each engine starts from its own example: the dry-air one is a 50 km line,
    # which no realistic vacuum spread would dry in a horizon anyone waits for.
    base = air_example if is_air else vacuum_example

    st.header(t("h_pipeline", lang))
    length_km = st.number_input(t("length", lang), 0.1, 2000.0,
                                base.pipeline.length_m / 1000, step=1.0,
                                help=t("length_help", lang))
    diameter_mm = st.number_input(t("diameter", lang), 10.0, 2000.0,
                                  base.pipeline.diameter_m * 1000, step=10.0,
                                  help=t("diameter_help", lang))
    if is_air:
        n_cells = st.slider(t("cells", lang), 20, 400,
                            air_example.pipeline.n_cells, step=10,
                            help=t("cells_help", lang))
        wall_thickness_mm = vacuum_example.pipeline.wall_thickness_mm
    else:
        n_cells = 1
        wall_thickness_mm = st.number_input(t("wall_thickness", lang), 1.0, 100.0,
                                            vacuum_example.pipeline.wall_thickness_mm,
                                            help=t("wall_thickness_help", lang))
    wall_temp_c = st.number_input(t("wall_temp", lang), -60.0, 80.0,
                                  base.pipeline.wall_temperature_c,
                                  help=t("wall_temp_help", lang))

    st.header(t("h_water", lang))
    film_um = st.number_input(t("film", lang), 0.1, 5000.0,
                              base.initial_water.film_thickness_mm * 1000,
                              help=t("film_help", lang))
    ambient_dew_c = st.number_input(t("ambient_dew", lang), -80.0, 60.0,
                                    base.initial_atmosphere.dew_point_c,
                                    help=t("ambient_dew_help", lang))
    if is_air:
        trapped_pct = st.slider(t("trapped", lang), 0.0, 50.0,
                                100.0 * air_example.initial_water.trapped_fraction,
                                step=1.0, help=t("trapped_help", lang))
        release_options = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.2]
        example_ratio = air_example.simulation.trapped_transfer_ratio
        trapped_ratio = st.select_slider(
            t("release", lang), options=release_options,
            value=example_ratio if example_ratio in release_options else 0.001,
            help=t("release_help", lang))
    else:
        # Not shown for vacuum: the engine keeps all residual water in one
        # inventory, so offering the controls would imply an effect there is none.
        trapped_pct, trapped_ratio = 0.0, 0.001
        st.caption(t("trapped_vacuum_note", lang))

    if is_air:
        st.header(t("h_air_equipment", lang))
        flow_nm3_h = st.number_input(t("flow", lang), 10.0, 200000.0,
                                     air_example.equipment.volumetric_flow_nm3_h or 2000.0,
                                     help=t("flow_help", lang))
        pressure_bar = st.number_input(t("pressure", lang), 1.0, 300.0,
                                       air_example.equipment.pressure_bar_a,
                                       help=t("pressure_help", lang))
        inlet_temp_c = st.number_input(t("inlet_temp", lang), -40.0, 100.0,
                                       air_example.equipment.inlet_temperature_c,
                                       help=t("inlet_temp_help", lang))
        inlet_dew_c = st.number_input(t("inlet_dew", lang), -90.0, 20.0,
                                      air_example.equipment.inlet_dew_point_c,
                                      help=t("inlet_dew_help", lang))

        st.header(t("h_acceptance", lang))
        target_choice = st.selectbox(t("target", lang),
                                     [-20.0, -30.0, t("target_custom", lang)], index=0,
                                     help=t("target_help", lang))
        target_c = (st.number_input(t("target_custom_value", lang), -90.0, 20.0, -25.0,
                                    help=t("target_custom_value_help", lang))
                    if target_choice == t("target_custom", lang) else float(target_choice))
        hold_h = st.number_input(t("hold", lang), 0.0, 48.0,
                                 air_example.acceptance.hold_duration_s / 3600,
                                 help=t("hold_help", lang))
        quoted_atmospheric = st.checkbox(t("quoted_atm", lang), value=False,
                                         help=t("quoted_atm_help", lang))
        dryer_atmospheric = st.checkbox(t("dryer_atm", lang), value=False,
                                        help=t("dryer_atm_help", lang))

        st.header(t("h_comparison", lang))
        compare_targets = st.multiselect(
            t("compare_targets", lang), [-20.0, -30.0, -40.0, -50.0],
            default=[air_example.acceptance.target_c,
                     *air_example.acceptance.additional_targets_c],
            help=t("compare_help", lang))
        energy_price = st.number_input(t("energy_price", lang), 0.0, 5.0, 0.25, step=0.05,
                                       help=t("energy_price_help", lang))
        rental_rate = st.number_input(t("rental", lang), 0.0, 10000.0, 150.0, step=50.0,
                                      help=t("rental_help", lang))
        dryer_energy = st.number_input(t("dryer_energy", lang), 0.0, 100.0, 0.0, step=0.5,
                                       help=t("dryer_energy_help", lang))
    else:
        st.header(t("h_vac_equipment", lang))
        st.caption(t("pump_curve_note", lang))
        n_pumps = st.slider(t("n_pumps", lang), 1, 8, vacuum_example.equipment.n_pumps,
                            help=t("n_pumps_help", lang))
        use_booster = st.checkbox(t("use_booster", lang),
                                  value=vacuum_example.equipment.booster is not None,
                                  help=t("use_booster_help", lang))
        booster_activation = st.number_input(
            t("booster_activation", lang), 0.1, 500.0,
            vacuum_example.equipment.booster_activation_mbar or 20.0,
            help=t("booster_activation_help", lang))
        derating = st.slider(t("derating", lang), 0.1, 1.0,
                             vacuum_example.equipment.derating,
                             help=t("derating_help", lang))

        st.header(t("h_heat", lang))
        external_temp_c = st.number_input(t("external_temp", lang), -40.0, 60.0,
                                          vacuum_example.thermal.external_temperature_c,
                                          help=t("external_temp_help", lang))
        u_value = st.number_input(t("u_value", lang), 0.0, 500.0,
                                  vacuum_example.thermal.u_value_w_m2_k,
                                  help=t("u_value_help", lang))

        st.header(t("h_acceptance", lang))
        target_pressure_mbar = st.number_input(
            t("target_pressure", lang), 0.01, 500.0,
            vacuum_example.acceptance.target_pressure_mbar,
            help=t("target_pressure_help", lang))
        use_frost_target = st.checkbox(
            t("use_frost_target", lang),
            value=vacuum_example.acceptance.target_frost_point_c is not None,
            help=t("use_frost_target_help", lang))
        target_choice = st.selectbox(t("frost_target", lang),
                                     [-20.0, -30.0, t("target_custom", lang)], index=1,
                                     help=t("frost_target_help", lang))
        target_c = (st.number_input(t("target_custom_value", lang), -90.0, 20.0, -25.0,
                                    help=t("target_custom_value_help", lang))
                    if target_choice == t("target_custom", lang) else float(target_choice))
        drawdown_factor = st.slider(t("drawdown", lang), 0.1, 1.0,
                                    vacuum_example.acceptance.drawdown_factor,
                                    help=t("drawdown_help", lang))
        hold_h = st.number_input(t("soak", lang), 0.0, 48.0,
                                 vacuum_example.acceptance.soak_duration_s / 3600,
                                 help=t("soak_help", lang))
        max_rise_mbar = st.number_input(t("max_rise", lang), 0.001, 100.0,
                                        vacuum_example.acceptance.max_pressure_rise_mbar,
                                        format="%.3f", help=t("max_rise_help", lang))
        reference_bar = st.number_input(
            t("reference_pressure", lang), 1.0, 300.0,
            vacuum_example.acceptance.reference_pressure_bar_a or 5.0,
            help=t("reference_pressure_help", lang))
        evaporation_model = st.selectbox(t("evaporation_closure", lang),
                                         ["equilibrium", "hertz_knudsen"],
                                         help=t("evaporation_closure_help", lang))

    max_time_h = st.number_input(t("horizon", lang), 1.0, 2000.0,
                                 base.simulation.max_time_s / 3600,
                                 help=t("horizon_help", lang))
    if is_air and n_cells * max_time_h > 20000:
        st.caption(":orange[" + t("slow_warning", lang) + "]")

    run_clicked = st.button(t("run", lang), type="primary")


if run_clicked and is_air:
    config = AirDryingCaseConfig(
        name="interactive_case",
        pipeline=PipelineConfig(length_m=length_km * 1000, diameter_m=diameter_mm / 1000,
                                n_cells=n_cells, wall_temperature_c=wall_temp_c),
        initial_water=InitialWaterConfig(film_thickness_mm=film_um / 1000,
                                         trapped_fraction=trapped_pct / 100.0),
        initial_atmosphere=InitialAtmosphereConfig(dew_point_c=ambient_dew_c),
        equipment=DryAirEquipmentConfig(
            volumetric_flow_nm3_h=flow_nm3_h, pressure_bar_a=pressure_bar,
            inlet_temperature_c=inlet_temp_c, inlet_dew_point_c=inlet_dew_c,
            inlet_reference_pressure_bar_a=1.01325 if dryer_atmospheric else None),
        acceptance=AcceptanceConfig(
            target_c=target_c, hold_duration_s=hold_h * 3600,
            additional_targets_c=[x for x in compare_targets if x != target_c],
            reference_pressure_bar_a=1.01325 if quoted_atmospheric else None),
        simulation=SimulationConfig(max_time_s=max_time_h * 3600,
                                    trapped_transfer_ratio=trapped_ratio),
    )

    with st.status(t("running_air", lang), expanded=True) as status:
        st.write(t("running_detail_air", lang, cells=n_cells, hours=max_time_h))
        started = time.perf_counter()
        result = run_air_drying(config)
        status.update(label=t("done", lang, seconds=time.perf_counter() - started),
                      state="complete", expanded=False)

    col1, col2, col3 = st.columns(3)
    col1.metric(t("m_time_target", lang),
                f"{result.time_to_target_s / 3600:.1f} h"
                if result.time_to_target_s is not None else t("m_not_reached", lang))
    col2.metric(t("m_outlet_final", lang), f"{result.outlet_primary_c[-1]:.1f} C")
    col3.metric(t("m_mass_error", lang), f"{result.mass_balance_relative_error:.2e}")

    for w in result.warnings:
        st.warning(warning_text(w, lang))

    t_h = result.t_s / 3600

    fig_dew = go.Figure()
    fig_dew.add_trace(go.Scatter(x=t_h, y=result.outlet_dew_point_c,
                                 name=t("c_dew_water", lang)))
    fig_dew.add_trace(go.Scatter(x=t_h, y=result.outlet_frost_point_c,
                                 name=t("c_frost_ice", lang)))
    fig_dew.add_hline(y=config.acceptance.target_c, line_dash="dash",
                      annotation_text=t("c_target_line", lang))
    fig_dew.update_layout(title=t("c_outlet", lang), xaxis_title=t("c_time_h", lang),
                          yaxis_title=t("c_temp_c", lang))
    st.plotly_chart(fig_dew, use_container_width=True)

    fig_liq = go.Figure()
    fig_liq.add_trace(go.Scatter(x=t_h, y=result.total_liquid_water_kg,
                                 name=t("c_liquid_name", lang)))
    if trapped_pct > 0:
        fig_liq.add_trace(go.Scatter(x=t_h, y=result.total_trapped_water_kg,
                                     name=t("c_trapped_name", lang), line_dash="dash"))
    fig_liq.update_layout(title=t("c_liquid", lang), xaxis_title=t("c_time_h", lang),
                          yaxis_title=t("c_kg", lang))
    st.plotly_chart(fig_liq, use_container_width=True)

    st.subheader(t("c_axial", lang))
    fig_axial = go.Figure()
    fig_axial.add_trace(go.Scatter(x=result.x_m / 1000, y=result.liquid_water_kg[:, -1],
                                   name=t("c_axial_y", lang)))
    fig_axial.update_layout(xaxis_title=t("c_axial_x", lang),
                            yaxis_title=t("c_axial_y", lang))
    st.plotly_chart(fig_axial, use_container_width=True)

    if compare_targets:
        st.subheader(t("s_cost", lang))
        st.caption(t("s_cost_note", lang))
        model = CostModel(energy_cost_per_kwh=energy_price,
                          rental_cost_per_hour=rental_rate,
                          dryer_specific_energy_kwh_per_1000_nm3=dryer_energy)
        rows, reached = [], []
        for tgt in sorted(compare_targets, reverse=True):
            cost = air_campaign_cost(config, result, model, target_c=tgt)
            if cost.reached_target:
                reached.append((tgt, cost))
                rows.append({t("t_target", lang): f"{tgt:g}",
                             t("t_time", lang): f"{cost.duration_h:.1f}",
                             t("t_energy", lang): f"{cost.energy_kwh / 1000:.2f}",
                             t("t_cost", lang): f"{cost.total_cost:,.0f}",
                             t("t_vs", lang): "-"})
            else:
                rows.append({t("t_target", lang): f"{tgt:g}",
                             t("t_time", lang): t("m_not_reached", lang),
                             t("t_energy", lang): "-", t("t_cost", lang): "-",
                             t("t_vs", lang): "-"})
        if reached:
            base_cost = reached[0][1].total_cost
            j = 0
            for row in rows:
                if row[t("t_time", lang)] != t("m_not_reached", lang):
                    row[t("t_vs", lang)] = (
                        f"+{100 * (reached[j][1].total_cost / base_cost - 1):.0f}%"
                        if base_cost else "-")
                    j += 1
        st.table(rows)

        if len(reached) > 1:
            fig_cmp = go.Figure()
            labels = [f"{x:g} C" for x, _ in reached]
            fig_cmp.add_trace(go.Bar(x=labels, y=[c.duration_h for _, c in reached],
                                     name=t("t_time", lang), yaxis="y"))
            fig_cmp.add_trace(go.Scatter(x=labels, y=[c.total_cost for _, c in reached],
                                         name=t("c_cost_y", lang), yaxis="y2",
                                         mode="lines+markers"))
            fig_cmp.update_layout(title=t("c_cost_chart", lang),
                                  xaxis_title=t("t_target", lang),
                                  yaxis=dict(title=t("t_time", lang)),
                                  yaxis2=dict(title=t("c_cost_y", lang),
                                              overlaying="y", side="right"))
            st.plotly_chart(fig_cmp, use_container_width=True)

        if trapped_pct == 0.0:
            st.info(t("no_trapped_note", lang))

    st.subheader(t("s_summary", lang))
    st.code(summary_text(config, result))

elif run_clicked and not is_air:
    equipment = VacuumEquipmentConfig(
        pump=vacuum_example.equipment.pump, n_pumps=n_pumps,
        booster=vacuum_example.equipment.booster if use_booster else None,
        booster_activation_mbar=booster_activation if use_booster else None,
        derating=derating)
    config = VacuumDryingCaseConfig(
        name="interactive_vacuum_case",
        pipeline=PipelineConfig(length_m=length_km * 1000, diameter_m=diameter_mm / 1000,
                                n_cells=1, wall_thickness_mm=wall_thickness_mm,
                                wall_temperature_c=wall_temp_c),
        initial_water=InitialWaterConfig(film_thickness_mm=film_um / 1000,
                                         trapped_fraction=trapped_pct / 100.0),
        initial_atmosphere=InitialAtmosphereConfig(dew_point_c=ambient_dew_c),
        equipment=equipment,
        thermal=ThermalConfig(external_temperature_c=external_temp_c,
                              u_value_w_m2_k=u_value),
        acceptance=VacuumAcceptanceConfig(
            target_pressure_mbar=target_pressure_mbar, drawdown_factor=drawdown_factor,
            soak_duration_s=hold_h * 3600, max_pressure_rise_mbar=max_rise_mbar,
            target_frost_point_c=target_c if use_frost_target else None,
            reference_pressure_bar_a=reference_bar),
        simulation=VacuumSimulationConfig(max_time_s=max_time_h * 3600,
                                          evaporation_model=evaporation_model),
    )

    with st.status(t("running_vacuum", lang), expanded=True) as status:
        st.write(t("running_detail_vacuum", lang))
        started = time.perf_counter()
        result = run_vacuum_drying(config)
        status.update(label=t("done", lang, seconds=time.perf_counter() - started),
                      state="complete", expanded=False)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("m_time_acceptance", lang),
                f"{result.time_to_acceptance_s / 3600:.2f} h"
                if result.accepted else t("m_not_accepted", lang))
    col2.metric(t("m_final_pressure", lang), f"{result.pressure_pa[-1] / 100:.3g} mbar")
    col3.metric(t("m_frost_inline", lang), f"{result.frost_point_c[-1]:.1f} C")
    col4.metric(t("m_min_temp", lang), f"{result.min_temperature_c:.1f} C")

    for w in result.warnings:
        st.warning(warning_text(w, lang))

    t_h = result.t_s / 3600

    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(x=t_h, y=result.pressure_pa / 100,
                               name=t("c_total_pressure", lang)))
    fig_p.add_trace(go.Scatter(x=t_h, y=result.vapor_pressure_pa / 100,
                               name=t("c_vapour_pressure", lang)))
    fig_p.add_hline(y=config.acceptance.target_pressure_mbar, line_dash="dash",
                    annotation_text=t("c_target_line", lang))
    fig_p.update_layout(title=t("c_pressure", lang), xaxis_title=t("c_time_h", lang),
                        yaxis_title=t("c_pressure_y", lang), yaxis_type="log")
    for i, (a, b) in enumerate(contiguous_spans(result.phase == "soak")):
        fig_p.add_vrect(x0=t_h[a], x1=t_h[b], fillcolor="LightSalmon", opacity=0.25,
                        line_width=0, annotation_text=t("c_soak", lang) if i == 0 else None)
    st.plotly_chart(fig_p, use_container_width=True)

    fig_w = go.Figure()
    fig_w.add_trace(go.Scatter(x=t_h, y=result.liquid_water_kg,
                               name=t("c_liquid_name", lang)))
    fig_w.add_trace(go.Scatter(x=t_h, y=result.pumped_water_kg, name=t("c_removed", lang)))
    fig_w.update_layout(title=t("c_water_inventory", lang),
                        xaxis_title=t("c_time_h", lang), yaxis_title=t("c_kg", lang))
    st.plotly_chart(fig_w, use_container_width=True)

    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(x=t_h, y=result.temperature_c, name=t("c_film_temp", lang)))
    fig_t.add_hline(y=0.0, line_dash="dot", annotation_text=t("c_freezing", lang))
    fig_t.update_layout(title=t("c_cooling", lang), xaxis_title=t("c_time_h", lang),
                        yaxis_title=t("c_temp_c", lang))
    st.plotly_chart(fig_t, use_container_width=True)

    if result.atmospheric_frost_point_c is not None:
        st.subheader(t("s_convention", lang))
        st.caption(t("s_convention_note", lang))
        c1, c2, c3 = st.columns(3)
        c1.metric(t("m_frost_inline", lang), f"{result.frost_point_c[-1]:.1f} C")
        c2.metric(t("s_after_backfill", lang, p=reference_bar),
                  f"{result.atmospheric_frost_point_c[-1]:.1f} C")
        c3.metric(t("s_water_content", lang),
                  f"{result.water_content_ppmv_at_reference[-1]:.0f} ppmv")

    st.subheader(t("s_summary", lang))
    st.code(vacuum_summary_text(config, result))

else:
    st.info(t("idle", lang))

# Shown on every view, results or not.
st.divider()
st.subheader(t("contact_header", lang))
st.markdown(t("contact_text", lang))
st.markdown(f"**{t('contact_name', lang)}** — "
            "[fabio.furini@uniroma1.it](mailto:fabio.furini@uniroma1.it)")
st.caption(t("contact_role", lang))
