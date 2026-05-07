import os
import sys
from tkinter import ttk

import customtkinter as ctk

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analytics.match_analysis import compare_teams, estimate_match_probabilities
from utils_desktop.db_utils import (
    load_combined_matches,
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
        self.geometry("1280x760")
        self.minsize(1100, 680)

        self.standings_df = load_standings()
        self.teams_df = load_teams()
        self.teams_list = self.teams_df["name"].tolist()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        self.create_sidebar_buttons()
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

        buttons = [
            ("Dashboard", self.show_dashboard),
            ("Clasificacion", self.show_standings),
            ("Partidos", self.show_matches),
            ("Prediccion", self.show_prediction),
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

    def create_table(self, parent, columns: tuple[str, ...], rows: list[tuple], height: int = 16):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=24, pady=12)

        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=130)

        for row in rows:
            tree.insert("", "end", values=row)

        return tree

    def show_dashboard(self):
        self.clear_main_frame()
        self.add_title(
            "Dashboard",
            "Vista general de datos cargados y estado actual del proyecto.",
        )

        metrics_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=24, pady=12)

        metrics = [
            ("Equipos", len(self.standings_df)),
            ("Maximo de puntos", int(self.standings_df["points"].max()) if not self.standings_df.empty else 0),
            (
                "Mejor diferencia",
                int(self.standings_df["goal_difference"].max()) if not self.standings_df.empty else 0,
            ),
            ("Goles registrados", int(self.standings_df["goals_for"].sum()) if not self.standings_df.empty else 0),
        ]

        for index, (label, value) in enumerate(metrics):
            metrics_frame.grid_columnconfigure(index, weight=1)
            card = ctk.CTkFrame(metrics_frame, corner_radius=8)
            card.grid(row=0, column=index, sticky="ew", padx=6)
            ctk.CTkLabel(card, text=label, text_color="#9ca3af").pack(pady=(16, 4))
            ctk.CTkLabel(card, text=str(value), font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(0, 16))

        top_df = self.standings_df.head(8)
        rows = [
            (
                row["position"],
                row["team"],
                row["points"],
                row["goals_for"],
                row["goals_against"],
                row["goal_difference"],
            )
            for _, row in top_df.iterrows()
        ]
        self.create_table(
            self.main_frame,
            ("Posicion", "Equipo", "Puntos", "GF", "GC", "DG"),
            rows,
            height=8,
        )

    def show_standings(self):
        self.clear_main_frame()
        self.add_title("Clasificacion", "Tabla actual ordenada por posicion.")

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
        )

    def show_matches(self):
        self.clear_main_frame()
        self.add_title("Partidos", "Consulta los partidos registrados de un equipo.")

        controls = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=8)

        selected_team = ctk.StringVar(value=self.teams_list[0] if self.teams_list else "")
        selector = ctk.CTkOptionMenu(
            controls,
            values=self.teams_list,
            variable=selected_team,
            width=280,
        )
        selector.pack(side="left", padx=(0, 12))

        table_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        table_container.pack(fill="both", expand=True)

        def render_matches():
            for widget in table_container.winfo_children():
                widget.destroy()

            matches_df = load_matches_by_team(selected_team.get())
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
            )

        ctk.CTkButton(controls, text="Consultar", command=render_matches, width=130).pack(side="left")
        render_matches()

    def show_prediction(self):
        self.clear_main_frame()
        self.add_title(
            "Prediccion",
            "Comparacion de equipos y estimacion Poisson basada en clasificacion, goles y forma.",
        )

        if len(self.teams_list) < 2:
            ctk.CTkLabel(self.main_frame, text="No hay suficientes equipos para comparar.").pack(pady=24)
            return

        controls = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=8)

        home_team = ctk.StringVar(value=self.teams_list[0])
        away_team = ctk.StringVar(value=self.teams_list[1])

        ctk.CTkLabel(controls, text="Local").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(controls, values=self.teams_list, variable=home_team, width=260).pack(side="left", padx=(0, 18))
        ctk.CTkLabel(controls, text="Visitante").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(controls, values=self.teams_list, variable=away_team, width=260).pack(side="left", padx=(0, 18))

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

            matches_df = load_combined_matches(home_team.get(), away_team.get())
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
            self.create_table(results_frame, ("Metrica", "Equipo", "Valor"), rows, height=10)

        ctk.CTkButton(controls, text="Analizar partido", command=render_prediction, width=150).pack(side="left")
        render_prediction()


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
