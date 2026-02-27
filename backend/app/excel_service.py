import pandas as pd
import os


def write_to_excel(data, output_path):
    """
    Writes processed NPI results to Excel.
    """

    if not data:
        raise Exception("No data to write to Excel.")

    # Define exact column order
    columns = [
        "First_Name",
        "Last_Name",
        "State",
        "Found_First_Name",
        "Found_Last_Name",
        "Found_State",
        "Full_Name",
        "NPI",
        "Mailing_Address",
        "Primary_Practice_Address",
        "Secondary_Practice_Address",
        "Taxonomy",
        "Specialty",
        "License",
        "Status",
    ]

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Ensure all expected columns exist
    for col in columns:
        if col not in df.columns:
            df[col] = None

    # Reorder columns
    df = df[columns]

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write to Excel
    df.to_excel(output_path, index=False, engine="openpyxl")