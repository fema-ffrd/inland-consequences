"""
From the Hazus flood specific building types task deliverable, extract the damage curves into
machine readable formats that match what has been done for Hazus.

File used for this exercise comes from "Task4D work, and is entitled "Damage_Function_Deliverable_2-5-2024.xlsx"

NOTE: This script will require a dependency not in the pyproject.toml: openpyxl
"""

import pandas as pd
from pandas.tests.test_downstream import df

pd.set_option('display.max_columns', None)

def extract_structure_damage_curves(damage_curves_excel: str) -> pd.DataFrame:
    """
    Extract Structure Damage Function tab from the Hazus flood damage curves Excel file.

    Args:
        damage_curves_excel (str): Path to the Hazus flood damage curves Excel file.
    
    Returns:
        pd.DataFrame: DataFrame containing the extracted structure damage curves.
    """
    sheet_name = "Structure Damage Function"
    df = pd.read_excel(damage_curves_excel, sheet_name=sheet_name)

    # filter to only relevant columns for structure (includes -12' to 24', with half-foot increments from -2' to 2')
    relevant_columns = [
        "DDF_ID", # new damage function id, not the old Hazus one
        "Originator Source", # source agency
        "-12'", "-11'", "-10'", "-9'", "-8'", "-7'", "-6'", "-5'", "-4'", "-3'",
        "-2'", "-1.5'", "-1'", "-0.5'", "0'", "0.5'", "1'", "1.5'", "2'",
        "3'", "4'", "5'", "6'", "7'", "8'", "9'", "10'", "11'", "12'",
        "13'", "14'", "15'", "16'", "17'", "18'", "19'", "20'", "21'", "22'", "23'", "24'"
    ]
    df = df[relevant_columns]

    # rename columns to match hazus format for depths (including half-foot increments)
    rename_dict = {
        "-12'": "ft12m", "-11'": "ft11m", "-10'": "ft10m", "-9'": "ft09m",
        "-8'": "ft08m", "-7'": "ft07m", "-6'": "ft06m", "-5'": "ft05m",
        "-4'": "ft04m", "-3'": "ft03m", "-2'": "ft02m", "-1.5'": "ft1_5m",
        "-1'": "ft01m", "-0.5'": "ft0_5m",
        "0'": "ft00", "0.5'": "ft0_5", "1'": "ft01", "1.5'": "ft1_5", "2'": "ft02",
        "3'": "ft03", "4'": "ft04", "5'": "ft05", "6'": "ft06",
        "7'": "ft07", "8'": "ft08", "9'": "ft09", "10'": "ft10", "11'": "ft11",
        "12'": "ft12", "13'": "ft13", "14'": "ft14", "15'": "ft15", "16'": "ft16",
        "17'": "ft17", "18'": "ft18", "19'": "ft19", "20'": "ft20", "21'": "ft21",
        "22'": "ft22", "23'": "ft23", "24'": "ft24"
    }
    df = df.rename(columns=rename_dict)
    df = df.replace("Null", pd.NA)
    return df


def extract_content_damage_curves(damage_curves_excel: str) -> pd.DataFrame:
    """
    Extract Content Damage Function tab from the Hazus flood damage curves Excel file.

    Args:
        damage_curves_excel (str): Path to the Hazus flood damage curves Excel file.
    
    Returns:
        pd.DataFrame: DataFrame containing the extracted content damage curves.
    """
    sheet_name = "Content Damage Function"
    df = pd.read_excel(damage_curves_excel, sheet_name=sheet_name)

    # filter to only relevant columns for content (includes -12' to 24', with half-foot increments from -2' to 2')
    relevant_columns = [
        "DDF_ID", # new damage function id, not the old Hazus one
        "Originator Source", # source agency
        "-12'", "-11'", "-10'", "-9'", "-8'", "-7'", "-6'", "-5'", "-4'", "-3'",
        "-2'", "-1.5'", "-1'", "-0.5'", "0'", "0.5'", "1'", "1.5'", "2'",
        "3'", "4'", "5'", "6'", "7'", "8'", "9'", "10'", "11'", "12'",
        "13'", "14'", "15'", "16'", "17'", "18'", "19'", "20'", "21'", "22'", "23'", "24'"
    ]
    df = df[relevant_columns]

    # rename columns to match hazus format for depths (including half-foot increments)
    rename_dict = {
        "-12'": "ft12m", "-11'": "ft11m", "-10'": "ft10m", "-9'": "ft09m",
        "-8'": "ft08m", "-7'": "ft07m", "-6'": "ft06m", "-5'": "ft05m",
        "-4'": "ft04m", "-3'": "ft03m", "-2'": "ft02m", "-1.5'": "ft1_5m",
        "-1'": "ft01m", "-0.5'": "ft0_5m",
        "0'": "ft00", "0.5'": "ft0_5", "1'": "ft01", "1.5'": "ft1_5", "2'": "ft02",
        "3'": "ft03", "4'": "ft04", "5'": "ft05", "6'": "ft06",
        "7'": "ft07", "8'": "ft08", "9'": "ft09", "10'": "ft10", "11'": "ft11",
        "12'": "ft12", "13'": "ft13", "14'": "ft14", "15'": "ft15", "16'": "ft16",
        "17'": "ft17", "18'": "ft18", "19'": "ft19", "20'": "ft20", "21'": "ft21",
        "22'": "ft22", "23'": "ft23", "24'": "ft24"
    }
    df = df.rename(columns=rename_dict)
    df = df.replace("Null", pd.NA)
    return df


