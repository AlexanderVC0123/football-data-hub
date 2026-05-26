import os
import sys
import base64

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analytics.dashboard_metrics import calculate_competition_kpis
from app.analytics.match_analysis import compare_teams, estimate_match_probabilities
from app.config import manual_sync_enabled
from app.database.connection import execute_schema
from app.database.read_queries import (
    load_competitions,
    load_last_sync_run,
    load_matches,
    load_matches_by_team,
    load_standings,
    load_teams,
)
from app.services.import_service import sync_competition_data
from pathlib import Path
from auth_page import inicializar_sesion, mostrar_login_header, mostrar_usuario_header
from datetime import datetime, timezone


st.set_page_config(
    page_title="Football Data Hub",
    page_icon="./assets/icons/fdh_icon.ico",
    layout="wide",
)

# Asegura tablas nuevas como sync_runs antes de leer datos para construir la UI.
if "schema_checked" not in st.session_state:
    execute_schema()
    st.session_state.schema_checked = True


def apply_page_styles():
    st.markdown(
        """
        <style>
        /* Quitamos padding superior excesivo de Streamlit */
        .block-container {
            padding-top: 1.2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        /* === NAVBAR COMO BLOQUE ÚNICO === */
        .st-key-fdh_topbar {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 12px 20px;
            margin-bottom: 16px;
        }

        .st-key-fdh_topbar div[data-testid="stHorizontalBlock"] {
            align-items: center;
        }
        
        .fdh-navbar {
            background: transparent;
            border: none;
            padding: 0;
            min-height: 0;
        }

        .fdh-brand img {
            width: 42px;
            height: 42px;
            object-fit: contain;
        }

        .fdh-brand-title {
            color: #f8fafc;
            font-size: 1.15rem;
            font-weight: 800;
            margin: 0;
            line-height: 1.1;
        }

        .fdh-brand-subtitle {
            color: #94a3b8;
            font-size: 0.75rem;
            margin: 2px 0 0 0;
        }

        .st-key-fdh_topbar div[data-testid="stButton"] button {
            border-radius: 10px;
            border: 1px solid #1e293b;
            background: #111827;
            color: #e5e7eb;
            font-weight: 600;
            height: 38px;
            font-size: 0.88rem;
        }

        .st-key-fdh_topbar div[data-testid="stButton"] button:hover {
            border-color: #38bdf8;
            color: #ffffff;
            background: #172033;
        }

        .st-key-fdh_topbar div[data-testid="stPopover"] button {
            border-radius: 10px;
            border: 1px solid #1e293b;
            background: #111827;
            color: #e5e7eb;
            font-weight: 600;
            height: 38px;
            font-size: 0.88rem;
            width: 100%;
        }

        .st-key-fdh_topbar div[data-testid="stPopover"] button:hover {
            border-color: #38bdf8;
            background: #172033;
        }

        /* === DENTRO DEL POPOVER === */
        div[data-testid="stForm"] {
            background: transparent;
            border: none;
            padding: 0;
            box-shadow: none;
        }

        div[data-testid="stForm"] input {
            background: #111827;
            color: #f8fafc;
            border-radius: 8px;
            height: 38px;
        }

        .fdh-user-box {
            background: transparent;
            border: none;
            padding: 0;
            min-height: 0;
            margin-bottom: 10px;
        }

        .fdh-user-box h3 {
            margin: 0 0 4px 0;
            font-size: 0.85rem;
            color: #f8fafc;
        }

        .fdh-user-email {
            font-size: 0.8rem;
            color: #cbd5e1;
            word-break: break-word;
        }

        /* === LÍNEA DE SINCRONIZACIÓN === */
        .fdh-sync-line {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #94a3b8;
            font-size: 0.82rem;
            padding: 4px 2px;
            margin: 4px 0 16px 0;
        }

        .fdh-sync-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .fdh-sync-dot-ok {
            background: #22c55e;
            box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
        }

        .fdh-sync-dot-err {
            background: #ef4444;
            box-shadow: 0 0 6px rgba(239, 68, 68, 0.5);
        }

        .fdh-sync-dot-gray {
            background: #64748b;
        }

        /* === TABLAS HTML CUSTOM === */
        .fdh-table {
            width: 100%;
            border-collapse: collapse;
            background: #0b1220;
            color: #e5e7eb;
            border: 1px solid #1e293b;
            border-radius: 10px;
            overflow: hidden;
            font-size: 0.9rem;
        }

        .fdh-table th {
            background: #111827;
            color: #93c5fd;
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid #1e293b;
        }

        .fdh-table td {
            padding: 9px 12px;
            border-bottom: 1px solid #1f2937;
        }

        /* === ESTADO VACÍO (cuando faltan datos) === */
        .fdh-empty {
            border: 1px solid #1e293b;
            background: #0b1220;
            padding: 28px;
            border-radius: 12px;
            color: #cbd5e1;
        }

        .fdh-empty h3 {
            color: #f8fafc;
            margin: 0 0 8px 0;
        }

        /* === MÉTRICAS NATIVAS DE STREAMLIT === */
        div[data-testid="stMetric"] {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 16px 18px;
        }

        /* Label de métrica: artillería contra el CSS de Streamlit */
        div[data-testid="stMetric"] [data-testid="stMetricLabel"],
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] *,
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] p,
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] label,
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] div {
            color: #e2e8f0 !important;
            font-size: 0.82rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }

        /* Valor de métrica */
        div[data-testid="stMetric"] [data-testid="stMetricValue"],
        div[data-testid="stMetric"] [data-testid="stMetricValue"] * {
            color: #f8fafc !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            margin-top: 4px !important;
        }

        /* Valor multilínea para textos largos */
        div[data-testid="stMetric"] [data-testid="stMetricValue"] > div {
            white-space: normal !important;
            line-height: 1.3 !important;
            overflow: visible !important;
        }

        /* Delta de métrica */
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            font-size: 0.78rem !important;
            font-weight: 600 !important;
        }

        /* Caption debajo de st.metric: contexto de la comparación */
        div[data-testid="stCaptionContainer"] {
            color: #94a3b8;
            font-size: 0.75rem;
            margin-top: -8px;
            line-height: 1.4;
        }

        /* === TARJETAS DE PARTIDO === */
        .fdh-matches-block {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px 20px;
            height: 100%;
        }

        .fdh-matches-header {
            margin-bottom: 14px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1e293b;
        }

        .fdh-matches-header h3 {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            margin: 0;
        }

        .fdh-matches-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .fdh-match-card {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 12px 14px;
            transition: border-color 150ms ease;
        }

        .fdh-match-card:hover {
            border-color: #334155;
        }

        .fdh-match-jornada {
            color: #64748b;
            font-size: 0.7rem;
            font-weight: 600;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .fdh-match-body {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            gap: 12px;
        }

        .fdh-match-team {
            font-size: 0.9rem;
            font-weight: 600;
        }

        .fdh-match-team:first-of-type {
            text-align: right;
        }

        .fdh-match-team:last-of-type {
            text-align: left;
        }

        .fdh-match-team-winner { color: #f8fafc; }
        .fdh-match-team-loser { color: #64748b; }
        .fdh-match-team-draw { color: #cbd5e1; }
        .fdh-match-team-pending { color: #cbd5e1; }

        .fdh-match-score {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.2rem;
            font-weight: 800;
            padding: 0 10px;
        }

        .fdh-match-score-winner { color: #f8fafc; }
        .fdh-match-score-loser { color: #64748b; }
        .fdh-match-score-draw { color: #cbd5e1; }
        .fdh-match-score-sep { color: #475569; }

        .fdh-match-time {
            color: #38bdf8;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 0 14px;
            white-space: nowrap;
        }

        .fdh-match-meta {
            color: #64748b;
            font-size: 0.7rem;
            margin-top: 8px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .fdh-match-meta-pending {
            color: #38bdf8;
        }

        .fdh-matches-empty {
            color: #64748b;
            font-size: 0.88rem;
            padding: 24px 12px;
            text-align: center;
        }

        /* === MINI TABLA TOP + BOTTOM === */
        .fdh-mini-table {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px 20px;
        }

        .fdh-mini-header {
            margin-bottom: 14px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1e293b;
        }

        .fdh-mini-header h3 {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            margin: 0 0 4px 0;
        }

        .fdh-mini-header p {
            color: #94a3b8;
            font-size: 0.78rem;
            margin: 0;
        }

        .fdh-mini-section {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .fdh-mini-label {
            color: #64748b;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 6px;
            font-weight: 600;
        }

        .fdh-mini-divider {
            height: 1px;
            background: #1e293b;
            margin: 14px 0;
        }

        .fdh-mini-row {
            display: grid;
            grid-template-columns: 28px 1fr auto auto;
            align-items: center;
            gap: 12px;
            padding: 7px 10px;
            border-radius: 6px;
            border-left: 3px solid transparent;
        }

        .fdh-mini-champions { border-left-color: #22c55e; background: rgba(34, 197, 94, 0.04); }
        .fdh-mini-europa { border-left-color: #3b82f6; background: rgba(59, 130, 246, 0.04); }
        .fdh-mini-descenso { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.04); }

        .fdh-mini-pos {
            color: #64748b;
            font-size: 0.8rem;
            font-weight: 700;
            text-align: right;
        }

        .fdh-mini-team {
            color: #e5e7eb;
            font-size: 0.85rem;
            font-weight: 500;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .fdh-mini-played {
            color: #64748b;
            font-size: 0.75rem;
        }

        .fdh-mini-points {
            color: #f8fafc;
            font-size: 0.85rem;
            font-weight: 700;
            min-width: 50px;
            text-align: right;
        }

        /* === TABLA DE CLASIFICACIÓN COMPLETA === */
        .fdh-stand-wrapper {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            overflow: hidden;
        }

        .fdh-stand-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            color: #e5e7eb;
        }

        .fdh-stand-table thead tr {
            background: #111827;
            border-bottom: 1px solid #1e293b;
        }

        .fdh-stand-table th {
            padding: 12px 10px;
            text-align: center;
            color: #94a3b8;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            cursor: help;
        }

        .fdh-stand-table th.fdh-stand-team {
            text-align: left;
        }

        .fdh-stand-table tbody tr {
            border-bottom: 1px solid #1f2937;
            border-left: 3px solid transparent;
            transition: background-color 120ms ease;
        }

        .fdh-stand-table tbody tr:hover {
            background: rgba(56, 189, 248, 0.05);
        }

        .fdh-stand-table tbody tr:last-child {
            border-bottom: none;
        }

        .fdh-stand-table td {
            padding: 11px 10px;
            text-align: center;
            vertical-align: middle;
        }

        .fdh-stand-pos {
            color: #64748b;
            font-weight: 600;
            width: 40px;
        }

        .fdh-stand-team {
            text-align: left !important;
            font-weight: 500;
            color: #f8fafc;
            max-width: 220px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .fdh-stand-num {
            color: #cbd5e1;
            font-variant-numeric: tabular-nums;
            width: 50px;
        }

        .fdh-stand-gd {
            color: #94a3b8;
        }

        .fdh-stand-points {
            color: #f8fafc;
            font-weight: 700;
            font-size: 0.95rem;
            width: 60px;
        }

        .fdh-stand-form {
            width: 150px;
        }

        /* Franjas de color por zona */
        .fdh-stand-champions {
            border-left-color: #22c55e !important;
            background: rgba(34, 197, 94, 0.04);
        }

        .fdh-stand-europa {
            border-left-color: #3b82f6 !important;
            background: rgba(59, 130, 246, 0.04);
        }

        .fdh-stand-descenso {
            border-left-color: #ef4444 !important;
            background: rgba(239, 68, 68, 0.04);
        }

        /* Cuadritos de forma dentro de la tabla (más pequeños que en el panel) */
        .fdh-form-squares-inline {
            display: flex;
            gap: 3px;
            justify-content: center;
            align-items: center;
        }

        .fdh-form-squares-inline .fdh-form-square {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            font-size: 0.62rem;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #f8fafc;
        }

        .fdh-form-squares-inline .fdh-form-win {
            background: #16a34a;
            color: #f8fafc;
            box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.3);
        }

        .fdh-form-squares-inline .fdh-form-draw {
            background: #64748b;
            color: #f8fafc;
            box-shadow: 0 0 0 1px rgba(100, 116, 139, 0.3);
        }

        .fdh-form-squares-inline .fdh-form-loss {
            background: #dc2626;
            color: #f8fafc;
            box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.3);
        }

        .fdh-form-squares-inline .fdh-form-empty {
            background: #1e293b;
            color: #475569;
        }

        /* === LEYENDA DE LA TABLA DE CLASIFICACIÓN === */
        .fdh-stand-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            align-items: center;
            padding: 10px 4px 0 4px;
            margin-top: 10px;
            font-size: 0.78rem;
            color: #94a3b8;
        }

        .fdh-legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .fdh-legend-dot {
            width: 10px;
            height: 10px;
            border-radius: 3px;
            display: inline-block;
        }

        .fdh-legend-champions { background: #22c55e; }
        .fdh-legend-europa { background: #3b82f6; }
        .fdh-legend-descenso { background: #ef4444; }

        .fdh-legend-text {
            color: #64748b;
            margin-left: auto;
            font-style: italic;
        }

        /* === HEADER DE EQUIPO === */
        .fdh-team-header {
            background: linear-gradient(135deg, #0b1220 0%, #111827 100%);
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 22px 26px;
            margin: 8px 0 18px 0;
        }

        .fdh-team-header-left {
            display: flex;
            align-items: center;
            gap: 18px;
        }

        .fdh-team-pos-badge {
            background: #111827;
            border: 1px solid #334155;
            color: #f8fafc !important;
            font-size: 1.5rem;
            font-weight: 800;
            padding: 10px 16px;
            border-radius: 12px;
            min-width: 70px;
            text-align: center;
        }

        .fdh-team-header-info {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .fdh-team-name {
            color: #f8fafc !important;
            font-size: 1.6rem !important;
            font-weight: 800 !important;
            margin: 0 !important;
            line-height: 1.1 !important;
            padding: 0 !important;
        }

        .fdh-team-subtitle {
            display: flex;
            align-items: center;
            gap: 14px;
            flex-wrap: wrap;
        }

        .fdh-zone-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .fdh-zone-champions {
            background: rgba(34, 197, 94, 0.15);
            color: #4ade80 !important;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }

        .fdh-zone-europa {
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa !important;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .fdh-zone-descenso {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171 !important;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .fdh-zone-mid {
            background: rgba(100, 116, 139, 0.15);
            color: #94a3b8 !important;
            border: 1px solid rgba(100, 116, 139, 0.3);
        }

        .fdh-team-points {
            color: #cbd5e1 !important;
            font-size: 0.92rem;
            font-weight: 600;
        }

        /* === FORMA RECIENTE EXTENDIDA (en pestaña Equipo) === */
        .fdh-form-extended {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 20px 22px;
            margin: 8px 0 18px 0;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .fdh-form-extended-squares {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .fdh-form-square-large {
            width: 32px;
            height: 32px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85rem;
            font-weight: 700;
            color: #f8fafc !important;
        }

        .fdh-form-square-large.fdh-form-win {
            background: #16a34a;
            box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.3);
        }

        .fdh-form-square-large.fdh-form-draw {
            background: #64748b;
            box-shadow: 0 0 0 1px rgba(100, 116, 139, 0.3);
        }

        .fdh-form-square-large.fdh-form-loss {
            background: #dc2626;
            box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.3);
        }

        .fdh-form-extended-stats {
            display: flex;
            gap: 18px;
            flex-wrap: wrap;
            padding-top: 4px;
            border-top: 1px solid #1e293b;
            padding-top: 14px;
        }

        .fdh-form-stat {
            color: #94a3b8;
            font-size: 0.88rem;
        }

        .fdh-form-stat strong {
            color: #f8fafc;
            font-weight: 700;
            font-size: 1rem;
            margin-right: 4px;
        }

        .fdh-form-stat-points {
            margin-left: auto;
            color: #cbd5e1;
        }

        .fdh-form-stat-points strong {
            color: #38bdf8;
        }

        /* === ENFRENTAMIENTOS === */
        .fdh-vs-label {
            text-align: center;
            color: #64748b;
            font-size: 1.4rem;
            font-weight: 800;
            padding-top: 30px;
            letter-spacing: 0.1em;
        }

        .fdh-vs-header {
            background: linear-gradient(135deg, #0b1220 0%, #111827 50%, #0b1220 100%);
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 26px 30px;
            margin: 16px 0 22px 0;
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            gap: 20px;
        }

        .fdh-vs-team {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
        }

        .fdh-vs-team-home {
            align-items: flex-end;
            text-align: right;
        }

        .fdh-vs-team-away {
            align-items: flex-start;
            text-align: left;
        }

        .fdh-vs-team-pos {
            color: #94a3b8;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .fdh-vs-team-name {
            color: #f8fafc !important;
            font-size: 1.4rem;
            font-weight: 800;
            line-height: 1.1;
        }

        .fdh-vs-team-points {
            color: #38bdf8;
            font-size: 0.92rem;
            font-weight: 600;
        }

        .fdh-vs-divider {
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 80px;
        }

        .fdh-vs-divider-text {
            color: #475569;
            font-size: 2.2rem;
            font-weight: 900;
            letter-spacing: 0.05em;
        }

        /* === STATS COMPARATIVAS (cards a la derecha del radar) === */
        .fdh-stats-block {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .fdh-stat-row {
            display: grid;
            grid-template-columns: 1fr 1.5fr 1fr;
            align-items: center;
            gap: 12px;
            padding: 9px 4px;
            border-bottom: 1px solid #1e293b;
        }

        .fdh-stat-row:last-child {
            border-bottom: none;
        }

        .fdh-stat-value {
            font-size: 1rem;
            font-weight: 700;
            text-align: center;
        }

        .fdh-stat-value-winner {
            color: #4ade80;
        }

        .fdh-stat-value-loser {
            color: #64748b;
        }

        .fdh-stat-value-draw {
            color: #cbd5e1;
        }

        .fdh-stat-label {
            color: #94a3b8;
            font-size: 0.8rem;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 500;
        }

        /* === PREDICCIÓN 1X2 === */
        .fdh-pred-block {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px 22px;
            margin: 4px 0 18px 0;
        }

        .fdh-pred-header {
            color: #f8fafc;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .fdh-pred-bars {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .fdh-pred-row {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .fdh-pred-row-label {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }

        .fdh-pred-team-name {
            color: #cbd5e1;
            font-size: 0.9rem;
            font-weight: 600;
        }

        .fdh-pred-team-value {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
        }

        .fdh-pred-bar-track {
            height: 12px;
            background: #111827;
            border-radius: 999px;
            overflow: hidden;
            border: 1px solid #1e293b;
        }

        .fdh-pred-bar {
            height: 100%;
            border-radius: 999px;
            transition: width 300ms ease;
        }

        .fdh-pred-bar-home {
            background: linear-gradient(90deg, #38bdf8 0%, #0ea5e9 100%);
        }

        .fdh-pred-bar-draw {
            background: linear-gradient(90deg, #94a3b8 0%, #64748b 100%);
        }

        .fdh-pred-bar-away {
            background: linear-gradient(90deg, #f97316 0%, #ea580c 100%);
        }

        /* === GOLES ESPERADOS (xG) === */
        .fdh-xg-block {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px 22px;
            height: 100%;
        }

        .fdh-xg-header {
            color: #f8fafc;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .fdh-xg-cards {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .fdh-xg-card {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 16px 14px;
            text-align: center;
        }

        .fdh-xg-home {
            border-color: rgba(56, 189, 248, 0.3);
        }

        .fdh-xg-away {
            border-color: rgba(249, 115, 22, 0.3);
        }

        .fdh-xg-team {
            color: #94a3b8;
            font-size: 0.78rem;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 600;
        }

        .fdh-xg-value {
            color: #f8fafc;
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1.1;
        }

        /* === MARCADORES MÁS PROBABLES === */
        .fdh-scorelines-block {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px 22px;
            height: 100%;
        }

        .fdh-scorelines-header {
            color: #f8fafc;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .fdh-scorelines-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .fdh-score-row {
            display: grid;
            grid-template-columns: 60px 1fr 60px;
            align-items: center;
            gap: 10px;
        }

        .fdh-score-label {
            color: #f8fafc;
            font-size: 0.92rem;
            font-weight: 700;
            text-align: center;
            font-variant-numeric: tabular-nums;
        }

        .fdh-score-bar-track {
            height: 8px;
            background: #111827;
            border-radius: 999px;
            overflow: hidden;
            border: 1px solid #1e293b;
        }

        .fdh-score-bar {
            height: 100%;
            background: linear-gradient(90deg, #38bdf8 0%, #0ea5e9 100%);
            border-radius: 999px;
        }

        .fdh-score-pct {
            color: #cbd5e1;
            font-size: 0.85rem;
            font-weight: 600;
            text-align: right;
        }

        /* === FORMA RECIENTE COMPARADA (en Enfrentamientos) === */
        .fdh-vs-form-card {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 18px 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .fdh-vs-form-team {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            text-align: center;
        }

        .fdh-vs-form-squares {
            display: flex;
            gap: 6px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .fdh-vs-form-empty {
            color: #64748b;
            font-size: 0.85rem;
            text-align: center;
            padding: 12px 0;
        }

        .fdh-vs-form-stats {
            display: flex;
            gap: 14px;
            justify-content: center;
            align-items: center;
            padding-top: 12px;
            border-top: 1px solid #1e293b;
            flex-wrap: wrap;
        }

        .fdh-vs-form-stat {
            color: #94a3b8;
            font-size: 0.85rem;
        }

        .fdh-vs-form-stat strong {
            color: #f8fafc;
            font-weight: 700;
            margin-right: 3px;
        }

        .fdh-vs-form-points {
            color: #cbd5e1;
        }

        .fdh-vs-form-points strong {
            color: #38bdf8;
        }

        /* === LANDING DE LOGIN === */
        .fdh-landing {
            max-width: 1100px;
            margin: 30px auto 60px auto;
            padding: 0 20px;
        }

        .fdh-landing-hero {
            text-align: center;
            padding: 50px 20px 40px 20px;
        }

        .fdh-landing-badge {
            display: inline-block;
            background: rgba(56, 189, 248, 0.10);
            border: 1px solid rgba(56, 189, 248, 0.25);
            color: #38bdf8;
            font-size: 0.85rem;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 999px;
            margin-bottom: 20px;
        }

        .fdh-landing-title {
            color: #f8fafc;
            font-size: 2.4rem;
            font-weight: 800;
            line-height: 1.15;
            margin: 0 auto 18px auto;
            max-width: 720px;
            letter-spacing: -0.01em;
        }

        .fdh-landing-subtitle {
            color: #cbd5e1;
            font-size: 1.08rem;
            line-height: 1.55;
            max-width: 640px;
            margin: 0 auto 28px auto;
        }

        .fdh-landing-hint {
            color: #94a3b8;
            font-size: 0.92rem;
            margin: 0;
        }

        .fdh-landing-hint strong {
            color: #38bdf8;
            font-weight: 600;
        }

        .fdh-landing-features {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 18px;
            margin-top: 30px;
        }

        .fdh-feature {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 22px 20px;
            transition: border-color 150ms ease, transform 150ms ease;
        }

        .fdh-feature:hover {
            border-color: #334155;
            transform: translateY(-2px);
        }

        .fdh-feature-icon {
            font-size: 1.6rem;
            margin-bottom: 12px;
        }

        .fdh-feature-title {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .fdh-feature-desc {
            color: #94a3b8;
            font-size: 0.88rem;
            line-height: 1.5;
        }

        @media (max-width: 900px) {
            .fdh-landing-features {
                grid-template-columns: 1fr;
            }
            .fdh-landing-title {
                font-size: 1.8rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str):
    st.markdown(
        f"""
        <div class="fdh-empty">
            <h3>{title}</h3>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_login_landing():
    """Landing que se muestra cuando el usuario no ha iniciado sesión."""
    st.markdown(
        """
        <div class="fdh-landing">
            <div class="fdh-landing-hero">
                <div class="fdh-landing-badge">⚽ Football Data Hub</div>
                <h1 class="fdh-landing-title">
                    Análisis y predicciones de las cinco grandes ligas europeas
                </h1>
                <p class="fdh-landing-subtitle">
                    Datos en tiempo real, estadísticas avanzadas y modelos de predicción
                    sobre LaLiga, Premier League, Serie A, Bundesliga y Ligue 1.
                </p>
                <p class="fdh-landing-hint">
                    Pulsa <strong>Acceder</strong> en la esquina superior derecha para iniciar sesión.
                </p>
            </div>
            <div class="fdh-landing-features">
                <div class="fdh-feature">
                    <div class="fdh-feature-icon">📊</div>
                    <div class="fdh-feature-title">Estadísticas actualizadas</div>
                    <div class="fdh-feature-desc">
                        Sincronización automática cada 6 horas desde football-data.org.
                        Clasificaciones, goles, defensas y rendimiento al día.
                    </div>
                </div>
                <div class="fdh-feature">
                    <div class="fdh-feature-icon">⚖️</div>
                    <div class="fdh-feature-title">Comparador de equipos</div>
                    <div class="fdh-feature-desc">
                        Enfrenta a cualquier pareja de equipos de la misma competición
                        y compara métricas clave de rendimiento.
                    </div>
                </div>
                <div class="fdh-feature">
                    <div class="fdh-feature-icon">🎯</div>
                    <div class="fdh-feature-title">Predicciones por modelo</div>
                    <div class="fdh-feature-desc">
                        Probabilidades 1X2, goles esperados y marcadores más probables
                        calculados con un modelo de Poisson sobre los últimos partidos.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()
    

def render_brand():
    BASE_DIR = Path(__file__).resolve().parent.parent
    logo_path = BASE_DIR / "assets" / "branding" / "fdh_logo_web_512.webp"
    logo_base64 = image_to_base64(logo_path)
    

    st.markdown(
        f"""
        <div class="fdh-navbar">
            <div class="fdh-brand">
                <img src="data:image/webp;base64,{logo_base64}" alt="FDH logo">
                <div>
                    <p class="fdh-brand-title">Football Data Hub</p>
                    <p class="fdh-brand-subtitle">Football analytics dashboard</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def cambiar_pagina(nombre_pagina):
    st.session_state.pagina_actual = nombre_pagina

def render_navigation():
    if "pagina_actual" not in st.session_state:
        st.session_state.pagina_actual = "Resumen"

    paginas = [
        "Resumen",
        "Clasificación",
        "Partidos",
        "Equipo",
        "Enfrentamientos"
    ]

    cols = st.columns(len(paginas))

    for col, pagina in zip(cols, paginas):
        with col:
            if st.button(pagina, key=f"nav_{pagina}", use_container_width=True):
                cambiar_pagina(pagina)
        
    return st.session_state.pagina_actual

def render_topbar():

    inicializar_sesion()

    with st.container(key="fdh_topbar"):

        col_brand, col_nav, col_user = st.columns([2,4, 1.2], gap="small", vertical_alignment="center",)

        with col_brand:
            render_brand()
        
        with col_nav:
            selected_page = render_navigation()

        with col_user:
            if st.session_state.logueado:
                mostrar_usuario_header()
            else:
                mostrar_login_header()
    return selected_page

def humanize_time_ago(timestamp):
    "Convierte un timestamp en tiempo legible como: 'Hace X tiempo'."
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z","+00:00"))
        except ValueError:
            return "Fecha desconocida"
    
    # pandas Timestamp también funciona; lo convertimos a datetime si hace falta
    if hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()
    
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = now - timestamp
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "hace unos segundos"
    if seconds < 3600:
        minutos = seconds // 60
        return f"hace {minutos} minuto{'s' if minutos != 1 else ''}"
    if seconds < 86400:
        horas = seconds // 3600
        return f"hace {horas} hora{'s' if horas != 1 else ''}"
    dias = seconds // 86400
    return f"hace {dias} día{'s' if dias != 1 else ''}" 

def render_sync_status(last_sync_df: pd.DataFrame):
    if last_sync_df.empty:
        st.markdown(
            '<div class="fdh-sync-line>'
            '<span class="fdh-sync-dot fdh-sync-dot-gray"></span>'
            'Sincronizaciones registradas'
            '</div>',
            unsafe_allow_html=True
        )
        return
    last_sync = last_sync_df.iloc[0]
    ok = last_sync["status"] == "SUCCESS"
    when = humanize_time_ago(last_sync["finished_at"])

    dot_class = "fdh-sync-dot-ok" if ok else "fdh-sync-dot-err"
    label = "correcta" if ok else "fallida"

    st.markdown(
        f'<div class="fdh-status">'
        f'<span class="fdh-sync-dot{dot_class}"></span>'
        f'Última actualización · {when} · {label}'
        f'</div>'
        , unsafe_allow_html=True
    
    )


def render_dark_table(df: pd.DataFrame, max_rows: int | None = None):
    display_df = df.head(max_rows) if max_rows else df
    html = display_df.to_html(index=False, classes="fdh-table", border=0, escape=True)
    st.markdown(html, unsafe_allow_html=True)


def configure_plot(fig, height: int = 420, show_colorscale: bool = False):
    """
    Aplica el tema visual unificado a un gráfico de Plotly.
    
    Args:
        fig: figura de Plotly
        height: alto en píxeles
        show_colorscale: si True, muestra la barra de color lateral
                         (útil solo en scatters donde el color codifica una dimensión extra)
    """
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font_color="#cbd5e1",
        font_family="Source Sans Pro, system-ui, sans-serif",
        font_size=12,
        height=height,
        margin=dict(l=50, r=20, t=50, b=50),
        title=dict(
            font=dict(color="#f8fafc", size=14, family="Source Sans Pro, system-ui, sans-serif"),
            x=0.02,
            xanchor="left",
        ),
        xaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#1e293b",
            linecolor="#1e293b",
            tickfont=dict(color="#94a3b8", size=11),
            title_font=dict(color="#cbd5e1", size=12),
        ),
        yaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#1e293b",
            linecolor="#1e293b",
            tickfont=dict(color="#94a3b8", size=11),
            title_font=dict(color="#cbd5e1", size=12),
        ),
        hoverlabel=dict(
            bgcolor="#111827",
            bordercolor="#334155",
            font=dict(color="#f8fafc", family="Source Sans Pro, system-ui, sans-serif", size=12),
        ),
        coloraxis_showscale=show_colorscale,
        showlegend=False,
    )
    return fig


