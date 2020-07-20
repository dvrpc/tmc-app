import pandas as pd
from os import environ
from pathlib import Path
from datetime import time
from sqlalchemy import create_engine
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")


def flatten_headers(input_file: Path,
                    tabname: str) -> list:
    """
    Transform a multi-level header into a single header row.

    For example:
        - 'Southbound / U Turns' becomes 'SB U'
        - 'Eastbound / Straight Through' becomes 'EB Thru'
    """

    replacements_level_1 = {
        "Southbound": "SB ",
        "Westbound": "WB ",
        "Northbound": "NB ",
        "Eastbound": "EB "
    }

    replacements_level_2 = {
        "u turns": "U",
        "left turns": "Left",
        "straight through": "Thru",
        "right turns": "Right",
        "peds in crosswalk": "Peds Xwalk",
        "bikes in crosswalk": "Bikes Xwalk",
        "time": "time",

        # handle the expected typos!
        "bikes in croswalk": "Bikes Xwalk",
        "peds in croswalk": "Peds Xwalk",
    }

    df = pd.read_excel(input_file,
                       nrows=3,
                       header=None,
                       sheet_name=tabname)

    headers = []

    # Start off with a blank l1
    l1 = ""

    for col in df.columns:
        level_1 = df.at[1, col]
        level_2 = df.at[2, col]

        # Update the l1 anytime a value is found
        if not pd.isna(level_1):
            if level_1 not in replacements_level_1:
                l1 = level_1
                msg = f"!!! '{level_1}' isn't included in the level 1 lookup. It won't be renamed."
                print(msg)
            else:
                l1 = replacements_level_1[level_1]

        # Warn the user if the file has unexpected headers!
        # If it does, use the raw value instead of our nicely formatted one
        if level_2.lower() in replacements_level_2:
            l2 = replacements_level_2[level_2.lower()]
        else:
            msg = f"!!! '{level_2}' isn't included in the level 2 lookup. It won't be renamed."
            print(msg)
            l2 = level_2

        headers.append(l1 + l2)

    return headers


class SQLUpload:
    """
    Efficiently extract data from Excel and import into SQL.

    """

    def __init__(self,
                 project_id: int,
                 file_id: int,
                 filepath: Path,):

        self._pid = project_id
        self._fid = file_id
        self._filepath = filepath

    def read_data(self,
                  tabname: str,
                  col_prefix: str):
        """
        Minimalist approach to reading the XLS files.

        Parameters
        ----------
            - tabname: name of tab in the excel file
            - col_prefix: whatever you want to use at
                          the beginning of the column names.
        """

        df = pd.read_excel(self._filepath,
                           skiprows=3,
                           header=None,
                           names=flatten_headers(self._filepath, tabname),
                           sheet_name=tabname).dropna()

        # Check all time values and ensure that each one
        # is formatted as a datetime.time. Some aren't by default!
        for idx, row in df.iterrows():

            if type(row.time) != time:
                hour, minute = row.time.split(":")
                df.at[idx, "time"] = time(
                    hour=int(hour),
                    minute=int(minute)
                )

        # Reindex on the time column
        df.set_index("time", inplace=True)

        # Clean up column names for SQL
        #  Prefix all columns. i.e. "SB U" -> "Light SB U"
        new_cols = {}
        for col in df.columns:
            nice_prefix = col_prefix.lower()
            nice_col = col.replace(" ", "_").lower()

            # Special handling for bikes and peds
            # If it's one of these, set it as the mode
            for val in ["bikes_", "peds_"]:
                if val in nice_col:
                    nice_col = nice_col.replace(val, "")
                    nice_prefix = val[:-1]

            new_cols[col] = f"{nice_prefix}_{nice_col}"

        df.rename(
            columns=new_cols,
            inplace=True
        )

        return df

    def spliced_light_and_heavy_df(self):

        df_light = self.read_data("Light Vehicles", "Light")
        df_heavy = self.read_data("Heavy Vehicles", "Heavy")

        df = pd.concat([df_light, df_heavy], axis=1, sort=False)

        df["fid"] = int(self._fid)

        return df

    def publish_to_database(self,
                            db_uri: str = SQLALCHEMY_DATABASE_URI,
                            df: pd.DataFrame = None,
                            pg_table_name: str = None,):

        if not df:
            df = self.spliced_light_and_heavy_df()
        if not pg_table_name:
            pg_table_name = f"data_p{self._pid}_f{self._fid}"

        engine = create_engine(db_uri)

        kwargs = {
            "if_exists": "replace",
        }

        df.to_sql(pg_table_name, engine, **kwargs)

        engine.dispose()