def extract_inventory_damage_curves(damage_curves_excel: str) -> pd.DataFrame:
    """
    Extract Inventory Damage Function tab from the Hazus flood damage curves Excel file.

    Args:
        damage_curves_excel (str): Path to the Hazus flood damage curves Excel file.
    
    Returns:
        pd.DataFrame: DataFrame containing the extracted inventory damage curves.
    """
    sheet_name = "Inventory Damage Function"
    df = pd.read_excel(damage_curves_excel, sheet_name=sheet_name)

    # filter to only relevant columns for inventory (starts from -8', includes half-foot increments)
    relevant_columns = [
        "DDF_ID", # new damage function id, not the old Hazus one
        "Originator Source", # source agency
        "-8'", "-7'", "-6'", "-5'", "-4'", "-3'", "-2'", "-1.5'", "-1'", "-0.5'",
        "0'", "0.5'", "1'", "1.5'", "2'", "3'", "4'", "5'", "6'", "7'", "8'", "9'",
        "10'", "11'", "12'", "13'", "14'", "15'", "16'", "17'", "18'", "19'", "20'",
        "21'", "22'", "23'", "24'"
    ]
    df = df[relevant_columns]

    # rename columns to match hazus format for depths (including half-foot increments)
    rename_dict = {
        "-8'": "ft08m", "-7'": "ft07m", "-6'": "ft06m", "-5'": "ft05m",
        "-4'": "ft04m", "-3'": "ft03m", "-2'": "ft02m", "-1.5'": "ft1_5m",
        "-1'": "ft01m", "-0.5'": "ft0_5m",
        "0'": "ft00", "0.5'": "ft0_5", "1'": "ft01", "1.5'": "ft1_5",
        "2'": "ft02", "3'": "ft03", "4'": "ft04", "5'": "ft05", "6'": "ft06",
        "7'": "ft07", "8'": "ft08", "9'": "ft09", "10'": "ft10", "11'": "ft11",
        "12'": "ft12", "13'": "ft13", "14'": "ft14", "15'": "ft15", "16'": "ft16",
        "17'": "ft17", "18'": "ft18", "19'": "ft19", "20'": "ft20", "21'": "ft21",
        "22'": "ft22", "23'": "ft23", "24'": "ft24"
    }
    df = df.rename(columns=rename_dict)
    df = df.replace("Null", pd.NA)
    return df


def correct_damage_function_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply corrections to null values in damage function curves.
    
    Rules:
    1. Null values below the lowest depth (before first non-null) are set to 0
    2. Null values above the highest depth (after last non-null) are set to the highest damage percentage
    3. Null values between lowest and highest depths are interpolated linearly using closest non-null neighbors
    
    Args:
        df (pd.DataFrame): DataFrame with damage curves (must have DDF_ID and depth columns)
    
    Returns:
        pd.DataFrame: DataFrame with corrected null values
    """
    # Identify metadata columns (non-depth columns)
    metadata_cols = ["DDF_ID", "Originator Source"]
    depth_cols = [col for col in df.columns if col not in metadata_cols]
    
    # Create a copy to avoid modifying original
    df_corrected = df.copy()
    
    # Process each row (each damage function)
    for idx in df_corrected.index:
        # Get values as a numpy array for easier scalar access
        row_values = df_corrected.loc[idx, depth_cols].values
        
        # Find first and last non-null indices
        non_null_indices = [i for i, val in enumerate(row_values) if pd.notna(val)]
        
        if len(non_null_indices) > 0:
            first_valid_pos = non_null_indices[0]
            last_valid_pos = non_null_indices[-1]
            
            # Get the maximum damage value for this curve
            max_damage = max(row_values[non_null_indices])
            
            # Process each depth column
            for i, col in enumerate(depth_cols):
                if pd.isna(row_values[i]):
                    if i < first_valid_pos:
                        # Before first non-null: set to 0
                        df_corrected.at[idx, col] = 0.0
                    elif i > last_valid_pos:
                        # After last non-null: set to max damage
                        df_corrected.at[idx, col] = max_damage
                    else:
                        # Between first and last non-null: interpolate using closest neighbors
                        # Find previous non-null value
                        prev_idx = None
                        for j in range(i - 1, -1, -1):
                            if pd.notna(row_values[j]):
                                prev_idx = j
                                break
                        
                        # Find next non-null value
                        next_idx = None
                        for j in range(i + 1, len(depth_cols)):
                            if pd.notna(row_values[j]):
                                next_idx = j
                                break
                        
                        # Interpolate linearly between neighbors
                        if prev_idx is not None and next_idx is not None:
                            prev_val = row_values[prev_idx]
                            next_val = row_values[next_idx]
                            # Linear interpolation
                            weight = (i - prev_idx) / (next_idx - prev_idx)
                            interpolated_val = prev_val + weight * (next_val - prev_val)
                            df_corrected.at[idx, col] = interpolated_val
    
    return df_corrected


def find_decreasing_damage_curves(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find rows with decreasing damage values across depth columns.
    
    Checks for any instances where damage percentage decreases as depth increases,
    which indicates a data quality issue in the damage curves.
    
    Args:
        df (pd.DataFrame): DataFrame with damage curves (must have depth columns from ft00 to ft24)
    
    Returns:
        pd.DataFrame: Subset of input DataFrame containing only rows with decreasing values
    """
    depth_columns = [f"ft{str(i).zfill(2)}" for i in range(0, 25)]
    
    def has_decreasing_values(row):
        for i in range(len(depth_columns) - 1):
            if pd.notnull(row[depth_columns[i]]) and pd.notnull(row[depth_columns[i + 1]]):
                if row[depth_columns[i]] > row[depth_columns[i + 1]]:
                    return True
        return False
    
    return df[df.apply(has_decreasing_values, axis=1)]


