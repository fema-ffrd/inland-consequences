import os
import pandas as pd

def update_foundation_types(df):
    """
    Update the FLSBT codes (4-letter strings) to the NSI-style foundation codes (1-letter abbreviations).
    This allows for separation of FLSBT naming conventions from the DDF lookup logic.

    Parameters:
    -----------
    df : DataFrame with 'foundation_type' column containing FLSBT-style codes (e.g., 'PILE', 'SHAL', 'SLAB', 'BASE')
    
    Returns:
    DataFrame with 'foundation_type' column updated to NSI-style codes
    """

    # dictionary to map NSI-style foundation types to FLSBT foundation types (note many-to-one mapping)
    foundation_lookups = {
        "C": "SHAL", # Crawl
        "B": "BASE", # Basement
        "S": "SLAB", # Slab
        "P": "SHAL", # Pier
        "F": "SLAB", # Fill
        "W": "SHAL", # Solid Wall
        "I": "PILE"  # Pile
    }

    # Create a DataFrame for the foundation lookups
    foundation_df = pd.DataFrame(list(foundation_lookups.items()), columns=['found_type', 'FLSBT_Foundation_Type'])

    # join the foundation lookups to the original DataFrame to get the NSI-style foundation type
    df_merge = pd.merge(df, foundation_df, left_on='foundation_type', right_on='FLSBT_Foundation_Type', how='left')

    # overwrite the original column values with the new values from the lookup, then drop the extra columns
    df_merge['foundation_type'] = df_merge['found_type']
    df_merge = df_merge.drop(columns=['FLSBT_Foundation_Type', 'found_type'])

    return df_merge


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

    # cast all columns to lowercase
    result_df.columns = [col.lower() for col in result_df.columns]

    # update foundation types to NSI-style codes
    result_df = update_foundation_types(result_df)
    
    return result_df


if __name__ == "__main__":
    # Example usage and testing
    foundation_flood_csv_path = 'data/foundation_flood_table_inv.csv'

    df_results = unpivot_foundation_flood_table_inv(foundation_flood_csv_path)
    print("Unpivoted Foundation/Flood Table Sample:")
    print(df_results.sample(10))

    df_results.to_csv('outputs/df_lookup_inventory.csv', index=False)