apply_page_styles()

def get_team_recent_form(team_name: str, matches_df: pd.DataFrame, n: int=5) -> list:
    """
    Devuelve la lista de los N últimos resultados(más reciente primero)
    Cada resultado es 'W', 'D', o 'L'
    """
    if matches_df.empty:
        return []
    
    finished = matches_df[matches_df["status"] == "FINISHED"].copy()
    if finished.empty:
        return []
    
    played = finished[
        (finished["home_team"] == team_name) | (finished["away_team"] == team_name)
    ].copy()

    if played.empty:
        return []
    
    played["utc_date"] = pd.to_datetime(played["utc_date"], errors="coerce")
    played = played.sort_values("utc_date", ascending=False).head(n)

    results = []
    for _, match in played.iterrows():
        is_home = match["home_team"] == team_name
        team_goals = match["home_score"] if is_home else match["away_score"]
        opp_goals = match["away_score"] if is_home else match["home_score"]

        if pd.isna(team_goals) or pd.isna(opp_goals):
            continue
        if team_goals > opp_goals:
            results.append("W")
        elif team_goals < opp_goals:
            results.append("L")
        else:
            results.append("D")
    return results

def style_standings_table(df: pd.DataFrame):
    """Aplica color de fondo según zona de la clasificación."""
    total_teams = len(df)
    descenso_from = total_teams - 2

    def color_row(row):
        pos = row["Posición"]
        if pos <= 4:
            return ["background-color: rgba(34, 197, 94, 0.08)"] * len(row)
        if pos <=6:
            return ["background-color: rgba(59, 130, 246, 0.08)"] * len(row)
        if pos >= descenso_from:
            return ["background-color: rgba(239, 68, 68, 0.08)"] * len(row)
        return [""] * len(row)
    
    styled = df.style.apply(color_row, axis=1)
    styled = styled.set_properties(**{
        "color": "#e5e7eb",
        "font-size": "0.88rem",
    })

    return styled