def extract_damage_curves(damage_curves_excel: str, sheet_name: str) -> pd.DataFrame:
    """
    Extract 1 tab from the Hazus flood damage curves Excel file.
    
    DEPRECATED: Use extract_structure_damage_curves(), extract_content_damage_curves(), 
    or extract_inventory_damage_curves() instead for better handling of sheet-specific columns.

    Args:
        damage_curves_excel (str): Path to the Hazus flood damage curves Excel file.
        sheet_name (str): The sheet name to extract.
    
    Returns:
        pd.DataFrame: DataFrame containing the extracted damage curves.
    """
    # Route to appropriate specialized function
    if sheet_name == "Structure Damage Function":
        df = extract_structure_damage_curves(damage_curves_excel)
    elif sheet_name == "Content Damage Function":
        df = extract_content_damage_curves(damage_curves_excel)
    elif sheet_name == "Inventory Damage Function":
        df = extract_inventory_damage_curves(damage_curves_excel)
    else:
        raise ValueError(f"Unknown sheet name: {sheet_name}")
    
    return correct_damage_function_nulls(df)


if __name__ == "__main__":

    damage_curves_excel = "data/Damage_Function_Deliverable_2-5-2024.xlsx"
    
    # Extract structure damage curves
    print("="*80)
    print("STRUCTURE DAMAGE FUNCTIONS")
    print("="*80)
    df_structure = extract_damage_curves(damage_curves_excel, "Structure Damage Function")
    print(df_structure.sample(min(5, len(df_structure))))
    print(f"Total structure damage functions: {len(df_structure)}")
    df_structure.to_csv("outputs/damage_curves_structure.csv", index=False)
    
    # Extract content damage curves
    print("\n" + "="*80)
    print("CONTENT DAMAGE FUNCTIONS")
    print("="*80)
    df_content = extract_damage_curves(damage_curves_excel, "Content Damage Function")
    print(df_content.sample(min(5, len(df_content))))
    print(f"Total content damage functions: {len(df_content)}")
    df_content.to_csv("outputs/damage_curves_contents.csv", index=False)
    
    # Extract inventory damage curves
    print("\n" + "="*80)
    print("INVENTORY DAMAGE FUNCTIONS")
    print("="*80)
    df_inventory = extract_damage_curves(damage_curves_excel, "Inventory Damage Function")
    print(df_inventory.sample(min(5, len(df_inventory))))
    print(f"Total inventory damage functions: {len(df_inventory)}")
    df_inventory.to_csv("outputs/damage_curves_inventory.csv", index=False)

    # # QC: Check for decreasing damage values
    # print("="*80)
    # print("QC: Structure - Rows with any decreasing values from ft00 to ft24:")
    # print("="*80)
    # decreasing_rows_structure = find_decreasing_damage_curves(df_structure)
    # print(decreasing_rows_structure)
    
    # if not decreasing_rows_structure.empty:
    #     print("\nDDF_IDs with decreasing values:")
    #     print(decreasing_rows_structure["DDF_ID"].tolist())
    
    # print("\n" + "="*80)
    # print("QC: Content - Rows with any decreasing values from ft00 to ft24:")
    # print("="*80)
    # decreasing_rows_content = find_decreasing_damage_curves(df_content)
    # print(decreasing_rows_content)
    
    # if not decreasing_rows_content.empty:
    #     print("\nDDF_IDs with decreasing values:")
    #     print(decreasing_rows_content["DDF_ID"].tolist())
    
    # print("\n" + "="*80)
    # print("QC: Inventory - Rows with any decreasing values from ft00 to ft24:")
    # print("="*80)
    # decreasing_rows_inventory = find_decreasing_damage_curves(df_inventory)
    # print(decreasing_rows_inventory)
    
    # if not decreasing_rows_inventory.empty:
    #     print("\nDDF_IDs with decreasing values:")
    #     print(decreasing_rows_inventory["DDF_ID"].tolist())


