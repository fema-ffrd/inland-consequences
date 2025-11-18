import os
import pandas as pd

def unpivot_foundation_flood_table_inv(filepath_or_df):
    """
    Unpivot the foundation type and flood peril type table (for inventory).

    The CSV has a first column with Occupancy Types
    The CSV has two header rows:
    - Row 1: Foundation Type (PILE, SHAL, SLAB, BASE repeating)
    - Row 2: Flood Peril Type (RLS, RHS, RLL, RHL, CST, CMV, CHW repeating)
    
    Returns a long table with columns:
    - Occupancy_Type
    - Foundation_Type
    - Flood_Peril_Type
    - Damage_Function_ID
    
    Parameters:
    -----------
    filepath_or_df : str or DataFrame
        Either path to CSV file or DataFrame with the foundation/flood data
    Returns:
    --------
    DataFrame
        Unpivoted long format DataFrame

    """
    
    # Load data with first two rows as headers
    if isinstance(filepath_or_df, str):
        df = pd.read_csv(filepath_or_df, header=[0, 1])
    else:
        df = filepath_or_df.copy()
    
    # The first column should be the occupancy_type values
    # After reading with header=[0,1], the DataFrame may have a MultiIndex for columns
    # or a single-level Index depending on the CSV. Normalize the first column name
    # to a simple string 'occupancy_type' so downstream code can access it reliably.
    if hasattr(df.columns, 'levels') and getattr(df.columns, 'nlevels', 1) > 1:
        # MultiIndex: replace the first tuple with a simple string
        cols = list(df.columns)
        cols[0] = 'occupancy_type'
        df.columns = cols
    else:
        # Single-level columns: just rename the first column
        first_col = df.columns[0]
        df = df.rename(columns={first_col: 'occupancy_type'})
    
    # Build long format table
    rows = []
    
    for _, row in df.iterrows():
        occupancy = row['occupancy_type']
        
        # Iterate through all other columns (which are tuples of (Foundation, Peril))
        for col in df.columns[1:]:
            if isinstance(col, tuple) and len(col) == 2:
                foundation = col[0]  # First header row value
                peril = col[1]       # Second header row value
                damage_id = row[col]
                
                rows.append({
                    'occupancy_type': occupancy,
                    'Foundation_Type': foundation,
                    'Flood_Peril_Type': peril,
                    'Damage_Function_ID': damage_id
                })
    
    result_df = pd.DataFrame(rows)
    
    # Sort for readability
    result_df = result_df.sort_values(['occupancy_type', 'Foundation_Type', 'Flood_Peril_Type'])
    result_df = result_df.reset_index(drop=True)
    
    return result_df


if __name__ == "__main__":
    # Example usage and testing
    foundation_flood_csv_path = 'data/foundation_flood_table_inv.csv'

    df_results = unpivot_foundation_flood_table_inv(foundation_flood_csv_path)
    print("Unpivoted Foundation/Flood Table Sample:")
    print(df_results.sample(10))