def render_match_card(home_team, away_team, home_score, away_score,
                      match_date, status, matchday=None):
    """
    Renderiza una tarjeta de partido individual estilo Sofascore.
    Marcador centrado y grande si está finalizado; hora/fecha si está pendiente.
    """

    is_finished = status == "FINISHED"
    if is_finished and pd.notna(home_score) and pd.notna(away_score):
        #Determinar el ganador para resaltar
        if home_score > away_score:
            home_class, away_class = "fdh-match-team-winner", "fdh-match-team-loser"
        elif home_score < away_score:
            home_class, away_class = "fdh-match-team-loser", "fdh-match-team-winner"
        else:
            home_class, away_class = "fdh-match-team-draw", "fdh-match-team-draw"
        
        score_html = (
            f'<div class="fdh-match-score">'
            f'<span class="{home_class.replace("team-", "score-")}">{int(home_score)}</span>'
            f'<span class="fdh-match-score-sep">-</span>'
            f'<span class="{away_class.replace("team-", "score-")}">{int(away_score)}</span>'
            f'</div>'
        )
        meta_html = '<div class="fdh-match-meta">Finalizado</div>'
    else:
        home_class = away_class = "fdh-match-team-pending"
        try:
            date_str = pd.to_datetime(match_date).strftime("%d %b · %H:%M")
        except Exception:
            date_str = ""
        score_html = f'<div class="fdh-match-time">{date_str}</div>'
        meta_html = '<div class="fdh-match-meta fdh-match-meta-pending">Pendiente</div>'
    
    matchday_html = (
        f'<div class="fdh-match-jornada">J{int(matchday)}</div>' 
        if matchday is not None and pd.notna(matchday) else ""
    )
    
    return (
        f'<div class="fdh-match-card">'
        f'{matchday_html}'
        f'<div class="fdh-match-body">'
        f'<div class="fdh-match-team {home_class}">{home_team}</div>'
        f'{score_html}'
        f'<div class="fdh-match-team {away_class}">{away_team}</div>'
        f'</div>'
        f'{meta_html}'
        f'</div>'
    )


