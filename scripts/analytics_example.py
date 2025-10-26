"""Example: use analytics helpers to load data and save CSVs.

Run this from the project root inside the venv:

    source .venv/bin/activate
    set -a; source .env; set +a
    python scripts/analytics_example.py

"""
from pathlib import Path
from app.analytics import get_engine, get_items_df, get_users_df, items_summary


def main():
    engine = get_engine()

    items = get_items_df(engine=engine)
    users = get_users_df(engine=engine)
    summary = items_summary(engine=engine)

    out = Path("analytics_output")
    out.mkdir(exist_ok=True)

    items.to_csv(out / "items.csv", index=False)
    users.to_csv(out / "users.csv", index=False)
    summary.to_csv(out / "items_summary.csv", index=False)

    print("Wrote analytics CSVs to:", out)


if __name__ == "__main__":
    main()
