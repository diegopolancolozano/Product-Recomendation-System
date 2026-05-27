from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_categories(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        file_path,
        sep="|",
        header=None,
        names=["category_id", "category_name"],
        dtype={"category_id": "Int64", "category_name": "string"},
    )
    return df.dropna(subset=["category_id"])


def load_product_category(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(file_path, sep="|")
    df = df.rename(columns={"v.Code_pr": "product_id", "v.code": "category_id"})
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df["category_id"] = pd.to_numeric(df["category_id"], errors="coerce").astype("Int64")
    return df.dropna(subset=["product_id", "category_id"])


def load_transactions(transactions_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for file_path in sorted(Path(transactions_dir).glob("*_Tran.csv")):
        df = pd.read_csv(
            file_path,
            sep="|",
            header=None,
            names=["date", "store_id", "customer_id", "product_list"],
            dtype={
                "date": "string",
                "store_id": "string",
                "customer_id": "string",
                "product_list": "string",
            },
        )
        if df.empty:
            continue
        df["source_file"] = file_path.name
        df["transaction_id"] = df.index.astype("int64")
        df["transaction_uid"] = (
            df["source_file"].str.replace("_Tran.csv", "", regex=False)
            + "-"
            + df["transaction_id"].astype(str)
        )
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        frames.append(df)

    if not frames:
        return pd.DataFrame(
            columns=[
                "date",
                "store_id",
                "customer_id",
                "product_list",
                "source_file",
                "transaction_id",
                "transaction_uid",
            ]
        )

    return pd.concat(frames, ignore_index=True)


def explode_items(
    transactions: pd.DataFrame, product_category: pd.DataFrame, categories: pd.DataFrame
) -> pd.DataFrame:
    items = transactions.copy()
    items["product_id"] = items["product_list"].fillna("").str.split()
    items = items.explode("product_id")
    items = items[items["product_id"].notna() & (items["product_id"] != "")]
    items["product_id"] = pd.to_numeric(items["product_id"], errors="coerce").astype("Int64")
    items = items.dropna(subset=["product_id"])
    items = items.merge(product_category, on="product_id", how="left")
    items = items.merge(categories, on="category_id", how="left")
    items["category_name"] = items["category_name"].fillna("Unknown")
    return items


def load_data(base_dir: Path) -> dict[str, pd.DataFrame]:
    base_dir = Path(base_dir)
    categories = load_categories(base_dir / "Products" / "Categories.csv")
    product_category = load_product_category(base_dir / "Products" / "ProductCategory.csv")
    transactions = load_transactions(base_dir / "Transactions")
    items = explode_items(transactions, product_category, categories)
    return {
        "categories": categories,
        "product_category": product_category,
        "transactions": transactions,
        "items": items,
    }