def render_matches_list(matches_df: pd.DataFrame, title: str, empty_text: str, limit: int = 6):
    """Renderiza una lista de partidos con título y estado vacío."""
    cards_html = ""
    if matches_df.empty:
        cards_html = f'<div class="fdh-matches-empty">{empty_text}</div>'
    else:
        for _, match in matches_df.head(limit).iterrows():
            cards_html += render_match_card(
                home_team=match["home_team"],
                away_team=match["away_team"],
                home_score=match.get("home_score"),
                away_score=match.get("away_score"),
                match_date=match["utc_date"],
                status=match["status"],
                matchday=match.get("matchday"),
            )

    block_html = (
        f'<div class="fdh-matches-block">'
        f'<div class="fdh-matches-header"><h3>{title}</h3></div>'
        f'<div class="fdh-matches-list">{cards_html}</div>'
        f'</div>'
    )
    
    st.markdown(block_html, unsafe_allow_html=True)

def render_top_bottom_table(standings_df: pd.DataFrame):
    """Muestra los 5 primeros y los 3 últimos de la clasificación."""
    if standings_df.empty:
        return
    
    sorted_df = standings_df.sort_values("position")
    top5 = sorted_df.head(5)
    bottom3 = sorted_df.tail(3)
    
    def row_html(row, zone_class=""):
        return (
            f'<div class="fdh-mini-row {zone_class}">'
            f'<span class="fdh-mini-pos">{int(row['position'])}</span>'
            f'<span class="fdh-mini-team">{row['team']}</span>'
            f'<span class="fdh-mini-played">{int(row['played_games'])} PJ</span>'
            f'<span class="fdh-mini-points">{int(row['points'])} pts</span>'
            f'</div>'
        )
    
    top_rows = ""
    for _, row in top5.iterrows():
        zone = "fdh-mini-champions" if row["position"] <= 4 else "fdh-mini-europa"
        top_rows += row_html(row, zone)
    
    bottom_rows = ""
    for _, row in bottom3.iterrows():
        bottom_rows += row_html(row, "fdh-mini-descenso")
    
    block_html = (
        f'<div class="fdh-mini-table">'
        f'<div class="fdh-mini-header">'
        f'<h3>Clasificación</h3>'
        f'<p>5 primeros y 3 últimos</p>'
        f'</div>'
        f'<div class="fdh-mini-section">'
        f'<div class="fdh-mini-label">Cabeza</div>'
        f'{top_rows}'
        f'</div>'
        f'<div class="fdh-mini-divider"></div>'
        f'<div class="fdh-mini-section">'
        f'<div class="fdh-mini-label">Cola</div>'
        f'{bottom_rows}'
        f'</div>'
        f'</div>'
    )
    st.markdown(block_html, unsafe_allow_html=True)

def form_squares_html(results: list, max_n: int=5) -> str:
    """Genera HTML con cuadros coloreados WWDLW para una lista de resultados"""
    results_display = list(reversed(results))

    squares = ""
    #Rellenamos con vacíos si hace falta
    for _ in range(max_n - len(results_display)):
        squares += '<span class="fdh-form-square fdh-form-empty">·</span>'

    for r in results_display:
        css_class = {
            "W": "fdh-form-win",
            "D": "fdh-form-draw",
            "L": "fdh-form-loss", 
        }.get(r, "fdh-form-empty")
        squares += f'<span class="fdh-form-square {css_class}">{r}</span>'
    
    return f'<div class="fdh-form-squares-inline">{squares}</div>'

