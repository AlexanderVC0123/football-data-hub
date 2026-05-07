import argparse

from app.config import DEFAULT_COMPETITIONS
from app.database.connection import execute_schema, test_connection
from app.services.import_service import sync_competitions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sincroniza datos de Football Data Hub.")
    parser.add_argument(
        "--competition",
        help="Codigo de una competicion. Ejemplos: PD, PL, SA, BL1, FL1.",
    )
    parser.add_argument(
        "--competitions",
        nargs="+",
        help="Lista de competiciones a sincronizar. Ejemplo: --competitions PD PL SA.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Sincroniza las competiciones por defecto: {', '.join(DEFAULT_COMPETITIONS)}.",
    )
    args = parser.parse_args()

    if args.all:
        competition_codes = DEFAULT_COMPETITIONS
    elif args.competitions:
        competition_codes = [code.upper() for code in args.competitions]
    elif args.competition:
        competition_codes = [args.competition.upper()]
    else:
        competition_codes = ["PD"]

    print("Iniciando Football Data Hub...")
    print(f"Competiciones seleccionadas: {', '.join(competition_codes)}")

    test_connection()
    execute_schema()
    sync_competitions(competition_codes)
