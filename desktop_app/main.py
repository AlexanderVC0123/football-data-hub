import os
import sys
from tkinter import ttk

import customtkinter as ctk
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analytics.dashboard_metrics import calculate_competition_kpis
from app.analytics.match_analysis import compare_teams, estimate_match_probabilities
from app.config import manual_sync_enabled
from app.database.connection import execute_schema
from app.services.import_service import sync_competition_data
from utils_desktop.db_utils import (
    load_combined_matches,
    load_competitions,
    load_last_sync_run,
    load_matches,
    load_matches_by_team,
    load_standings,
    load_teams,
)

from PIL import Image


# === PALETA DE COLORES (alineada con la web) ===
COLOR_BG = "#0b1220"
COLOR_SURFACE = "#111827"
COLOR_BORDER = "#1e293b"
COLOR_BORDER_LIGHT = "#334155"
COLOR_TEXT = "#f8fafc"
COLOR_TEXT_MUTED = "#cbd5e1"
COLOR_TEXT_DIM = "#94a3b8"
COLOR_TEXT_FAINT = "#64748b"

COLOR_ACCENT = "#38bdf8"      # azul cielo
COLOR_ACCENT_HOVER = "#0ea5e9"
COLOR_SUCCESS = "#22c55e"     # verde Champions
COLOR_INFO = "#3b82f6"        # azul Europa
COLOR_DANGER = "#ef4444"      # rojo descenso
COLOR_WIN = "#16a34a"
COLOR_DRAW = "#64748b"
COLOR_LOSS = "#dc2626"

# Zonas de la clasificación (versiones suaves para fondo)
COLOR_ZONE_CHAMPIONS_BG = "#0e2a1b"
COLOR_ZONE_EUROPA_BG = "#0e1d33"
COLOR_ZONE_DESCENSO_BG = "#2a0e0e"


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

#COMPONENTES REUTILIZABLES

def create_kpi_card(parent, label: str, value: str, detail:str="", accent:str | None = None):
    """Crea una KPI card parecido a la web"""
    card = ctk.CTkFrame(
        parent,
        corner_radius=12,
        fg_color=COLOR_SURFACE,
        border_width=1,
        border_color=COLOR_BORDER,
    )

    #LABEL EN UPPERCASE
    ctk.CTkLabel(
        card,
        text=label.upper(),
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=COLOR_TEXT_DIM,
        anchor="w",
    ).pack(fill="x", padx=16, pady=(14, 4))

    #Valor grande
    ctk.CTkLabel(
        card,
        text=str(value),
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=COLOR_TEXT,
        anchor="w",
        wraplength=240,
        justify="left",
    ).pack(fill="x", padx=16, pady=(0, 4))

    #Detail/caption
    if detail:
        ctk.CTkLabel(
            card,
            text=str(detail),
            font=ctk.CTkFont(size=11),
            text_color=COLOR_ACCENT if accent else COLOR_TEXT_DIM,
            anchor="w",
            wraplength=240,
            justify="left",
        ).pack(fill="x", padx=16, pady=(0, 4))

    else:
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()
    
    return card