def render_standings_table_html(standings_df: pd.DataFrame, matches_df: pd.DataFrame):
    """
    Renderiza la tabla de clasificación completa con HTML
    """
    if standings_df.empty:
        return
    
    total_teams = len(standings_df)
    descenso_from = total_teams-3

    rows_html = ""
    for _, row in standings_df.iterrows():
        pos = int(row["position"])

        #Determinar zona y clase de color
        if pos <= 4:
            zone_class = "fdh-stand-champions"
        elif pos <= 6:
            zone_class = "fdh-stand-europa"
        elif pos > descenso_from:
            zone_class = "fdh-stand-descenso"
        else:
            zone_class = ""

        recent_form = get_team_recent_form(row["team"], matches_df, n=5)
        form_html = form_squares_html(recent_form, max_n=5)

        print(f" recent_form n=5 = {recent_form}")
        print(f" form_html max_n=5 = {form_html}")

        rows_html += (
            f'<tr class="{zone_class}">'
            f'<td class="fdh-stand-pos">{pos}</td>'
            f'<td class="fdh-stand-team">{row["team"]}</td>'
            f'<td class="fdh-stand-num">{int(row["played_games"])}</td>'
            f'<td class="fdh-stand-num">{int(row["won"])}</td>'
            f'<td class="fdh-stand-num">{int(row["draw"])}</td>'
            f'<td class="fdh-stand-num">{int(row["lost"])}</td>'
            f'<td class="fdh-stand-num">{int(row["goals_for"])}</td>'
            f'<td class="fdh-stand-num">{int(row["goals_against"])}</td>'
            f'<td class="fdh-stand-num fdh-stand-gd">{int(row["goal_difference"]):+d}</td>'
            f'<td class="fdh-stand-form">{form_html}</td>'
            f'<td class="fdh-stand-points">{int(row["points"])}</td>'
            f'</tr>'
        )

        table_html = (
        '<div class="fdh-stand-wrapper">'
        '<table class="fdh-stand-table">'
        '<thead>'
        '<tr>'
        '<th class="fdh-stand-pos">#</th>'
        '<th class="fdh-stand-team">Equipo</th>'
        '<th class="fdh-stand-num" title="Partidos jugados">PJ</th>'
        '<th class="fdh-stand-num" title="Victorias">V</th>'
        '<th class="fdh-stand-num" title="Empates">E</th>'
        '<th class="fdh-stand-num" title="Derrotas">D</th>'
        '<th class="fdh-stand-num" title="Goles a favor">GF</th>'
        '<th class="fdh-stand-num" title="Goles en contra">GC</th>'
        '<th class="fdh-stand-num" title="Diferencia de goles">DG</th>'
        '<th class="fdh-stand-form">Forma</th>'
        '<th class="fdh-stand-points">Pts</th>'
        '</tr>'
        '</thead>'
        '<tbody>'
        f'{rows_html}'
        '</tbody>'
        '</table>'
        '</div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

def format_standings_table(df: pd.DataFrame):
    return df.rename(
        columns={
            "position": "Posición",
            "team": "Equipo",
            "played_games": "Partidos",
            "won": "Victorias",
            "draw": "Empates",
            "lost": "Derrotas",
            "points": "Puntos",
            "goals_for": "Goles a favor",
            "goals_against": "Goles en contra",
            "goal_difference": "Diferencia de goles",
        }
    )


def format_matches_table(df: pd.DataFrame):
    return df.rename(
        columns={
            "matchday": "Jornada",
            "utc_date": "Fecha/Hora",
            "home_team": "Local",
            "away_team": "Visitante",
            "home_score": "Gol local",
            "away_score": "Gol visitante",
            "status": "Estado",
        }
    )


def load_combined_matches(competition_id: int, *team_names: str):
    frames = [
        load_matches_by_team(team_name, competition_id=competition_id)
        for team_name in team_names
        if team_name
    ]
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates(
        subset=["matchday", "utc_date", "home_team", "away_team"],
        keep="first",
    )


def probability_chart(prediction: dict):
    labels = [
        prediction["home_team"],
        "Empate",
        prediction["away_team"],
    ]
    values = [
        prediction["home_win_probability"],
        prediction["draw_probability"],
        prediction["away_win_probability"],
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=["#1f7a4d", "#6b7280", "#2563eb"],
                text=[f"{value:.1f}%" for value in values],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title="Probabilidad estimada",
        yaxis_title="Probabilidad",
        xaxis_title="Resultado",
        yaxis_ticksuffix="%",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return configure_plot(fig, height=360)


selected_page = render_topbar()

if not st.session_state.logueado:
    render_login_landing()
    st.stop()

competitions_df = load_competitions()
if competitions_df.empty:
    render_empty_state(
        "Datos en preparación",
        "Todavía no hay competiciones cargadas. Cuando el proceso de sincronización termine, este panel mostrará las ligas disponibles automáticamente.",
    )
    st.stop()

competition_options = {
    f"{row['name']} ({row['code']})": {"id": int(row["id"]), "code": row["code"]}
    for _, row in competitions_df.iterrows()
}
selected_competition_label = st.selectbox("Competición", list(competition_options.keys()))
selected_competition = competition_options[selected_competition_label]
selected_competition_id = selected_competition["id"]
selected_competition_code = selected_competition["code"]

last_sync_df = load_last_sync_run(selected_competition_code)
render_sync_status(last_sync_df)

if manual_sync_enabled(): 
    with st.expander("Herramienta de mantenimiento"):
        if st.button("Actualizar competición desde API"):
        # La sincronización usa upserts: si el registro ya existe, se actualiza con
        # los datos nuevos de la API en vez de quedarse con informacion antigua.
            with st.spinner(f"Actualizando {selected_competition_code} desde la API..."):
                sync_competition_data(selected_competition_code)
            st.success("Datos actualizados correctamente.")
            st.rerun()

standings_df = load_standings(selected_competition_id)
teams_df = load_teams(selected_competition_id)
competition_matches_df = load_matches(selected_competition_id)
teams_list = teams_df["name"].tolist()

if standings_df.empty or not teams_list:
    render_empty_state(
        "Competición sin datos analíticos",
        "La competición existe en la base, pero aún no tiene clasificación o equipos asociados. El panel se completará después de la próxima sincronización.",
    )
    st.stop()

display_standings_df = format_standings_table(standings_df)
kpis = calculate_competition_kpis(standings_df, competition_matches_df)

#Dataframes precalculados que se usan en varias pestañas
finished_matches_df = competition_matches_df[
    competition_matches_df["status"] == "FINISHED"
].copy()
pending_matches_df = competition_matches_df[
    competition_matches_df["status"] != "FINISHED"
].copy()

if not finished_matches_df.empty:
    finished_matches_df["utc_date"] = pd.to_datetime(
        finished_matches_df["utc_date"], errors="coerce"
    )
if not pending_matches_df.empty:
    pending_matches_df["utc_date"] = pd.to_datetime(
        pending_matches_df["utc_date"], errors="coerce"
    )

if selected_page == "Resumen":
    # --- KPIs principales (lo que ya tienes) ---
    main_kpi_cols = st.columns(4)
    main_kpi_keys = ["leader", "top_attack", "best_defense", "goals_per_match"]
    
    for column, key in zip(main_kpi_cols, main_kpi_keys):
        item = kpis[key]
        with column:
            delta_val = item.get("delta_numeric")
            if delta_val is not None:
                st.metric(
                    label=item["label"],
                    value=item["value"],
                    delta=f"+{delta_val}" if delta_val > 0 else str(delta_val),
                )
                st.caption(item["detail"])
            else:
                st.metric(label=item["label"], value=item["value"])
                st.caption(item["detail"])
    
    with st.expander("Ver más indicadores"):
        secondary_kpi_cols = st.columns(4)
        secondary_kpi_keys = ["highest_scoring_match", "next_match", "completion_rate", "pending_matches"]
        
        for column, key in zip(secondary_kpi_cols, secondary_kpi_keys):
            item = kpis[key]
            with column:
                delta_val = item.get("delta_numeric")
                if delta_val is not None:
                    st.metric(
                        label=item["label"],
                        value=item["value"],
                        delta=f"+{delta_val}" if delta_val > 0 else str(delta_val),
                    )
                    st.caption(item["detail"])
                else:
                    st.metric(label=item["label"], value=item["value"])
                    st.caption(item["detail"])
    
    st.divider()
    
    # --- Resultados última jornada | Próximos partidos ---
    col_recent, col_upcoming = st.columns(2)
    
    with col_recent:
        # Última jornada con partidos finalizados
        if not finished_matches_df.empty:
            last_matchday = int(finished_matches_df["matchday"].max())
            recent_matches = finished_matches_df[
                finished_matches_df["matchday"] == last_matchday
            ].sort_values("utc_date", ascending=False)
            title = f"Última jornada · J{last_matchday}"
        else:
            recent_matches = pd.DataFrame()
            title = "Última jornada"
        
        render_matches_list(
            recent_matches,
            title=title,
            empty_text="No hay partidos finalizados todavía.",
            limit=6,
        )
    
    with col_upcoming:
        # Próximos partidos pendientes
        upcoming = pending_matches_df.sort_values("utc_date").head(6) \
            if not pending_matches_df.empty else pd.DataFrame()
        
        render_matches_list(
            upcoming,
            title="Próximos partidos",
            empty_text="No hay partidos programados.",
            limit=6,
        )
    
    st.divider()
    
    # --- Mini tabla top + bottom ---
    col_mini, col_charts = st.columns([1, 2])
    
    with col_mini:
        render_top_bottom_table(standings_df)
    
    with col_charts:
        # Aquí dejamos los 3 gráficos actuales en horizontal pequeño
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            attack_fig = px.bar(
                standings_df.sort_values("goals_for", ascending=False).head(6),
                x="team",
                y="goals_for",
                color="goals_for",
                title="Ataques más productivos",
                color_continuous_scale="Greens",
            )
            attack_fig.update_layout(xaxis_title="", yaxis_title="Goles")
            st.plotly_chart(configure_plot(attack_fig, height=320), width="stretch")
        
        with chart_col2:
            defense_fig = px.bar(
                standings_df.sort_values("goals_against", ascending=True).head(6),
                x="team",
                y="goals_against",
                color="goals_against",
                title="Defensas más sólidas",
                color_continuous_scale="Blues_r",
            )
            defense_fig.update_layout(xaxis_title="", yaxis_title="Encajados")
            st.plotly_chart(configure_plot(defense_fig, height=320), width="stretch")
            
elif selected_page == "Clasificación":
    #Layout: tabla densa a la izquierda, scatter ataque/defensa a la derecha
    col_table, col_scatter = st.columns([2, 1])

    with col_table:
        render_standings_table_html(standings_df, competition_matches_df)
        st.markdown(
            '<div class="fdh-stand-legend">'
            '<span class="fdh-legend-item"><span class="fdh-legend-dot fdh-legend-champions"></span> Champions League </span>'
            '<span class="fdh-legend-item"><span class="fdh-legend-dot fdh-legend-europa"></span> Europa League </span>'
            '<span class="fdh-legend-item"><span class="fdh-legend-dot fdh-legend-descenso"></span> Descenso </span>'
            '<span class="fdh-legend-item fdh-legend-text">Forma: últimos 5 partidos (más antiguo a más reciente)</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    
    with col_scatter:
        #Scatter ataque vs defensa
        scatter_fig = px.scatter(
            standings_df,
            x="goals_for",
            y="goals_against",
            size="points",
            color="position",
            hover_name="team",
            title="Ataque vs defensa",
            color_continuous_scale="Viridis_r",
            labels={
                "goals_for": "Goles a favor",
                "goals_against": "Goles en contra",
                "position": "Posición"
            },
        )
        scatter_fig.update_layout(
            xaxis_title="Goles a favor",
            yaxis_title="Goles en contra"
        )
        st.plotly_chart(
            configure_plot(scatter_fig, height=520, show_colorscale=True),
            width="stretch",
        )
    st.divider()

    #Debajo: grafico de diferencia de goles para toda la liga
    diff_fig = px.bar(
        standings_df.sort_values("goal_difference", ascending=False),
        x="team",
        y="goal_difference",
        title="Diferencia de goles por equipo",
        color_continuous_scale="Teal",
    )
    diff_fig.update_layout(
        xaxis_title="",
        yaxis_title="Diferencia",
    )
    st.plotly_chart(configure_plot(diff_fig, height=380), width="stretch")

elif selected_page == "Partidos":
    #Determinar todas las jornadas disponibles
    if competition_matches_df.empty:
        render_empty_state(
            "Sin partidos cargados",
            "Todavía no hay partidos registrados para esta competición",
        )
        st.stop()
    
    all_matchdays = sorted(
        competition_matches_df["matchday"].dropna().unique().astype(int),
        reverse=True
    )

    #Layout: filtros arriba, lista de partidos abajo 
    col_filter_matchday, col_filter_team, col_filter_status = st.columns([1,2,1])

    with col_filter_matchday:
        #Por defecto, la última jornada con partidos finalizados
        finished_matchdays = (
            finished_matches_df["matchday"].dropna().unique().astype(int)
            if not finished_matches_df.empty else []
        )

        default_matchday = max(finished_matchdays) if len(finished_matchdays) > 0 else all_matchdays[0]
        default_index = all_matchdays.index(default_matchday) if default_matchday in all_matchdays else 0

        selected_matchday = st.selectbox(
            "Jornada",
            all_matchdays,
            index=default_index,
            format_func=lambda j: f"Jornada {j}",
            key="matches_matchday",
        )
    with col_filter_team:
        team_filter = st.selectbox(
            "Equipo (opcional)",
            ["Todos los equipos"] + teams_list,
            key="matches_team_filter",
        )
    with col_filter_status:
        status_filter = st.selectbox(
            "Estado",
            ["Todos", "Finalizados", "Pendientes"],
            key="matches_status_filter"
        )

    #Aplicar filtros
    filtered = competition_matches_df[
        competition_matches_df["matchday"] == selected_matchday
    ].copy()

    if team_filter != "Todos los equipos":
        filtered = filtered[
            (filtered["home_team"] == team_filter) | (filtered["away_team"] == team_filter)
        ]
    
    if status_filter == "Finalizados":
        filtered = filtered[filtered["status"] == "Finished"]
    elif status_filter == "Pendientes":
        filtered = filtered[filtered["status"] != "Finished"]
    
    #Ordenar por fecha
    if not filtered.empty:
        filtered["utc_date"] = pd.to_datetime(filtered["utc_date"], errors="coerce")
        filtered = filtered.sort_values("utc_date")

    #Renderizar titulo dinámico
    title_parts = [f"Jornada {selected_matchday}"]
    if team_filter != "Todos los equipos":
        title_parts.append(f"· {team_filter}")
    title = " ".join(title_parts)

    #Renderizar lista de partidos
    render_matches_list(
        filtered,
        title=title,
        empty_text="No hay partidos que coincidan con los partidos filtrados.",
        limit=15,
    )

    #Resumen de la jornada al final si hay partidos finalizados
    finished_in_view = filtered[filtered["status"] == "FINISHED"].copy()
    if not finished_in_view.empty:
        finished_in_view["total_goals"] = (
            finished_in_view["home_score"].fillna(0) + finished_in_view["away_score"].fillna(0)
        )
        total_goals = int(finished_in_view["total_goals"].sum())
        avg_goals = finished_in_view["total_goals"].mean()
        n_matches = len(finished_in_view)
        
        st.divider()
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.metric("Partidos finalizados", n_matches)
        with stat_col2:
            st.metric("Goles totales", total_goals)
        with stat_col3:
            st.metric("Promedio por partido", f"{avg_goals:.2f}")
    
elif selected_page == "Equipo":
    if not teams_list:
        render_empty_state(
            "Sin equipos cargados",
            "No hay equipos disponibles en esta competición.",
        )
        st.stop()
    
    # Selector de equipo
    selected_team = st.selectbox(
        "Selecciona un equipo",
        teams_list,
        key="team_detail_selector",
    )
    
    # Datos del equipo desde la clasificación
    team_row = standings_df[standings_df["team"] == selected_team]
    if team_row.empty:
        render_empty_state(
            f"Sin datos para {selected_team}",
            "Este equipo no tiene datos de clasificación todavía.",
        )
        st.stop()
    
    team_data = team_row.iloc[0]
    team_position = int(team_data["position"])
    team_points = int(team_data["points"])
    team_played = int(team_data["played_games"])
    team_won = int(team_data["won"])
    team_drawn = int(team_data["draw"])
    team_lost = int(team_data["lost"])
    team_goals_for = int(team_data["goals_for"])
    team_goals_against = int(team_data["goals_against"])
    team_goal_diff = int(team_data["goal_difference"])
    
    # Determinar zona del equipo
    total_teams = len(standings_df)
    if team_position <= 4:
        zone_label = "Champions League"
        zone_class = "fdh-zone-badge fdh-zone-champions"
    elif team_position <= 6:
        zone_label = "Europa League"
        zone_class = "fdh-zone-badge fdh-zone-europa"
    elif team_position >= total_teams - 2:
        zone_label = "Descenso"
        zone_class = "fdh-zone-badge fdh-zone-descenso"
    else:
        zone_label = "Zona media"
        zone_class = "fdh-zone-badge fdh-zone-mid"
    
    # Header del equipo
    st.markdown(
        f'<div class="fdh-team-header">'
        f'<div class="fdh-team-header-left">'
        f'<div class="fdh-team-pos-badge">#{team_position}</div>'
        f'<div class="fdh-team-header-info">'
        f'<h1 class="fdh-team-name">{selected_team}</h1>'
        f'<div class="fdh-team-subtitle">'
        f'<span class="{zone_class}">{zone_label}</span>'
        f'<span class="fdh-team-points">{team_points} puntos</span>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    
    # KPIs del equipo: 4 cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        st.metric(
            label="Partidos jugados",
            value=team_played,
        )
        st.caption(f"{team_won}V · {team_drawn}E · {team_lost}D")
    
    with kpi_col2:
        st.metric(
            label="Goles a favor",
            value=team_goals_for,
        )
        avg_for = team_goals_for / team_played if team_played > 0 else 0
        st.caption(f"{avg_for:.2f} por partido")
    
    with kpi_col3:
        st.metric(
            label="Goles en contra",
            value=team_goals_against,
        )
        avg_against = team_goals_against / team_played if team_played > 0 else 0
        st.caption(f"{avg_against:.2f} por partido")
    
    with kpi_col4:
        diff_display = f"+{team_goal_diff}" if team_goal_diff > 0 else str(team_goal_diff)
        st.metric(
            label="Diferencia de goles",
            value=diff_display,
        )
        ppg = team_points / team_played if team_played > 0 else 0
        st.caption(f"{ppg:.2f} pts por partido")

    # --- Forma reciente (últimos 10 partidos) ---
    st.markdown('<h3 class="fdh-section-title">Forma reciente</h3>', unsafe_allow_html=True)
    
    recent_form_10 = get_team_recent_form(selected_team, competition_matches_df, n=10)
    
    if recent_form_10:
        # Estadísticas de la forma
        wins = recent_form_10.count("W")
        draws = recent_form_10.count("D")
        losses = recent_form_10.count("L")
        points_from_form = wins * 3 + draws
        
        # Cuadritos grandes
        form_squares_large = ""
        # Pintamos del más antiguo (izquierda) al más reciente (derecha)
        for r in reversed(recent_form_10):
            css_class = {
                "W": "fdh-form-win",
                "D": "fdh-form-draw",
                "L": "fdh-form-loss",
            }.get(r, "fdh-form-empty")
            form_squares_large += f'<span class="fdh-form-square-large {css_class}">{r}</span>'
        
        st.markdown(
            f'<div class="fdh-form-extended">'
            f'<div class="fdh-form-extended-squares">{form_squares_large}</div>'
            f'<div class="fdh-form-extended-stats">'
            f'<span class="fdh-form-stat"><strong>{wins}</strong> victorias</span>'
            f'<span class="fdh-form-stat"><strong>{draws}</strong> empates</span>'
            f'<span class="fdh-form-stat"><strong>{losses}</strong> derrotas</span>'
            f'<span class="fdh-form-stat fdh-form-stat-points"><strong>{points_from_form}</strong> pts en últimos {len(recent_form_10)}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No hay partidos finalizados para calcular la forma.")
    
    st.divider()
    
    # --- Calendario: últimos finalizados + próximos pendientes ---
    team_matches = load_matches_by_team(selected_team, competition_id=selected_competition_id)
    
    if not team_matches.empty:
        team_matches["utc_date"] = pd.to_datetime(team_matches["utc_date"], errors="coerce")
        
        team_finished = team_matches[team_matches["status"] == "FINISHED"].sort_values(
            "utc_date", ascending=False
        ).head(5)
        team_pending = team_matches[team_matches["status"] != "FINISHED"].sort_values(
            "utc_date", ascending=True
        ).head(3)
        
        col_finished, col_pending = st.columns(2)
        
        with col_finished:
            # Ordenar de más antiguo a más reciente para mostrar
            team_finished_display = team_finished.sort_values("utc_date", ascending=True)
            render_matches_list(
                team_finished_display,
                title="Últimos 5 partidos",
                empty_text="No hay partidos finalizados.",
                limit=5,
            )
        
        with col_pending:
            render_matches_list(
                team_pending,
                title="Próximos partidos",
                empty_text="No hay partidos programados.",
                limit=3,
            )
    else:
        render_empty_state(
            "Sin partidos disponibles",
            f"No se encontraron partidos para {selected_team} en esta competición.",
        )
    
    # --- Evolución de puntos jornada a jornada ---
    if not team_finished.empty:
        st.divider()
        st.markdown('<h3 class="fdh-section-title">Evolución durante la temporada</h3>', unsafe_allow_html=True)
        
        # Calcular puntos acumulados del equipo jornada a jornada
        finished_all = team_matches[team_matches["status"] == "FINISHED"].copy()
        finished_all = finished_all.dropna(subset=["home_score", "away_score"])
        finished_all = finished_all.sort_values("matchday")
        
        team_points_per_match = []
        cum_points = 0
        for _, match in finished_all.iterrows():
            is_home = match["home_team"] == selected_team
            team_goals = match["home_score"] if is_home else match["away_score"]
            opp_goals = match["away_score"] if is_home else match["home_score"]
            
            if team_goals > opp_goals:
                cum_points += 3
            elif team_goals == opp_goals:
                cum_points += 1
            
            team_points_per_match.append({
                "matchday": int(match["matchday"]),
                "points": cum_points,
            })
        
        team_evolution_df = pd.DataFrame(team_points_per_match)
        
        # Calcular media de la liga: para cada jornada, puntos promedio acumulados
        # de TODOS los equipos hasta esa jornada
        all_finished = competition_matches_df[competition_matches_df["status"] == "FINISHED"].copy()
        all_finished = all_finished.dropna(subset=["home_score", "away_score"])
        
        # Para cada equipo, calcular su puntos acumulados por jornada
        league_data = []
        all_teams = pd.unique(
            all_finished[["home_team", "away_team"]].values.ravel("K")
        )
        
        for team in all_teams:
            team_matches_subset = all_finished[
                (all_finished["home_team"] == team) | (all_finished["away_team"] == team)
            ].sort_values("matchday")
            
            cum = 0
            for _, m in team_matches_subset.iterrows():
                is_home = m["home_team"] == team
                tg = m["home_score"] if is_home else m["away_score"]
                og = m["away_score"] if is_home else m["home_score"]
                if tg > og:
                    cum += 3
                elif tg == og:
                    cum += 1
                league_data.append({
                    "team": team,
                    "matchday": int(m["matchday"]),
                    "points": cum,
                })
        
        league_df = pd.DataFrame(league_data)
        league_avg = league_df.groupby("matchday")["points"].mean().reset_index()
        league_avg["team"] = "Media de la liga"
        team_evolution_df["team"] = selected_team
        
        # Combinar para graficar las dos líneas
        plot_df = pd.concat([
            team_evolution_df[["matchday", "points", "team"]],
            league_avg[["matchday", "points", "team"]],
        ])
        
        evolution_fig = px.line(
            plot_df,
            x="matchday",
            y="points",
            color="team",
            markers=True,
            title=f"Puntos acumulados · {selected_team} vs. media de la liga",
            labels={"matchday": "Jornada", "points": "Puntos acumulados", "team": ""},
            color_discrete_map={
                selected_team: "#38bdf8",
                "Media de la liga": "#94a3b8",
            },
        )
        evolution_fig.update_traces(line=dict(width=2.5))
        evolution_fig.update_layout(
            showlegend=True,
            xaxis_title="Jornada",
            yaxis_title="Puntos acumulados",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )
        st.plotly_chart(configure_plot(evolution_fig, height=380), width="stretch")

elif selected_page == "Predicción":
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Local", teams_list, key="prediction_home")
    with col2:
        away_team = st.selectbox("Visitante", teams_list, index=min(1, len(teams_list) - 1), key="prediction_away")

    if home_team == away_team:
        st.warning("Selecciona dos equipos diferentes.")
    else:
        prediction_matches = load_combined_matches(selected_competition_id, home_team, away_team)
        prediction = estimate_match_probabilities(
            standings_df,
            prediction_matches,
            home_team,
            away_team,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"Gana {home_team}", f"{prediction['home_win_probability']}%")
        with col2:
            st.metric("Empate", f"{prediction['draw_probability']}%")
        with col3:
            st.metric(f"Gana {away_team}", f"{prediction['away_win_probability']}%")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.plotly_chart(probability_chart(prediction), width="stretch")

        with col2:
            goals_df = pd.DataFrame(
                [
                    {"team": home_team, "expected_goals": prediction["home_expected_goals"]},
                    {"team": away_team, "expected_goals": prediction["away_expected_goals"]},
                ]
            )
            fig = px.bar(
                goals_df,
                x="team",
                y="expected_goals",
                color="team",
                title="Goles esperados",
            )
            fig.update_layout(xaxis_title="", yaxis_title="Goles", showlegend=True)
            st.plotly_chart(configure_plot(fig, height=360), width="stretch")

        scorelines_df = pd.DataFrame(prediction["top_scorelines"])
        scorelines_df = scorelines_df.rename(
            columns={"score": "Marcador", "probability": "Probabilidad (%)"}
        )
        st.caption("Marcadores más probables según modelo Poisson")
        render_dark_table(scorelines_df)

        form_col1, form_col2 = st.columns(2)
        with form_col1:
            st.caption(f"Forma reciente - {home_team}")
            render_dark_table(prediction["home_summary"]["recent_matches"])
        with form_col2:
            st.caption(f"Forma reciente - {away_team}")
            render_dark_table(prediction["away_summary"]["recent_matches"])

elif selected_page == "Enfrentamientos":
    if not teams_list or len(teams_list) < 2:
        render_empty_state(
            "Sin equipos suficientes",
            "Se necesitan al menos 2 equipos para hacer un enfrentamiento.",
        )
        st.stop()
    
    # Selectores de equipos
    col_a, col_vs, col_b = st.columns([5, 1, 5])
    
    with col_a:
        home_team = st.selectbox(
            "Equipo A (local)",
            teams_list,
            index=0,
            key="enf_home",
        )
    
    with col_vs:
        st.markdown(
            '<div class="fdh-vs-label">VS</div>',
            unsafe_allow_html=True,
        )
    
    with col_b:
        # Default: el segundo de la lista
        default_idx = 1 if len(teams_list) > 1 else 0
        away_team = st.selectbox(
            "Equipo B (visitante)",
            teams_list,
            index=default_idx,
            key="enf_away",
        )
    
    if home_team == away_team:
        st.warning("Selecciona dos equipos diferentes para compararlos.")
        st.stop()
    
    # Datos de cada equipo desde la clasificación
    home_row = standings_df[standings_df["team"] == home_team]
    away_row = standings_df[standings_df["team"] == away_team]
    
    if home_row.empty or away_row.empty:
        render_empty_state(
            "Datos incompletos",
            "Uno de los equipos seleccionados no tiene datos de clasificación.",
        )
        st.stop()
    
    home_data = home_row.iloc[0]
    away_data = away_row.iloc[0]
    
    # Header VS con ambos equipos side-by-side
    st.markdown(
        f'<div class="fdh-vs-header">'
        f'<div class="fdh-vs-team fdh-vs-team-home">'
        f'<div class="fdh-vs-team-pos">#{int(home_data["position"])}</div>'
        f'<div class="fdh-vs-team-name">{home_team}</div>'
        f'<div class="fdh-vs-team-points">{int(home_data["points"])} pts</div>'
        f'</div>'
        f'<div class="fdh-vs-divider">'
        f'<div class="fdh-vs-divider-text">vs</div>'
        f'</div>'
        f'<div class="fdh-vs-team fdh-vs-team-away">'
        f'<div class="fdh-vs-team-pos">#{int(away_data["position"])}</div>'
        f'<div class="fdh-vs-team-name">{away_team}</div>'
        f'<div class="fdh-vs-team-points">{int(away_data["points"])} pts</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --- Comparativa de métricas (radar) ---
    st.markdown(
        '<h3 class="fdh-section-title">Comparativa de rendimiento</h3>',
        unsafe_allow_html=True,
    )
    
    # Métricas a comparar (eje del radar)
    metrics_labels = [
        "Puntos",
        "Victorias",
        "Goles a favor",
        "Goles en contra (inv.)",
        "Diferencia de goles",
        "Eficiencia (pts/PJ)",
    ]
    
    home_played = max(int(home_data["played_games"]), 1)
    away_played = max(int(away_data["played_games"]), 1)
    
    # Para que el radar sea comparable, normalizamos cada métrica.
    # Usamos como referencia el máximo de cada métrica en TODA la liga.
    max_points = standings_df["points"].max()
    max_wins = standings_df["won"].max()
    max_goals_for = standings_df["goals_for"].max()
    max_goals_against = standings_df["goals_against"].max()
    max_goal_diff = standings_df["goal_difference"].max()
    min_goal_diff = standings_df["goal_difference"].min()
    
    def normalize(value, vmax, vmin=0):
        """Normaliza a 0-100 para el radar."""
        if vmax == vmin:
            return 50
        return max(0, min(100, ((value - vmin) / (vmax - vmin)) * 100))
    
    home_values = [
        normalize(home_data["points"], max_points),
        normalize(home_data["won"], max_wins),
        normalize(home_data["goals_for"], max_goals_for),
        # Goles en contra invertido: menos = mejor → invertimos
        100 - normalize(home_data["goals_against"], max_goals_against),
        normalize(home_data["goal_difference"], max_goal_diff, min_goal_diff),
        normalize(home_data["points"] / home_played, max_points / 38 if max_points else 1),
    ]
    
    away_values = [
        normalize(away_data["points"], max_points),
        normalize(away_data["won"], max_wins),
        normalize(away_data["goals_for"], max_goals_for),
        100 - normalize(away_data["goals_against"], max_goals_against),
        normalize(away_data["goal_difference"], max_goal_diff, min_goal_diff),
        normalize(away_data["points"] / away_played, max_points / 38 if max_points else 1),
    ]
    
    # Construir radar con plotly graph_objects
    radar_fig = go.Figure()
    
    radar_fig.add_trace(go.Scatterpolar(
        r=home_values + [home_values[0]],
        theta=metrics_labels + [metrics_labels[0]],
        fill="toself",
        name=home_team,
        line=dict(color="#38bdf8", width=2.5),
        fillcolor="rgba(56, 189, 248, 0.20)",
        marker=dict(size=6),
    ))
    
    radar_fig.add_trace(go.Scatterpolar(
        r=away_values + [away_values[0]],
        theta=metrics_labels + [metrics_labels[0]],
        fill="toself",
        name=away_team,
        line=dict(color="#f97316", width=2.5),
        fillcolor="rgba(249, 115, 22, 0.20)",
        marker=dict(size=6),
    ))
    
    radar_fig.update_layout(
        polar=dict(
            bgcolor="#0b1220",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=False,
                gridcolor="#1e293b",
                linecolor="#1e293b",
            ),
            angularaxis=dict(
                gridcolor="#1e293b",
                linecolor="#1e293b",
                tickfont=dict(color="#cbd5e1", size=11),
            ),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
        ),
        title="Comparativa normalizada (100 = máximo de la liga)",
    )
    
    # Layout: radar a la izquierda, stats cards a la derecha
    col_radar, col_stats = st.columns([3, 2])
    
    with col_radar:
        radar_fig = configure_plot(radar_fig, height=440)
        radar_fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5,
                font=dict(color="#cbd5e1", size=12),
            ),
        )
        st.plotly_chart(radar_fig, width="stretch")
    
    with col_stats:
        # Cards de stats lado a lado: home_value | label | away_value
        def stat_row(label, home_val, away_val, suffix=""):
            # Determinar qué equipo gana en esta métrica para colorear
            try:
                hv = float(home_val) if not isinstance(home_val, str) else 0
                av = float(away_val) if not isinstance(away_val, str) else 0
                home_class = "fdh-stat-value-winner" if hv > av else "fdh-stat-value-loser"
                away_class = "fdh-stat-value-winner" if av > hv else "fdh-stat-value-loser"
                if hv == av:
                    home_class = away_class = "fdh-stat-value-draw"
            except (ValueError, TypeError):
                home_class = away_class = ""
            
            return (
                f'<div class="fdh-stat-row">'
                f'<div class="fdh-stat-value {home_class}">{home_val}{suffix}</div>'
                f'<div class="fdh-stat-label">{label}</div>'
                f'<div class="fdh-stat-value {away_class}">{away_val}{suffix}</div>'
                f'</div>'
            )
        
        home_ppg = round(home_data["points"] / home_played, 2)
        away_ppg = round(away_data["points"] / away_played, 2)
        
        stats_html = (
            '<div class="fdh-stats-block">'
            f'{stat_row("Posición", f"#{int(home_data['position'])}", f"#{int(away_data['position'])}")}'
            f'{stat_row("Puntos", int(home_data["points"]), int(away_data["points"]))}'
            f'{stat_row("Partidos jugados", int(home_data["played_games"]), int(away_data["played_games"]))}'
            f'{stat_row("Victorias", int(home_data["won"]), int(away_data["won"]))}'
            f'{stat_row("Empates", int(home_data["draw"]), int(away_data["draw"]))}'
            f'{stat_row("Derrotas", int(home_data["lost"]), int(away_data["lost"]))}'
            f'{stat_row("Goles a favor", int(home_data["goals_for"]), int(away_data["goals_for"]))}'
            f'{stat_row("Goles en contra", int(home_data["goals_against"]), int(away_data["goals_against"]))}'
            f'{stat_row("Diferencia", f"{int(home_data['goal_difference']):+d}", f"{int(away_data['goal_difference']):+d}")}'
            f'{stat_row("Pts/partido", home_ppg, away_ppg)}'
            '</div>'
        )
        
        st.markdown(stats_html, unsafe_allow_html=True)

        # --- Predicción del enfrentamiento ---
    st.divider()
    st.markdown(
        '<h3 class="fdh-section-title">Predicción del enfrentamiento</h3>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Modelo Poisson basado en el rendimiento reciente. "
        "Las probabilidades son orientativas, no garantizan resultados."
    )
    
    # Cargar partidos combinados de ambos equipos para el modelo
    prediction_matches = load_combined_matches(
        selected_competition_id,
        home_team,
        away_team,
    )
    
    try:
        prediction = estimate_match_probabilities(
            standings_df,
            prediction_matches,
            home_team,
            away_team,
        )
    except Exception as e:
        st.error(f"No se pudo calcular la predicción: {e}")
        st.stop()
    
    p_home = prediction["home_win_probability"]
    p_draw = prediction["draw_probability"]
    p_away = prediction["away_win_probability"]
    xg_home = prediction["home_expected_goals"]
    xg_away = prediction["away_expected_goals"]
    
    # Bloque 1X2 con barras horizontales gruesas estilo Sofascore
    prob_html = (
        '<div class="fdh-pred-block">'
        '<div class="fdh-pred-header">Probabilidad 1X2</div>'
        '<div class="fdh-pred-bars">'
        # Equipo local
        f'<div class="fdh-pred-row">'
        f'<div class="fdh-pred-row-label">'
        f'<span class="fdh-pred-team-name">{home_team}</span>'
        f'<span class="fdh-pred-team-value">{p_home:.1f}%</span>'
        f'</div>'
        f'<div class="fdh-pred-bar-track">'
        f'<div class="fdh-pred-bar fdh-pred-bar-home" style="width:{p_home}%;"></div>'
        f'</div>'
        f'</div>'
        # Empate
        f'<div class="fdh-pred-row">'
        f'<div class="fdh-pred-row-label">'
        f'<span class="fdh-pred-team-name">Empate</span>'
        f'<span class="fdh-pred-team-value">{p_draw:.1f}%</span>'
        f'</div>'
        f'<div class="fdh-pred-bar-track">'
        f'<div class="fdh-pred-bar fdh-pred-bar-draw" style="width:{p_draw}%;"></div>'
        f'</div>'
        f'</div>'
        # Equipo visitante
        f'<div class="fdh-pred-row">'
        f'<div class="fdh-pred-row-label">'
        f'<span class="fdh-pred-team-name">{away_team}</span>'
        f'<span class="fdh-pred-team-value">{p_away:.1f}%</span>'
        f'</div>'
        f'<div class="fdh-pred-bar-track">'
        f'<div class="fdh-pred-bar fdh-pred-bar-away" style="width:{p_away}%;"></div>'
        f'</div>'
        f'</div>'
        '</div>'
        '</div>'
    )
    
    st.markdown(prob_html, unsafe_allow_html=True)
    
    # Bloque inferior: xG + tabla de marcadores
    col_xg, col_score = st.columns([1, 1])
    
    with col_xg:
        # Cards de goles esperados
        xg_html = (
            '<div class="fdh-xg-block">'
            '<div class="fdh-xg-header">Goles esperados (xG)</div>'
            '<div class="fdh-xg-cards">'
            f'<div class="fdh-xg-card fdh-xg-home">'
            f'<div class="fdh-xg-team">{home_team}</div>'
            f'<div class="fdh-xg-value">{xg_home:.2f}</div>'
            f'</div>'
            f'<div class="fdh-xg-card fdh-xg-away">'
            f'<div class="fdh-xg-team">{away_team}</div>'
            f'<div class="fdh-xg-value">{xg_away:.2f}</div>'
            f'</div>'
            '</div>'
            '</div>'
        )
        st.markdown(xg_html, unsafe_allow_html=True)
    
    with col_score:
        # Marcadores más probables
        scorelines = prediction.get("top_scorelines", [])
        if scorelines:
            rows = ""
            for sc in scorelines[:5]:
                rows += (
                    f'<div class="fdh-score-row">'
                    f'<span class="fdh-score-label">{sc["score"]}</span>'
                    f'<div class="fdh-score-bar-track">'
                    f'<div class="fdh-score-bar" style="width:{sc["probability"] * 4}%;"></div>'
                    f'</div>'
                    f'<span class="fdh-score-pct">{sc["probability"]:.1f}%</span>'
                    f'</div>'
                )
            
            scorelines_html = (
                '<div class="fdh-scorelines-block">'
                '<div class="fdh-scorelines-header">Marcadores más probables</div>'
                f'<div class="fdh-scorelines-list">{rows}</div>'
                '</div>'
            )
            st.markdown(scorelines_html, unsafe_allow_html=True)

        # --- Forma reciente comparada ---
    st.divider()
    st.markdown(
        '<h3 class="fdh-section-title">Forma reciente comparada</h3>',
        unsafe_allow_html=True,
    )
    
    col_form_home, col_form_away = st.columns(2)
    
    def render_form_compact_card(team_name: str, accent_color: str):
        """Renderiza una card compacta con la forma reciente de un equipo."""
        recent = get_team_recent_form(team_name, competition_matches_df, n=5)
        
        if not recent:
            squares_html = '<div class="fdh-vs-form-empty">Sin datos suficientes</div>'
            wins = draws = losses = points = 0
        else:
            squares = ""
            for r in reversed(recent):
                css_class = {
                    "W": "fdh-form-win",
                    "D": "fdh-form-draw",
                    "L": "fdh-form-loss",
                }.get(r, "fdh-form-empty")
                squares += f'<span class="fdh-form-square-large {css_class}">{r}</span>'
            squares_html = f'<div class="fdh-vs-form-squares">{squares}</div>'
            
            wins = recent.count("W")
            draws = recent.count("D")
            losses = recent.count("L")
            points = wins * 3 + draws
        
        card_html = (
            f'<div class="fdh-vs-form-card" style="border-top: 3px solid {accent_color};">'
            f'<div class="fdh-vs-form-team">{team_name}</div>'
            f'{squares_html}'
            f'<div class="fdh-vs-form-stats">'
            f'<span class="fdh-vs-form-stat"><strong>{wins}</strong>V</span>'
            f'<span class="fdh-vs-form-stat"><strong>{draws}</strong>E</span>'
            f'<span class="fdh-vs-form-stat"><strong>{losses}</strong>D</span>'
            f'<span class="fdh-vs-form-stat fdh-vs-form-points"><strong>{points}</strong> pts</span>'
            f'</div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)
    
    with col_form_home:
        render_form_compact_card(home_team, "#38bdf8")
    
    with col_form_away:
        render_form_compact_card(away_team, "#f97316")
