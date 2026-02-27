import pandas as pd

def read_excel_file(file_path):
    df = pd.read_excel(file_path)

    # Ensure correct column names
    df = df.rename(columns=lambda x: x.strip())

    required_columns = ["First_Name", "Last_Name", "State"]

    for col in required_columns:
        if col not in df.columns:
            raise Exception(f"Missing required column: {col}")

    rows = df[required_columns].to_dict(orient="records")

    return rows