def create_section_header(parent, title: str, subtitle: str | None = None):
    """Cabecera de sección con título y subtítulo opcional."""
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.pack(fill="x", padx=28, pady=(20, 8))
    
    ctk.CTkLabel(
        header,
        text=title,
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=COLOR_TEXT,
        anchor="w",
    ).pack(fill="x")
    
    if subtitle:
        ctk.CTkLabel(
            header,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

def create_match_card(parent, home_team: str, away_team: str, 
                       home_score, away_score, status: str, matchday=None):
    """Tarjeta de partido individual con marcador grande centrado."""
    card = ctk.CTkFrame(
        parent,
        corner_radius=10,
        fg_color=COLOR_SURFACE,
        border_width=1,
        border_color=COLOR_BORDER,
    )
    card.pack(fill="x", padx=4, pady=4)
    
    # Jornada arriba (si existe)
    if matchday is not None:
        try:
            md_int = int(matchday)
            ctk.CTkLabel(
                card,
                text=f"J{md_int}",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=COLOR_TEXT_FAINT,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(8, 0))
        except (ValueError, TypeError):
            pass
    
    # Cuerpo del partido: equipo local | marcador | equipo visitante
    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="x", padx=12, pady=(4, 8))
    
    is_finished = status == "FINISHED"
    
    if is_finished and home_score is not None and away_score is not None:
        # Determinar ganador para color
        try:
            hs = int(home_score)
            as_ = int(away_score)
        except (ValueError, TypeError):
            hs = as_ = 0
        
        if hs > as_:
            home_color, away_color = COLOR_TEXT, COLOR_TEXT_FAINT
            home_score_color, away_score_color = COLOR_TEXT, COLOR_TEXT_FAINT
        elif hs < as_:
            home_color, away_color = COLOR_TEXT_FAINT, COLOR_TEXT
            home_score_color, away_score_color = COLOR_TEXT_FAINT, COLOR_TEXT
        else:
            home_color = away_color = COLOR_TEXT_MUTED
            home_score_color = away_score_color = COLOR_TEXT_MUTED
        
        score_text = f"{hs}  -  {as_}"
    else:
        home_color = away_color = COLOR_TEXT_MUTED
        home_score_color = away_score_color = COLOR_ACCENT
        score_text = "vs"
    
    # Grid: equipo local | marcador | equipo visitante
    body.grid_columnconfigure(0, weight=1)
    body.grid_columnconfigure(1, weight=0)
    body.grid_columnconfigure(2, weight=1)
    
    ctk.CTkLabel(
        body,
        text=home_team,
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=home_color,
        anchor="e",
    ).grid(row=0, column=0, sticky="ew", padx=(0, 10))
    
    ctk.CTkLabel(
        body,
        text=score_text,
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=home_score_color,
    ).grid(row=0, column=1, padx=10)
    
    ctk.CTkLabel(
        body,
        text=away_team,
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=away_color,
        anchor="w",
    ).grid(row=0, column=2, sticky="ew", padx=(10, 0))
    
    # Estado abajo
    meta_color = COLOR_TEXT_FAINT if is_finished else COLOR_ACCENT
    meta_text = "FINALIZADO" if is_finished else "PENDIENTE"
    ctk.CTkLabel(
        card,
        text=meta_text,
        font=ctk.CTkFont(size=9, weight="bold"),
        text_color=meta_color,
    ).pack(pady=(0, 8))
    
    return card

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Football Data Hub")
        self.geometry("1440x900")
        self.minsize(1200, 760)
        self.configure(fg_color=COLOR_BG)

        # Inicialización de schema y datos
        execute_schema()
        self.configure_table_style()

        self.competitions_df = load_competitions()
        self.competition_options = {
            f"{row['name']} ({row['code']})": {"id": int(row["id"]), "code": row["code"]}
            for _, row in self.competitions_df.iterrows()
        }
        self.selected_competition = ctk.StringVar(
            value=next(iter(self.competition_options), "")
        )
        self.selected_competition_id = None
        self.refresh_competition_data()

        # Página activa para resaltar el botón seleccionado
        self.current_page = "Resumen"
        self.nav_buttons = {}

        # Layout principal: sidebar fija + main area
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=260,
            corner_radius=0,
            fg_color=COLOR_SURFACE,
        )
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.main_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
            fg_color=COLOR_BG,
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        self.create_sidebar()
        self.show_resumen()

    # ---------- ESTILO TREEVIEW ----------
    def configure_table_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            fieldbackground=COLOR_SURFACE,
            bordercolor=COLOR_BORDER,
            font=("Segoe UI", 11),
            rowheight=34,
        )
        style.configure(
            "Treeview.Heading",
            background=COLOR_BG,
            foreground=COLOR_ACCENT,
            relief="flat",
            font=("Segoe UI", 11, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", COLOR_BORDER_LIGHT)],
            foreground=[("selected", COLOR_TEXT)],
        )

    # ---------- DATOS ----------
    def refresh_competition_data(self):
        option = self.competition_options.get(self.selected_competition.get(), {})
        self.selected_competition_id = option.get("id")
        self.selected_competition_code = option.get("code")
        self.standings_df = load_standings(self.selected_competition_id)
        self.teams_df = load_teams(self.selected_competition_id)
        self.matches_df = load_matches(self.selected_competition_id)
        self.teams_list = self.teams_df["name"].tolist()
        self.last_sync_text = self.get_last_sync_text()

    def get_last_sync_text(self):
        if not self.selected_competition_code:
            return "Sin competición"
        sync_df = load_last_sync_run(self.selected_competition_code)
        if sync_df.empty:
            return "Sin sincronizaciones registradas"
        last_sync = sync_df.iloc[0]
        status = "correcta" if last_sync["status"] == "SUCCESS" else "fallida"
        return f"Última sincronización: {status}"

    def sync_selected_competition(self):
        if not self.selected_competition_code:
            return
        sync_competition_data(self.selected_competition_code)
        self.refresh_competition_data()
        if hasattr(self, "last_sync_label"):
            self.last_sync_label.configure(text=self.last_sync_text)
        self.show_resumen()

    def on_competition_change(self, _selected_value=None):
        self.refresh_competition_data()
        if hasattr(self, "last_sync_label"):
            self.last_sync_label.configure(text=self.last_sync_text)
        # Re-renderiza la pestaña actual
        self.navigate(self.current_page)

    def format_match_date(self, utc_date) -> str:
        """Formatea la fecha del partido dd//mm/yyyy HH:MM"""
        if utc_date is None:
            return "-"
        try:
            import pandas as pd
            dt = pd.to_datetime(utc_date)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(utc_date)

    # ---------- SIDEBAR ----------
    def create_sidebar(self):
        # Logo + título
        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(28, 6))

        ctk.CTkLabel(
            header,
            image=ctk.CTkImage(dark_image=Image.open("assets/branding/fdh_logo_web_512.webp"), size=(150, 150)),
            text=""
        ).pack(fill="x")

        ctk.CTkLabel(
            header,
            text="Football Data Hub",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(
            header,
            text="Analytics dashboard",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_FAINT,
            anchor="w",
        ).pack(fill="x")

        # Separador visual
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDER).pack(
            fill="x", padx=20, pady=18
        )

        # Selector de competición
        if self.competition_options:
            ctk.CTkLabel(
                self.sidebar,
                text="COMPETICIÓN",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=COLOR_TEXT_FAINT,
                anchor="w",
            ).pack(fill="x", padx=20, pady=(0, 6))

            ctk.CTkOptionMenu(
                self.sidebar,
                values=list(self.competition_options.keys()),
                variable=self.selected_competition,
                command=self.on_competition_change,
                fg_color=COLOR_BG,
                button_color=COLOR_BORDER,
                button_hover_color=COLOR_BORDER_LIGHT,
                dropdown_fg_color=COLOR_SURFACE,
                dropdown_hover_color=COLOR_BORDER,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(size=12),
            ).pack(fill="x", padx=20)

            self.last_sync_label = ctk.CTkLabel(
                self.sidebar,
                text=self.last_sync_text,
                font=ctk.CTkFont(size=10),
                text_color=COLOR_TEXT_FAINT,
                anchor="w",
                wraplength=200,
                justify="left",
            )
            self.last_sync_label.pack(fill="x", padx=20, pady=(6, 12))

            if manual_sync_enabled():
                ctk.CTkButton(
                    self.sidebar,
                    text="↻ Sincronizar API",
                    command=self.sync_selected_competition,
                    height=32,
                    corner_radius=8,
                    fg_color=COLOR_SUCCESS,
                    hover_color=COLOR_WIN,
                    font=ctk.CTkFont(size=12, weight="bold"),
                ).pack(fill="x", padx=20, pady=(0, 18))

        # Separador
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDER).pack(
            fill="x", padx=20, pady=(0, 12)
        )

        # Navegación
        ctk.CTkLabel(
            self.sidebar,
            text="NAVEGACIÓN",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLOR_TEXT_FAINT,
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 6))

        nav_items = [
            ("Resumen", self.show_resumen),
            ("Clasificación", self.show_clasificacion),
            ("Equipo", self.show_equipo),
            ("Enfrentamientos", self.show_enfrentamientos),
        ]

        for label, command in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                command=lambda l=label: self.navigate(l),
                height=40,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLOR_BORDER,
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
                font=ctk.CTkFont(size=13),
            )
            btn.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[label] = btn

    def navigate(self, page: str):
        """Navega a una pestaña y resalta el botón correspondiente."""
        self.current_page = page

        # Restablecer estilos de todos los botones
        for label, btn in self.nav_buttons.items():
            if label == page:
                btn.configure(
                    fg_color=COLOR_BORDER,
                    text_color=COLOR_ACCENT,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLOR_TEXT_MUTED,
                )

        # Ejecutar el render de la pestaña
        page_methods = {
            "Resumen": self.show_resumen,
            "Clasificación": self.show_clasificacion,
            "Equipo": self.show_equipo,
            "Enfrentamientos": self.show_enfrentamientos,
        }
        method = page_methods.get(page)
        if method:
            method()

    # ---------- UTILS DE UI ----------
    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def add_page_header(self, title: str, subtitle: str | None = None):
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 12))

        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x")

        if subtitle:
            ctk.CTkLabel(
                header,
                text=subtitle,
                font=ctk.CTkFont(size=12),
                text_color=COLOR_TEXT_DIM,
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

    def show_empty_state(self, title: str, body: str):
        container = ctk.CTkFrame(
            self.main_frame,
            corner_radius=12,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        container.pack(fill="x", padx=28, pady=14)

        ctk.CTkLabel(
            container,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(fill="x", padx=22, pady=(18, 4))

        ctk.CTkLabel(
            container,
            text=body,
            text_color=COLOR_TEXT_DIM,
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", padx=22, pady=(0, 18))

    # ---------- PESTAÑAS ----------
    def show_resumen(self):
        self.clear_main_frame()
        self.add_page_header(
            "Resumen",
            "Vista general de la competición y rendimiento de los equipos.",
        )

        if self.standings_df.empty:
            self.show_empty_state(
                "Datos en preparación",
                "La competición seleccionada todavía no tiene datos analíticos cargados. "
                "Cuando termine la sincronización, este panel se completará automáticamente.",
            )
            return
        
        kpis = calculate_competition_kpis(self.standings_df, self.matches_df)

        main_kpis_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        main_kpis_frame.pack(fill="x", padx=28, pady=(8, 4))
        
        main_keys = ["leader", "top_attack", "best_defense", "goals_per_match"]
        for i, key in enumerate(main_keys):
            item = kpis[key]
            main_kpis_frame.grid_columnconfigure(i, weight=1, uniform="kpi")
            card = create_kpi_card(
                main_kpis_frame,
                label=item["label"],
                value=item["value"],
                detail=item["detail"],
                accent=item.get("delta_numeric") is not None,
            )
            card.grid(row=0, column=i, sticky="ew", padx=6, pady=6)
        
        # === KPIs SECUNDARIOS ===
        create_section_header(
            self.main_frame,
            "Más indicadores",
            "Detalles complementarios sobre el estado de la competición.",
        )
        
        secondary_kpis_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        secondary_kpis_frame.pack(fill="x", padx=28, pady=(0, 4))
        
        secondary_keys = ["highest_scoring_match", "next_match", "completion_rate", "pending_matches"]
        for i, key in enumerate(secondary_keys):
            item = kpis[key]
            secondary_kpis_frame.grid_columnconfigure(i, weight=1, uniform="kpi2")
            card = create_kpi_card(
                secondary_kpis_frame,
                label=item["label"],
                value=item["value"],
                detail=item["detail"],
            )
            card.grid(row=0, column=i, sticky="ew", padx=6, pady=6)
        
        # === ÚLTIMA JORNADA + MINI TABLA ===
        finished_matches_df = self.matches_df[self.matches_df["status"] == "FINISHED"].copy()
        
        if not finished_matches_df.empty:
            create_section_header(
                self.main_frame,
                "Última jornada y clasificación",
                "Resultados recientes y resumen del top y la cola de la tabla.",
            )
            
            content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            content.pack(fill="x", padx=28, pady=(0, 20))
            content.grid_columnconfigure(0, weight=2, uniform="content")
            content.grid_columnconfigure(1, weight=1, uniform="content")
            
            # --- Columna izquierda: última jornada ---
            last_md = int(finished_matches_df["matchday"].max())
            last_md_matches = finished_matches_df[
                finished_matches_df["matchday"] == last_md
            ].head(6)
            
            left_block = ctk.CTkFrame(
                content,
                corner_radius=12,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            left_block.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            
            ctk.CTkLabel(
                left_block,
                text=f"ÚLTIMA JORNADA · J{last_md}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLOR_TEXT_DIM,
                anchor="w",
            ).pack(fill="x", padx=16, pady=(14, 8))
            
            matches_container = ctk.CTkFrame(left_block, fg_color="transparent")
            matches_container.pack(fill="x", padx=12, pady=(0, 12))
            
            for _, m in last_md_matches.iterrows():
                create_match_card(
                    matches_container,
                    home_team=m["home_team"],
                    away_team=m["away_team"],
                    home_score=m.get("home_score"),
                    away_score=m.get("away_score"),
                    status=m["status"],
                    matchday=m.get("matchday"),
                )
            
            # --- Columna derecha: mini tabla top/bottom ---
            right_block = ctk.CTkFrame(
                content,
                corner_radius=12,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            right_block.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
            
            ctk.CTkLabel(
                right_block,
                text="CLASIFICACIÓN",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLOR_TEXT_DIM,
                anchor="w",
            ).pack(fill="x", padx=16, pady=(14, 4))
            
            ctk.CTkLabel(
                right_block,
                text="5 primeros y 3 últimos",
                font=ctk.CTkFont(size=10),
                text_color=COLOR_TEXT_FAINT,
                anchor="w",
            ).pack(fill="x", padx=16, pady=(0, 10))
            
            sorted_df = self.standings_df.sort_values("position")
            top5 = sorted_df.head(5)
            bottom3 = sorted_df.tail(3)
            total_teams = len(sorted_df)
            
            mini_container = ctk.CTkFrame(right_block, fg_color="transparent")
            mini_container.pack(fill="x", padx=12, pady=(0, 12))
            
            # Top 5
            ctk.CTkLabel(
                mini_container,
                text="CABEZA",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=COLOR_TEXT_FAINT,
                anchor="w",
            ).pack(fill="x", padx=4, pady=(4, 4))
            
            for _, row in top5.iterrows():
                pos = int(row["position"])
                if pos <= 4:
                    accent_color = COLOR_SUCCESS
                elif pos <= 6:
                    accent_color = COLOR_INFO
                else:
                    accent_color = COLOR_TEXT_FAINT
                self._create_mini_row(mini_container, row, accent_color)
            
            # Separador
            ctk.CTkFrame(
                mini_container,
                height=1,
                fg_color=COLOR_BORDER,
            ).pack(fill="x", padx=4, pady=8)
            
            ctk.CTkLabel(
                mini_container,
                text="COLA",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=COLOR_TEXT_FAINT,
                anchor="w",
            ).pack(fill="x", padx=4, pady=(0, 4))
            
            for _, row in bottom3.iterrows():
                self._create_mini_row(mini_container, row, COLOR_DANGER)
    
    def _create_mini_row(self, parent, row, accent_color: str):
        
        """Fila compacta de la mini-tabla con franja de color."""
        row_frame = ctk.CTkFrame(parent, fg_color="transparent", height=50)
        row_frame.pack(fill="x", padx=4, pady=2)
        row_frame.pack_propagate(False)
        
        # Franja vertical de color
        ctk.CTkFrame(
            row_frame,
            width=3,
            fg_color=accent_color,
            corner_radius=2,
        ).pack(side="left", fill="y", padx=(0, 8))
        
        # Posición
        ctk.CTkLabel(
            row_frame,
            text=str(int(row["position"])),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_FAINT,
            width=24,
            anchor="w",
        ).pack(side="left")
        
        # Equipo
        ctk.CTkLabel(
            row_frame,
            text=row["team"],
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        
        # Partidos jugados
        ctk.CTkLabel(
            row_frame,
            text=f"{int(row['played_games'])} PJ",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_FAINT,
            width=50,
        ).pack(side="left")
        
        # Puntos
        ctk.CTkLabel(
            row_frame,
            text=f"{int(row['points'])} pts",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT,
            width=55,
            anchor="e",
        ).pack(side="left")

    def show_clasificacion(self):
        self.clear_main_frame()
        self.add_page_header(
            "Clasificación",
            "Tabla completa con zonas europeas y descenso resaltadas.",
        )
        
        if self.standings_df.empty:
            self.show_empty_state(
                "Clasificación no disponible",
                "No hay tabla de posiciones para esta competición. "
                "Aparecerá aquí en cuanto exista una sincronización correcta.",
            )
            return
        
        # Contenedor de la tabla con padding y fondo coherente
        table_container = ctk.CTkFrame(
            self.main_frame,
            corner_radius=12,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        table_container.pack(fill="both", expand=True, padx=28, pady=(8, 4))
        
        # Construir filas con forma reciente
        rows_with_form = []
        for _, row in self.standings_df.sort_values("position").iterrows():
            form = self._get_team_form_text(row["team"], n=5)
            rows_with_form.append((
                int(row["position"]),
                row["team"],
                int(row["played_games"]),
                int(row["won"]),
                int(row["draw"]),
                int(row["lost"]),
                int(row["goals_for"]),
                int(row["goals_against"]),
                f"{int(row['goal_difference']):+d}",
                form,
                int(row["points"]),
            ))
        
        columns = ("Pos", "Equipo", "PJ", "V", "E", "D", "GF", "GC", "DG", "Forma", "Pts")
        column_widths = {
            "Pos": 50,
            "Equipo": 220,
            "PJ": 55,
            "V": 50,
            "E": 50,
            "D": 50,
            "GF": 60,
            "GC": 60,
            "DG": 65,
            "Forma": 110,
            "Pts": 70,
        }
        
        # Frame interno para Treeview + scrollbar
        tree_frame = ctk.CTkFrame(table_container, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Estilo personalizado para esta tabla con filas más altas
        style = ttk.Style()
        style.configure(
            "Standings.Treeview",
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            fieldbackground=COLOR_SURFACE,
            bordercolor=COLOR_BORDER,
            font=("Segoe UI", 13),
            rowheight=45,
        )
        style.configure(
            "Standings.Treeview.Heading",
            background=COLOR_BG,
            foreground=COLOR_ACCENT,
            relief="flat",
            font=("Segoe UI", 11, "bold"),
        )
        style.map(
            "Standings.Treeview",
            background=[("selected", COLOR_BORDER_LIGHT)],
            foreground=[("selected", COLOR_TEXT)],
        )
        
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=20,
            style="Standings.Treeview",
        )
        tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Configurar columnas
        for col in columns:
            tree.heading(col, text=col)
            anchor = "w" if col in ("Equipo", "Forma") else "center"
            tree.column(col, anchor=anchor, width=column_widths[col], minwidth=column_widths[col])
        
        # Configurar tags de color por zona
        tree.tag_configure(
            "champions",
            background=COLOR_ZONE_CHAMPIONS_BG,
            foreground=COLOR_TEXT,
        )
        tree.tag_configure(
            "europa",
            background=COLOR_ZONE_EUROPA_BG,
            foreground=COLOR_TEXT,
        )
        tree.tag_configure(
            "descenso",
            background=COLOR_ZONE_DESCENSO_BG,
            foreground=COLOR_TEXT,
        )
        tree.tag_configure(
            "normal",
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT,
        )
        
        # Insertar filas con su tag correspondiente
        total_teams = len(rows_with_form)
        descenso_from = total_teams - 2  # Las 3 últimas
        
        for row in rows_with_form:
            pos = row[0]
            if pos <= 4:
                tag = "champions"
            elif pos <= 6:
                tag = "europa"
            elif pos >= descenso_from:
                tag = "descenso"
            else:
                tag = "normal"
            tree.insert("", "end", values=row, tags=(tag,))
        
        # === LEYENDA DE ZONAS ===
        legend_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        legend_frame.pack(fill="x", padx=28, pady=(4, 20))
        
        legend_items = [
            ("Champions League", COLOR_SUCCESS),
            ("Europa League", COLOR_INFO),
            ("Descenso", COLOR_DANGER),
        ]
        
        for label, color in legend_items:
            item = ctk.CTkFrame(legend_frame, fg_color="transparent")
            item.pack(side="left", padx=(0, 24))
            
            ctk.CTkFrame(
                item,
                width=12,
                height=12,
                fg_color=color,
                corner_radius=3,
            ).pack(side="left", padx=(0, 6))
            
            ctk.CTkLabel(
                item,
                text=label,
                font=ctk.CTkFont(size=11),
                text_color=COLOR_TEXT_DIM,
            ).pack(side="left")
        
        # Nota de la columna Forma a la derecha
        ctk.CTkLabel(
            legend_frame,
            text="Forma: últimos 5 partidos (de más antiguo a más reciente)",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color=COLOR_TEXT_FAINT,
        ).pack(side="right")
    
    def _get_team_form_text(self, team_name: str, n: int = 5) -> str:
        """Calcula la forma reciente de un equipo y la devuelve como texto."""
        if self.matches_df.empty:
            return ""
        
        finished = self.matches_df[self.matches_df["status"] == "FINISHED"].copy()
        if finished.empty:
            return ""
        
        played = finished[
            (finished["home_team"] == team_name) | (finished["away_team"] == team_name)
        ].copy()
        
        if played.empty:
            return ""
        
        played = played.dropna(subset=["home_score", "away_score"])
        if played.empty:
            return ""
        
        import pandas as pd
        played["utc_date"] = pd.to_datetime(played["utc_date"], errors="coerce")
        played = played.sort_values("utc_date", ascending=False).head(n)
        
        results = []
        for _, match in played.iterrows():
            is_home = match["home_team"] == team_name
            team_goals = match["home_score"] if is_home else match["away_score"]
            opp_goals = match["away_score"] if is_home else match["home_score"]
            
            if team_goals > opp_goals:
                results.append("W")
            elif team_goals < opp_goals:
                results.append("L")
            else:
                results.append("D")
        
        # Invertir para mostrar de más antiguo a más reciente
        results.reverse()
        return "  ".join(results)

    def show_equipo(self):
        """
        Muestra el análisis individual de un equipo:
        - selector de equipo
        - resumen principal
        - KPIs del equipo
        - calendario de partidos
        """

        self.clear_main_frame()

        self.add_page_header(
            "Equipo",
            "Consulta el rendimiento individual de cada equipo de la competición.",
        )

        if not self.teams_list:
            self.show_empty_state(
                "Sin equipos disponibles",
                "No hay equipos cargados para la competición seleccionada.",
            )
            return

        # === SELECTOR DE EQUIPO ===
        selector_frame = ctk.CTkFrame(
            self.main_frame,
            corner_radius=12,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        selector_frame.pack(fill="x", padx=28, pady=(4, 16))

        ctk.CTkLabel(
            selector_frame,
            text="SELECCIONA UN EQUIPO",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLOR_TEXT_FAINT,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 6))

        selected_team_var = ctk.StringVar(value=self.teams_list[0])

        team_selector = ctk.CTkOptionMenu(
            selector_frame,
            values=self.teams_list,
            variable=selected_team_var,
            fg_color=COLOR_BG,
            button_color=COLOR_BORDER,
            button_hover_color=COLOR_BORDER_LIGHT,
            dropdown_fg_color=COLOR_SURFACE,
            dropdown_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=12),
        )
        team_selector.pack(fill="x", padx=16, pady=(0, 16))

        # Contenedor donde se pintará la información del equipo
        team_content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        team_content.pack(fill="both", expand=True)

        def render_team_data():
            """
            Renderiza los datos del equipo seleccionado.
            Se ejecuta al cargar la pestaña y cuando cambia el selector.
            """

            # Limpiamos el contenido anterior
            for widget in team_content.winfo_children():
                widget.destroy()

            team_name = selected_team_var.get()

            # Buscamos la fila del equipo en la clasificación
            team_row = self.standings_df[self.standings_df["team"] == team_name]

            if team_row.empty:
                self.show_empty_state(
                    "Datos no encontrados",
                    "No se han encontrado datos de clasificación para este equipo.",
                )
                return

            team_data = team_row.iloc[0]

            # === HEADER DEL EQUIPO ===
            header = ctk.CTkFrame(
                team_content,
                corner_radius=14,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            header.pack(fill="x", padx=28, pady=(0, 16))

            header.grid_columnconfigure(0, weight=1)
            header.grid_columnconfigure(1, weight=0)

            ctk.CTkLabel(
                header,
                text=team_name,
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=COLOR_TEXT,
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 4))

            # ===== COLOR POR POSICIÓN SEGÚN ZONA =====
            pos = int(team_data["position"])
            total_teams = len(self.standings_df)

            if pos <= 4:
                pos_color = COLOR_SUCCESS
            elif pos <=6:
                pos_color = COLOR_INFO
            elif pos>= total_teams - 3:
                pos_color = COLOR_DANGER
            else:
                pos_color = COLOR_ACCENT

            ctk.CTkLabel(
                header,
                text=f"#{pos}",
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=pos_color,
            ).grid(row=0, column=1, padx=20, pady=(18, 4))

            ctk.CTkLabel(
                header,
                text=f"{int(team_data['points'])} puntos",
                font=ctk.CTkFont(size=13),
                text_color=COLOR_TEXT_DIM,
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))

            # === KPIs DEL EQUIPO ===
            kpi_frame = ctk.CTkFrame(team_content, fg_color="transparent")
            kpi_frame.pack(fill="x", padx=28, pady=(0, 14))

            played_games = max(int(team_data["played_games"]), 1)
            points_per_game = round(int(team_data["points"]) / played_games, 2)

            team_kpis = [
                ("Partidos", int(team_data["played_games"]), "jugados"),
                ("Victorias", int(team_data["won"]), "ganados"),
                ("Goles a favor", int(team_data["goals_for"]), "marcados"),
                ("Pts/partido", points_per_game, "media"),
            ]

            for i, (label, value, detail) in enumerate(team_kpis):
                kpi_frame.grid_columnconfigure(i, weight=1, uniform="team_kpi")

                card = create_kpi_card(
                    kpi_frame,
                    label=label,
                    value=value,
                    detail=detail,
                    accent=True,
                )
                card.grid(row=0, column=i, sticky="ew", padx=6, pady=6)

            # === CALENDARIO DEL EQUIPO ===
            create_section_header(
                team_content,
                "Calendario",
                "Partidos disputados y pendientes del equipo seleccionado.",
            )

            matches = load_matches_by_team(
                team_name,
                competition_id=self.selected_competition_id,
            )

            if matches.empty:
                self.show_empty_state(
                    "Sin partidos",
                    "No hay partidos disponibles para este equipo.",
                )
                return

            table_container = ctk.CTkFrame(
                team_content,
                corner_radius=12,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            table_container.pack(fill="both", expand=True, padx=28, pady=(0, 24))

            tree_frame = ctk.CTkFrame(table_container, fg_color="transparent")
            tree_frame.pack(fill="both", expand=True, padx=14, pady=14)

            columns = (
                "jornada",
                "fecha",
                "local",
                "resultado",
                "visitante",
                "estado",
            )

            tree = ttk.Treeview(
                tree_frame,
                columns=columns,
                show="headings",
                height=14,
            )

            scrollbar = ttk.Scrollbar(
                tree_frame,
                orient="vertical",
                command=tree.yview,
            )

            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Cabeceras
            tree.heading("jornada", text="J")
            tree.heading("fecha", text="FECHA")
            tree.heading("local", text="LOCAL")
            tree.heading("resultado", text="RESULTADO")
            tree.heading("visitante", text="VISITANTE")
            tree.heading("estado", text="ESTADO")

            # Tamaño de columnas
            tree.column("jornada", width=50, anchor="center", stretch=False)
            tree.column("fecha", width=150, anchor="center", stretch=False)
            tree.column("local", width=220, anchor="w", stretch=True)
            tree.column("resultado", width=100, anchor="center", stretch=False)
            tree.column("visitante", width=220, anchor="w", stretch=True)
            tree.column("estado", width=110, anchor="center", stretch=False)

            # Tags para diferenciar partidos terminados y pendientes
            tree.tag_configure(
                "finished",
                background=COLOR_SURFACE,
                foreground=COLOR_TEXT,
            )

            tree.tag_configure(
                "pending",
                background=COLOR_ZONE_EUROPA_BG,
                foreground=COLOR_TEXT,
            )

            # Insertamos los partidos en la tabla
            for _, match in matches.iterrows():
                status = match["status"]

                if status == "FINISHED":
                    result_text = f"{match['home_score']} - {match['away_score']}"
                    tag = "finished"
                    status_text = "Finalizado"
                else:
                    result_text = "vs"
                    tag = "pending"
                    status_text = "Pendiente"

                tree.insert(
                    "",
                    "end",
                    values=(
                        int(match["matchday"]) if pd.notna(match["matchday"]) else "-",
                        self.format_match_date(match["utc_date"]),
                        match["home_team"],
                        result_text,
                        match["away_team"],
                        status_text,
                    ),
                    tags=(tag,),
                )

        # Pintamos los datos por primera vez
        render_team_data()

        # Cuando se cambia el equipo, se vuelve a pintar el contenido
        team_selector.configure(command=lambda _value: render_team_data())

    def create_comparison_row(self, parent, label: str, home_value, away_value, mode: str):
        """
        Crea una fila para comparar una estadística entre dos equipos.

        mode:
        - higher: gana el valor más alto
        - lower: gana el valor más bajo
        """

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=6)

        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=1)

        # Decidimos quién gana en esta estadística
        if home_value == away_value:
            home_color = away_color = COLOR_TEXT_DIM
        else:
            if mode == "higher":
                home_wins = home_value > away_value
            else:
                home_wins = home_value < away_value

            home_color = COLOR_SUCCESS if home_wins else COLOR_TEXT_FAINT
            away_color = COLOR_SUCCESS if not home_wins else COLOR_TEXT_FAINT

        ctk.CTkLabel(
            row,
            text=str(home_value),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=home_color,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_DIM,
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            row,
            text=str(away_value),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=away_color,
            anchor="e",
        ).grid(row=0, column=2, sticky="ew")

    def create_probability_bar(self, parent, label: str, value: float, color: str):
        """
        Crea una barra horizontal para mostrar una probabilidad.
        """

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=8)

        # Texto superior: equipo + porcentaje
        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(
            top,
            text=label,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text=f"{value:.1f}%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=color,
            anchor="e",
        ).pack(side="right")

        # Barra de fondo
        bar_bg = ctk.CTkFrame(
            row,
            height=12,
            corner_radius=10,
            fg_color=COLOR_BG,
        )
        bar_bg.pack(fill="x", pady=(5, 0))

        # Limitamos el porcentaje entre 0 y 100
        safe_value = max(0, min(100, value))

        # Barra de progreso
        bar_fg = ctk.CTkFrame(
            bar_bg,
            height=12,
            corner_radius=10,
            fg_color=color,
        )
        bar_fg.place(relx=0, rely=0, relwidth=safe_value / 100, relheight=1)

    def create_scoreline_row(self, parent, score: str, probability: float):
        """
        Crea una fila para mostrar un marcador probable.
        """

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=7)

        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row,
            text=score,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT,
            width=60,
        ).grid(row=0, column=0, sticky="w")

        # Barra visual
        bar_bg = ctk.CTkFrame(
            row,
            height=10,
            corner_radius=8,
            fg_color=COLOR_BG,
        )
        bar_bg.grid(row=0, column=1, sticky="ew", padx=10)

        # Multiplicamos para que se vea mejor visualmente
        visual_width = min(probability * 4, 100)

        bar_fg = ctk.CTkFrame(
            bar_bg,
            height=10,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
        )
        bar_fg.place(relx=0, rely=0, relwidth=visual_width / 100, relheight=1)

        ctk.CTkLabel(
            row,
            text=f"{probability:.1f}%",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_DIM,
            width=60,
            anchor="e",
        ).grid(row=0, column=2, sticky="e")

    def show_enfrentamientos(self):
        """
        Muestra una comparativa entre dos equipos:
        - selectores lado a lado
        - tabla comparativa
        - predicción 1X2 con barras
        - marcadores más probables
        """

        self.clear_main_frame()

        self.add_page_header(
            "Enfrentamientos",
            "Compara dos equipos y consulta una predicción orientativa del partido.",
        )

        if not self.teams_list or len(self.teams_list) < 2:
            self.show_empty_state(
                "Sin equipos suficientes",
                "Se necesitan al menos dos equipos para comparar.",
            )
            return

        # === SELECTORES SIDE BY SIDE ===
        selector_frame = ctk.CTkFrame(
            self.main_frame,
            corner_radius=12,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        selector_frame.pack(fill="x", padx=28, pady=(4, 16))

        selector_frame.grid_columnconfigure(0, weight=1)
        selector_frame.grid_columnconfigure(1, weight=0)
        selector_frame.grid_columnconfigure(2, weight=1)

        home_var = ctk.StringVar(value=self.teams_list[0])
        away_var = ctk.StringVar(value=self.teams_list[1])

        ctk.CTkLabel(
            selector_frame,
            text="Equipo local",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            selector_frame,
            text="VS",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_ACCENT,
        ).grid(row=1, column=1, padx=20, pady=(0, 16))

        ctk.CTkLabel(
            selector_frame,
            text="Equipo visitante",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        ).grid(row=0, column=2, sticky="ew", padx=16, pady=(14, 6))

        home_selector = ctk.CTkOptionMenu(
            selector_frame,
            values=self.teams_list,
            variable=home_var,
            fg_color=COLOR_BG,
            button_color=COLOR_BORDER,
            button_hover_color=COLOR_BORDER_LIGHT,
            dropdown_fg_color=COLOR_SURFACE,
            dropdown_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
        )
        home_selector.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))

        away_selector = ctk.CTkOptionMenu(
            selector_frame,
            values=self.teams_list,
            variable=away_var,
            fg_color=COLOR_BG,
            button_color=COLOR_BORDER,
            button_hover_color=COLOR_BORDER_LIGHT,
            dropdown_fg_color=COLOR_SURFACE,
            dropdown_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
        )
        away_selector.grid(row=1, column=2, sticky="ew", padx=16, pady=(0, 16))

        content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)

        def render_matchup():
            """
            Renderiza la comparativa y la predicción de los dos equipos.
            """

            for widget in content_frame.winfo_children():
                widget.destroy()

            home_team = home_var.get()
            away_team = away_var.get()

            if home_team == away_team:
                self.show_empty_state(
                    "Equipos repetidos",
                    "Selecciona dos equipos diferentes para poder comparar.",
                )
                return

            home_row = self.standings_df[self.standings_df["team"] == home_team]
            away_row = self.standings_df[self.standings_df["team"] == away_team]

            if home_row.empty or away_row.empty:
                self.show_empty_state(
                    "Datos incompletos",
                    "No se han encontrado datos suficientes para comparar estos equipos.",
                )
                return

            home_data = home_row.iloc[0]
            away_data = away_row.iloc[0]

            # === HEADER DEL ENFRENTAMIENTO ===
            header = ctk.CTkFrame(
                content_frame,
                corner_radius=14,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            header.pack(fill="x", padx=28, pady=(0, 16))

            header.grid_columnconfigure(0, weight=1)
            header.grid_columnconfigure(1, weight=0)
            header.grid_columnconfigure(2, weight=1)

            ctk.CTkLabel(
                header,
                text=f"#{int(home_data['position'])}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLOR_ACCENT,
            ).grid(row=0, column=0, pady=(16, 0))

            ctk.CTkLabel(
                header,
                text="VS",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=COLOR_TEXT_FAINT,
            ).grid(row=0, column=1, padx=30, pady=(16, 0))

            ctk.CTkLabel(
                header,
                text=f"#{int(away_data['position'])}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLOR_ACCENT,
            ).grid(row=0, column=2, pady=(16, 0))

            ctk.CTkLabel(
                header,
                text=home_team,
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=COLOR_TEXT,
            ).grid(row=1, column=0, sticky="ew", padx=18, pady=4)

            ctk.CTkLabel(
                header,
                text=away_team,
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=COLOR_TEXT,
            ).grid(row=1, column=2, sticky="ew", padx=18, pady=4)

            ctk.CTkLabel(
                header,
                text=f"{int(home_data['points'])} pts",
                font=ctk.CTkFont(size=12),
                text_color=COLOR_TEXT_DIM,
            ).grid(row=2, column=0, pady=(0, 16))

            ctk.CTkLabel(
                header,
                text=f"{int(away_data['points'])} pts",
                font=ctk.CTkFont(size=12),
                text_color=COLOR_TEXT_DIM,
            ).grid(row=2, column=2, pady=(0, 16))

            # === COMPARATIVA DE STATS ===
            create_section_header(
                content_frame,
                "Comparativa de estadísticas",
                "Datos principales de ambos equipos en la competición.",
            )

            comparison_block = ctk.CTkFrame(
                content_frame,
                corner_radius=12,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            comparison_block.pack(fill="x", padx=28, pady=(0, 16))

            home_played = max(int(home_data["played_games"]), 1)
            away_played = max(int(away_data["played_games"]), 1)

            stats = [
                ("Posición", int(home_data["position"]), int(away_data["position"]), "lower"),
                ("Puntos", int(home_data["points"]), int(away_data["points"]), "higher"),
                ("Partidos", int(home_data["played_games"]), int(away_data["played_games"]), "higher"),
                ("Victorias", int(home_data["won"]), int(away_data["won"]), "higher"),
                ("Empates", int(home_data["draw"]), int(away_data["draw"]), "higher"),
                ("Derrotas", int(home_data["lost"]), int(away_data["lost"]), "lower"),
                ("Goles a favor", int(home_data["goals_for"]), int(away_data["goals_for"]), "higher"),
                ("Goles en contra", int(home_data["goals_against"]), int(away_data["goals_against"]), "lower"),
                ("Diferencia", int(home_data["goal_difference"]), int(away_data["goal_difference"]), "higher"),
                ("Pts/partido", round(int(home_data["points"]) / home_played, 2), round(int(away_data["points"]) / away_played, 2), "higher"),
            ]

            for label, home_value, away_value, mode in stats:
                self.create_comparison_row(
                    comparison_block,
                    label,
                    home_value,
                    away_value,
                    mode,
                )

            # === PREDICCIÓN ===
            create_section_header(
                content_frame,
                "Predicción 1X2",
                "Estimación orientativa basada en el rendimiento de ambos equipos.",
            )

            prediction_matches = load_combined_matches(
                self.selected_competition_id,
                home_team,
                away_team,
            )

            try:
                prediction = estimate_match_probabilities(
                    self.standings_df,
                    prediction_matches,
                    home_team,
                    away_team,
                )
            except Exception as error:
                self.show_empty_state(
                    "Predicción no disponible",
                    f"No se pudo calcular la predicción: {error}",
                )
                return

            prediction_block = ctk.CTkFrame(
                content_frame,
                corner_radius=12,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            prediction_block.pack(fill="x", padx=28, pady=(0, 16))

            self.create_probability_bar(
                prediction_block,
                home_team,
                prediction["home_win_probability"],
                COLOR_ACCENT,
            )

            self.create_probability_bar(
                prediction_block,
                "Empate",
                prediction["draw_probability"],
                COLOR_DRAW,
            )

            self.create_probability_bar(
                prediction_block,
                away_team,
                prediction["away_win_probability"],
                COLOR_INFO,
            )

            # === MARCADORES MÁS PROBABLES ===
            create_section_header(
                content_frame,
                "Marcadores más probables",
                "Resultados estimados por el modelo.",
            )

            score_block = ctk.CTkFrame(
                content_frame,
                corner_radius=12,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            score_block.pack(fill="x", padx=28, pady=(0, 24))

            scorelines = prediction.get("top_scorelines", [])

            if not scorelines:
                ctk.CTkLabel(
                    score_block,
                    text="No hay marcadores disponibles.",
                    text_color=COLOR_TEXT_DIM,
                ).pack(padx=16, pady=16)
            else:
                for item in scorelines[:5]:
                    self.create_scoreline_row(
                        score_block,
                        item["score"],
                        item["probability"],
                    )

        # Pintamos el enfrentamiento inicial
        render_matchup()

        # Al cambiar un equipo, se recalcula la vista
        home_selector.configure(command=lambda _value: render_matchup())
        away_selector.configure(command=lambda _value: render_matchup())


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()