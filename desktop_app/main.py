import os
import sys
from tkinter import ttk

import customtkinter as ctk

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


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Football Data Hub")
        self.geometry("1440x840")
        self.minsize(1180, 720)
        self.configure(fg_color="#0f172a")

        # Asegura tablas nuevas como sync_runs antes de cargar datos en la app.
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

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        self.create_sidebar_buttons()
        self.show_dashboard()

    def configure_table_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#111827",
            foreground="#e5e7eb",
            fieldbackground="#111827",
            bordercolor="#243044",
            font=("Segoe UI", 12),
            rowheight=38,
        )
        style.configure(
            "Treeview.Heading",
            background="#172033",
            foreground="#d1d5db",
            relief="flat",
            font=("Segoe UI", 12, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", "#1f7a4d")],
            foreground=[("selected", "#ffffff")],
        )

    def refresh_competition_data(self):
        self.selected_competition_id = self.competition_options.get(
            self.selected_competition.get(), {}
        ).get("id")
        self.selected_competition_code = self.competition_options.get(
            self.selected_competition.get(), {}
        ).get("code")
        self.standings_df = load_standings(self.selected_competition_id)
        self.teams_df = load_teams(self.selected_competition_id)
        self.matches_df = load_matches(self.selected_competition_id)
        self.teams_list = self.teams_df["name"].tolist()
        self.last_sync_text = self.get_last_sync_text()

    def get_last_sync_text(self):
        if not self.selected_competition_code:
            return "Última actualización: sin competición"

        sync_df = load_last_sync_run(self.selected_competition_code)
        if sync_df.empty:
            return "Última actualización: sin registros"

        last_sync = sync_df.iloc[0]
        status = "correcta" if last_sync["status"] == "SUCCESS" else "fallida"
        return f"Última actualización: {last_sync['finished_at']} ({status})"

    def sync_selected_competition(self):
        if not self.selected_competition_code:
            return

        # Esta accion llama a la API y despues recarga los DataFrames que usa la
        # interfaz. Las inserciones son upserts, asi que tambien corrigen datos ya existentes.
        sync_competition_data(self.selected_competition_code)
        self.refresh_competition_data()
        if hasattr(self, "last_sync_label"):
            self.last_sync_label.configure(text=self.last_sync_text)
        self.show_dashboard()

    def create_sidebar_buttons(self):
        title = ctk.CTkLabel(
            self.sidebar,
            text="FDH",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.pack(pady=(28, 6))

        subtitle = ctk.CTkLabel(
            self.sidebar,
            text="Football Data Hub",
            font=ctk.CTkFont(size=13),
            text_color="#9ca3af",
        )
        subtitle.pack(pady=(0, 24))

        if self.competition_options:
            competition_selector = ctk.CTkOptionMenu(
                self.sidebar,
                values=list(self.competition_options.keys()),
                variable=self.selected_competition,
                command=self.on_competition_change,
                width=188,
            )
            competition_selector.pack(fill="x", pady=(0, 8), padx=16)

            self.last_sync_label = ctk.CTkLabel(
                self.sidebar,
                text=self.last_sync_text,
                font=ctk.CTkFont(size=11),
                text_color="#9ca3af",
                wraplength=180,
                justify="left",
            )
            self.last_sync_label.pack(fill="x", pady=(0, 12), padx=16)

            if manual_sync_enabled():
                sync_button = ctk.CTkButton(
                    self.sidebar,
                    text="Actualizar API",
                    command=self.sync_selected_competition,
                    height=34,
                    corner_radius=6,
                    fg_color="#1f7a4d",
                    hover_color="#16613c",
                )
                sync_button.pack(fill="x", pady=(0, 18), padx=16)

        buttons = [
            ("Dashboard", self.show_dashboard),
            ("Clasificación", self.show_standings),
            ("Partidos", self.show_matches),
            ("Predicción", self.show_prediction),
        ]

        for text, command in buttons:
            button = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                height=38,
                corner_radius=6,
            )
            button.pack(fill="x", pady=7, padx=16)

    def on_competition_change(self, _selected_value=None):
        self.refresh_competition_data()
        if hasattr(self, "last_sync_label"):
            self.last_sync_label.configure(text=self.last_sync_text)
        self.show_dashboard()

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def add_title(self, text: str, subtitle: str | None = None):
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(22, 10))

        title = ctk.CTkLabel(
            header,
            text=text,
            font=ctk.CTkFont(size=26, weight="bold"),
            anchor="w",
        )
        title.pack(fill="x")

        if subtitle:
            caption = ctk.CTkLabel(
                header,
                text=subtitle,
                font=ctk.CTkFont(size=13),
                text_color="#9ca3af",
                anchor="w",
            )
            caption.pack(fill="x", pady=(4, 0))

    def show_empty_state(self, title: str, body: str):
        container = ctk.CTkFrame(self.main_frame, corner_radius=8)
        container.pack(fill="x", padx=24, pady=24)
        ctk.CTkLabel(
            container,
            text=title,
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(20, 4))
        ctk.CTkLabel(
            container,
            text=body,
            text_color="#9ca3af",
            anchor="w",
            wraplength=760,
        ).pack(fill="x", padx=22, pady=(0, 20))

    def create_table(
        self,
        parent,
        columns: tuple[str, ...],
        rows: list[tuple],
        height: int = 16,
        column_widths: dict[str, int] | None = None,
    ):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=24, pady=12)

        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        for col in columns:
            tree.heading(col, text=col)
            width = column_widths.get(col, 140) if column_widths else 140
            anchor = "w" if col in {"Equipo", "Local", "Visitante", "Metrica"} else "center"
            tree.column(col, anchor=anchor, width=width, minwidth=width)

        for row in rows:
            tree.insert("", "end", values=row)

        return tree

    def show_dashboard(self):
        self.clear_main_frame()
        self.add_title(
            "Dashboard",
            "Vista general de datos cargados y estado actual del proyecto.",
        )

        if self.standings_df.empty:
            self.show_empty_state(
                "Datos en preparación",
                "La competición seleccionada todavia no tiene datos analíticos cargados. Cuando termine la sincronización, este panel se completará automáticamente.",
            )
            return

        kpis = calculate_competition_kpis(self.standings_df, self.matches_df)

        for row_index, keys in enumerate(
            [
                ["leader", "top_attack", "best_defense", "goals_per_match"],
                ["highest_scoring_match", "next_match", "completion_rate", "pending_matches"],
            ]
        ):
            metrics_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            metrics_frame.pack(fill="x", padx=24, pady=(12 if row_index == 0 else 2, 2))

            for index, key in enumerate(keys):
                item = kpis[key]
                metrics_frame.grid_columnconfigure(index, weight=1)
                card = ctk.CTkFrame(metrics_frame, corner_radius=8)
                card.grid(row=0, column=index, sticky="ew", padx=6)
                ctk.CTkLabel(card, text=item["label"], text_color="#9ca3af").pack(pady=(14, 3))
                ctk.CTkLabel(
                    card,
                    text=str(item["value"]),
                    font=ctk.CTkFont(size=20, weight="bold"),
                    wraplength=260,
                ).pack(pady=(0, 2))
                ctk.CTkLabel(
                    card,
                    text=str(item["detail"]),
                    text_color="#9ca3af",
                    font=ctk.CTkFont(size=12),
                    wraplength=260,
                ).pack(pady=(0, 14))

        summary_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        summary_frame.pack(fill="both", expand=True)
        summary_frame.grid_columnconfigure(0, weight=2)
        summary_frame.grid_columnconfigure(1, weight=1)
        summary_frame.grid_columnconfigure(2, weight=1)

        table_area = ctk.CTkFrame(summary_frame, fg_color="transparent")
        table_area.grid(row=0, column=0, sticky="nsew")
        attack_area = ctk.CTkFrame(summary_frame, fg_color="transparent")
        attack_area.grid(row=0, column=1, sticky="nsew")
        defense_area = ctk.CTkFrame(summary_frame, fg_color="transparent")
        defense_area.grid(row=0, column=2, sticky="nsew")

        ctk.CTkLabel(
            table_area,
            text="Clasificación completa",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(12, 0))
        rows = [
            (
                row["position"],
                row["team"],
                row["points"],
                row["goals_for"],
                row["goals_against"],
                row["goal_difference"],
            )
            for _, row in self.standings_df.iterrows()
        ]
        self.create_table(
            table_area,
            ("Posicion", "Equipo", "Puntos", "GF", "GC", "DG"),
            rows,
            height=16,
            column_widths={"Posicion": 95, "Equipo": 220, "Puntos": 105, "GF": 85, "GC": 85, "DG": 85},
        )

        ctk.CTkLabel(
            attack_area,
            text="Mejores ataques",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(12, 0))
        attack_rows = [
            (row["team"], row["goals_for"])
            for _, row in self.standings_df.sort_values("goals_for", ascending=False).head(10).iterrows()
        ]
        self.create_table(
            attack_area,
            ("Equipo", "GF"),
            attack_rows,
            height=10,
            column_widths={"Equipo": 210, "GF": 80},
        )

        ctk.CTkLabel(
            defense_area,
            text="Mejores defensas",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(12, 0))
        defense_rows = [
            (row["team"], row["goals_against"])
            for _, row in self.standings_df.sort_values("goals_against", ascending=True).head(10).iterrows()
        ]
        self.create_table(
            defense_area,
            ("Equipo", "GC"),
            defense_rows,
            height=10,
            column_widths={"Equipo": 210, "GC": 80},
        )

    def show_standings(self):
        self.clear_main_frame()
        self.add_title("Clasificación", "Tabla actual ordenada por posicion.")

        if self.standings_df.empty:
            self.show_empty_state(
                "Clasificación no disponible",
                "No hay tabla de posiciones para esta competición. Se mostrara aqui en cuanto exista una sincronización correcta.",
            )
            return

        rows = [
            (
                row["position"],
                row["team"],
                row["played_games"],
                row["won"],
                row["draw"],
                row["lost"],
                row["points"],
                row["goals_for"],
                row["goals_against"],
                row["goal_difference"],
            )
            for _, row in self.standings_df.iterrows()
        ]

        self.create_table(
            self.main_frame,
            ("Posicion", "Equipo", "PJ", "G", "E", "P", "Pts", "GF", "GC", "DG"),
            rows,
            column_widths={
                "Posicion": 95,
                "Equipo": 260,
                "PJ": 70,
                "G": 70,
                "E": 70,
                "P": 70,
                "Pts": 80,
                "GF": 70,
                "GC": 70,
                "DG": 70,
            },
        )

    def show_matches(self):
        self.clear_main_frame()
        self.add_title("Partidos", "Consulta los partidos registrados de un equipo.")

        if not self.teams_list:
            self.show_empty_state(
                "Equipos no disponibles",
                "Todavia no hay equipos asociados a esta competición. Revisa el estado de sincronización o espera al proximo proceso automatico.",
            )
            return

        controls = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=8)

        selected_team = ctk.StringVar(value=self.teams_list[0] if self.teams_list else "")
        selector = ctk.CTkOptionMenu(
            controls,
            values=self.teams_list,
            variable=selected_team,
            width=380,
        )
        selector.pack(side="left", padx=(0, 12))

        table_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        table_container.pack(fill="both", expand=True)

        def render_matches():
            for widget in table_container.winfo_children():
                widget.destroy()

            matches_df = load_matches_by_team(
                selected_team.get(),
                competition_id=self.selected_competition_id,
            )
            rows = [
                (
                    row["matchday"],
                    row["utc_date"],
                    row["home_team"],
                    row["away_team"],
                    row["home_score"],
                    row["away_score"],
                    row["status"],
                )
                for _, row in matches_df.iterrows()
            ]
            self.create_table(
                table_container,
                ("Jornada", "Fecha", "Local", "Visitante", "GL", "GV", "Estado"),
                rows,
                column_widths={
                    "Jornada": 90,
                    "Fecha": 190,
                    "Local": 240,
                    "Visitante": 240,
                    "GL": 70,
                    "GV": 70,
                    "Estado": 130,
                },
            )

        ctk.CTkButton(controls, text="Consultar", command=render_matches, width=130).pack(side="left")
        render_matches()

    def show_prediction(self):
        self.clear_main_frame()
        self.add_title(
            "Predicción",
            "Comparacion de equipos y estimacion Poisson basada en clasificación, goles y forma.",
        )

        if len(self.teams_list) < 2:
            self.show_empty_state(
                "Predicción no disponible",
                "Se necesitan al menos dos equipos asociados a la competición para calcular un partido.",
            )
            return

        controls = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=8)

        home_team = ctk.StringVar(value=self.teams_list[0])
        away_team = ctk.StringVar(value=self.teams_list[1])

        ctk.CTkLabel(controls, text="Local").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(controls, values=self.teams_list, variable=home_team, width=380).pack(side="left", padx=(0, 18))
        ctk.CTkLabel(controls, text="Visitante").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(controls, values=self.teams_list, variable=away_team, width=380).pack(side="left", padx=(0, 18))

        results_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        results_frame.pack(fill="both", expand=True)

        def add_probability_bar(parent, label: str, value: float):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=label, width=180, anchor="w").pack(side="left")
            bar = ctk.CTkProgressBar(row)
            bar.set(value / 100)
            bar.pack(side="left", fill="x", expand=True, padx=10)
            ctk.CTkLabel(row, text=f"{value:.1f}%", width=70).pack(side="left")

        def render_prediction():
            for widget in results_frame.winfo_children():
                widget.destroy()

            if home_team.get() == away_team.get():
                ctk.CTkLabel(results_frame, text="Selecciona dos equipos diferentes.").pack(pady=24)
                return

            matches_df = load_combined_matches(
                self.selected_competition_id,
                home_team.get(),
                away_team.get(),
            )
            prediction = estimate_match_probabilities(
                self.standings_df,
                matches_df,
                home_team.get(),
                away_team.get(),
            )

            cards = ctk.CTkFrame(results_frame, fg_color="transparent")
            cards.pack(fill="x", padx=24, pady=14)

            for index, (label, value) in enumerate(
                [
                    (f"Gana {home_team.get()}", f"{prediction['home_win_probability']}%"),
                    ("Empate", f"{prediction['draw_probability']}%"),
                    (f"Gana {away_team.get()}", f"{prediction['away_win_probability']}%"),
                    ("Goles esperados", prediction["total_expected_goals"]),
                ]
            ):
                cards.grid_columnconfigure(index, weight=1)
                card = ctk.CTkFrame(cards, corner_radius=8)
                card.grid(row=0, column=index, sticky="ew", padx=6)
                ctk.CTkLabel(card, text=label, text_color="#9ca3af").pack(pady=(14, 4))
                ctk.CTkLabel(card, text=str(value), font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(0, 14))

            bars = ctk.CTkFrame(results_frame)
            bars.pack(fill="x", padx=24, pady=8)
            add_probability_bar(bars, home_team.get(), prediction["home_win_probability"])
            add_probability_bar(bars, "Empate", prediction["draw_probability"])
            add_probability_bar(bars, away_team.get(), prediction["away_win_probability"])

            score_rows = [
                (scoreline["score"], f"{scoreline['probability']}%")
                for scoreline in prediction["top_scorelines"]
            ]
            self.create_table(results_frame, ("Marcador probable", "Probabilidad"), score_rows, height=5)

            comparison_df = compare_teams(
                self.standings_df,
                matches_df,
                home_team.get(),
                away_team.get(),
            )
            rows = [
                (row["metric"], row["team"], row["value"])
                for _, row in comparison_df.iterrows()
            ]
            self.create_table(
                results_frame,
                ("Metrica", "Equipo", "Valor"),
                rows,
                height=10,
                column_widths={"Metrica": 260, "Equipo": 260, "Valor": 110},
            )

        ctk.CTkButton(controls, text="Analizar partido", command=render_prediction, width=150).pack(side="left")
        render_prediction()


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
