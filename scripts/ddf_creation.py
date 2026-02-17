import os
import pandas as pd

def generate_flsbt_lookup_table():
    """
    Generate a complete lookup table that maps:
    (Construction Type, Occupancy Type, Story Range, SQFT Range) → FLSBT Range
    
    This replaces the complex conditional logic with a simple table lookup.
    """
    
    rows = []
    
    # Helper function to add rows
    def add_row(construction, occupancies, story_min, story_max, flsbt_base, sqft_min=None, sqft_max=None):
        """Add a row for each occupancy type in the list"""
        if isinstance(occupancies, str):
            occupancies = [occupancies]
        
        # Determine FLSBT range format
        if flsbt_base in ["MH", "MLRI", "SPMB"]:
            # No story suffix
            flsbt_range = flsbt_base
        elif story_min == story_max:
            # Single story
            flsbt_range = f"{flsbt_base}{story_min:03d}"
        else:
            # Story range
            flsbt_range = f"{flsbt_base}{story_min:03d}-{story_max:03d}"
        
        for occ in occupancies:
            rows.append({
                'Construction_Type': construction,
                'Occupancy_Type': occ,
                'Story_Min': story_min,
                'Story_Max': story_max,
                'SQFT_Min': sqft_min,
                'SQFT_Max': sqft_max,
                'FLSBT_Range': flsbt_range
            })
    
    # ==================== MANUFACTURED HOMES ====================
    add_row('H', 'RES2', 1, 999, 'MH')
    add_row('MH', 'RES2', 1, 999, 'MH')
    
    # ==================== WOOD (W) ====================
    
    # WSF: RES1, RES3A (1-4 stories)
    add_row('W', ['RES1', 'RES3A'], 1, 1, 'WSF')
    add_row('W', ['RES1', 'RES3A'], 2, 4, 'WSF')
    
    # WMUH: RES3B-F, RES4-6 (1-4 stories)
    wmuh_occs = ['RES3B', 'RES3C', 'RES3D', 'RES3E', 'RES3F', 'RES4', 'RES5', 'RES6']
    add_row('W', wmuh_occs, 1, 1, 'WMUH')
    add_row('W', wmuh_occs, 2, 4, 'WMUH')
    
    # WLRM: COM1, COM9 (1-2 stories)
    add_row('W', ['COM1', 'COM9'], 1, 2, 'WLRM')
    
    # WLRI: COM1, COM9 (3-6 stories)
    add_row('W', ['COM1', 'COM9'], 3, 6, 'WLRI')
    
    # WLRI: Other commercial/industrial (1-6 stories)
    wlri_occs = ['COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM10',
                 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6',
                 'REL1', 'AGR1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('W', wlri_occs, 1, 6, 'WLRI')
    
    # ==================== MASONRY (M) ====================
    
    # MSF: RES1, RES3A (1-7 stories)
    add_row('M', ['RES1', 'RES3A'], 1, 1, 'MSF')
    add_row('M', ['RES1', 'RES3A'], 2, 4, 'MSF')
    add_row('M', ['RES1', 'RES3A'], 5, 7, 'MSF')
    
    # MMUH: RES3B (1-7 stories)
    add_row('M', 'RES3B', 1, 1, 'MMUH')
    add_row('M', 'RES3B', 2, 4, 'MMUH')
    add_row('M', 'RES3B', 5, 7, 'MMUH')
    
    # MLRM: COM1, COM9 (1-2 stories)
    add_row('M', ['COM1', 'COM9'], 1, 2, 'MLRM')
    
    # MLRI: IND1, AGR1 (1 story only, no suffix)
    add_row('M', ['IND1', 'AGR1'], 1, 1, 'MLRI')
    
    # MERB: RES3C-F, RES4-6 (1-30 stories)
    merb_occs = ['RES3C', 'RES3D', 'RES3E', 'RES3F', 'RES4', 'RES5', 'RES6']
    add_row('M', merb_occs, 1, 1, 'MERB')
    add_row('M', merb_occs, 2, 4, 'MERB')
    add_row('M', merb_occs, 5, 30, 'MERB')
    
    # MECB: COM1, COM9 (3+ stories), IND1, AGR1 (3+ stories)
    add_row('M', ['COM1', 'COM9'], 3, 4, 'MECB')
    add_row('M', ['COM1', 'COM9'], 5, 30, 'MECB')
    
    add_row('M', ['IND1', 'AGR1'], 2, 4, 'MECB')
    add_row('M', ['IND1', 'AGR1'], 5, 30, 'MECB')

    # MECB: Other commercial/industrial (1-30 stories)
    mecb_occs = ['COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM10',
                 'IND2', 'IND3', 'IND4', 'IND5', 'IND6',
                 'REL1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('M', mecb_occs, 1, 4, 'MECB')
    add_row('M', mecb_occs, 5, 30, 'MECB')
    
    # ==================== CONCRETE (C) ====================
    
    # CSF: RES1, RES3A (1-40 stories)
    add_row('C', ['RES1', 'RES3A'], 1, 1, 'CSF')
    add_row('C', ['RES1', 'RES3A'], 2, 4, 'CSF')
    add_row('C', ['RES1', 'RES3A'], 5, 40, 'CSF')
    
    # CERB: RES3B-F, RES4-6 (1-40 stories)
    cerb_occs = ['RES3B', 'RES3C', 'RES3D', 'RES3E', 'RES3F', 'RES4', 'RES5', 'RES6']
    add_row('C', cerb_occs, 1, 1, 'CERB')
    add_row('C', cerb_occs, 2, 4, 'CERB')
    add_row('C', cerb_occs, 5, 40, 'CERB')
    
    # CECB: All commercial/industrial (1-40 stories)
    cecb_occs = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10',
                 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6',
                 'REL1', 'AGR1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('C', cecb_occs, 1, 4, 'CECB')
    add_row('C', cecb_occs, 5, 40, 'CECB')
    
    # ==================== STEEL (S) ====================
    
    # SPMB: COM1, COM2, IND1-6, AGR1 (≤4000 sqft, no story suffix)
    spmb_occs = ['COM1', 'COM2', 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6', 'AGR1']
    add_row('S', spmb_occs, 1, 108, 'SPMB', sqft_min=0, sqft_max=4000)
    
    # SERB: All residential (1-108 stories)
    serb_occs = ['RES1', 'RES3A', 'RES3B', 'RES3C', 'RES3D', 'RES3E', 'RES3F', 'RES4', 'RES5', 'RES6']
    add_row('S', serb_occs, 1, 1, 'SERB')
    add_row('S', serb_occs, 2, 4, 'SERB')
    add_row('S', serb_occs, 5, 108, 'SERB')
    
    # SECB: COM1, COM2, IND1-6, AGR1 (>4000 sqft, 1-108 stories)
    secb1_occs = ['COM1', 'COM2', 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6', 'AGR1']
    add_row('S', secb1_occs, 1, 4, 'SECB', sqft_min=4001, sqft_max=None)
    add_row('S', secb1_occs, 5, 108, 'SECB', sqft_min=4001, sqft_max=None)
    
    # SECB: Other commercial/institutional (1-108 stories)
    secb2_occs = ['COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10',
                  'REL1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('S', secb2_occs, 1, 4, 'SECB')
    add_row('S', secb2_occs, 5, 108, 'SECB')
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Sort for better readability
    df = df.sort_values(['Construction_Type', 'Occupancy_Type', 'Story_Min'])
    df = df.reset_index(drop=True)
    
    return df


def lookup_flsbt(df, lookup_table):
    """
    Perform direct lookup to find FLSBT_Range for each building.
    
    Parameters:
    -----------
    df : DataFrame with columns S_GENERALBUILDINGTYPE, S_OCCTYPE, S_NUMSTORY, S_SQFT
    lookup_table : DataFrame returned by generate_flsbt_lookup_table()
    
    Returns:
    --------
    DataFrame with added FLSBT_Range column
    """
    df = df.copy()
    
    # Normalize inputs
    df['_construction'] = df['S_GENERALBUILDINGTYPE'].str.upper().str.strip()
    df['_occupancy'] = df['S_OCCTYPE'].str.upper().str.strip()
    df['_stories'] = pd.to_numeric(df['S_NUMSTORY'], errors='coerce')
    df['_sqft'] = pd.to_numeric(df.get('S_SQFT', 0), errors='coerce').fillna(0)
    
    # Initialize result column
    df['FLSBT_Range'] = None
    
    # For each row in the lookup table, find matching buildings
    for _, rule in lookup_table.iterrows():
        mask = (
            (df['_construction'] == rule['Construction_Type']) &
            (df['_occupancy'] == rule['Occupancy_Type']) &
            (df['_stories'] >= rule['Story_Min']) &
            (df['_stories'] <= rule['Story_Max'])
        )
        
        # Apply SQFT filters if specified
        if pd.notna(rule['SQFT_Min']):
            mask &= (df['_sqft'] >= rule['SQFT_Min'])
        if pd.notna(rule['SQFT_Max']):
            mask &= (df['_sqft'] <= rule['SQFT_Max'])
        
        df.loc[mask, 'FLSBT_Range'] = rule['FLSBT_Range']
    
    # Clean up temporary columns
    df = df.drop(columns=['_construction', '_occupancy', '_stories', '_sqft'])
    
    return df


def unpivot_foundation_flood_table(filepath_or_df):
    """
    Unpivot the foundation type and flood peril type table.
    
    The CSV has two header rows:
    - Row 1: Foundation Type (PILE, SHAL, SLAB, BASE repeating)
    - Row 2: Flood Peril Type (RLS, RHS, RLL, RHL, CST, CMV, CHW repeating)
    
    Returns a long table with columns:
    - FLSBT_Range
    - Foundation_Type
    - Flood_Peril_Type
    - Damage_Function_ID
    
    Parameters:
    -----------
    filepath_or_df : str or DataFrame
        Either path to CSV file or DataFrame with the foundation/flood data
    """
    
    # Load data with first two rows as headers
    if isinstance(filepath_or_df, str):
        df = pd.read_csv(filepath_or_df, header=[0, 1])
    else:
        df = filepath_or_df.copy()
    
    # The first column should be the FLSBT values
    # After reading with header=[0,1], the DataFrame may have a MultiIndex for columns
    # or a single-level Index depending on the CSV. Normalize the first column name
    # to a simple string 'FLSBT_Range' so downstream code can access it reliably.
    if hasattr(df.columns, 'levels') and getattr(df.columns, 'nlevels', 1) > 1:
        # MultiIndex: replace the first tuple with a simple string
        cols = list(df.columns)
        cols[0] = 'FLSBT_Range'
        df.columns = cols
    else:
        # Single-level columns: just rename the first column
        first_col = df.columns[0]
        df = df.rename(columns={first_col: 'FLSBT_Range'})
    
    # Build long format table
    rows = []
    
    for _, row in df.iterrows():
        flsbt = row['FLSBT_Range']
        
        # Iterate through all other columns (which are tuples of (Foundation, Peril))
        for col in df.columns[1:]:
            if isinstance(col, tuple) and len(col) == 2:
                foundation = col[0]  # First header row value
                peril = col[1]       # Second header row value
                damage_id = row[col]
                
                rows.append({
                    'FLSBT_Range': flsbt,
                    'Foundation_Type': foundation,
                    'Flood_Peril_Type': peril,
                    'Damage_Function_ID': damage_id
                })
    
    result_df = pd.DataFrame(rows)
    
    # Sort for readability
    result_df = result_df.sort_values(['FLSBT_Range', 'Foundation_Type', 'Flood_Peril_Type'])
    result_df = result_df.reset_index(drop=True)
    
    return result_df

def update_foundation_types(df):
    """
    Update the FLSBT codes (4-letter strings) to the NSI-style foundation codes (1-letter abbreviations).
    This allows for separation of FLSBT naming conventions from the DDF lookup logic.

    Parameters:
    -----------
    df : DataFrame with 'Foundation_Type' column containing FLSBT-style codes (e.g., 'PILE', 'SHAL', 'SLAB', 'BASE')
    
    Returns:
    DataFrame with 'Foundation_Type' column updated to NSI-style codes
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


# Generate and display the lookup table
def create_complete_lookup_table(foundation_flood_csv_path):
    """
    Create a completely flattened lookup table that combines:
    1. FLSBT assignment rules (Construction + Occupancy + Stories + SQFT → FLSBT)
    2. Foundation/Flood damage functions (FLSBT + Foundation + Flood Peril → Damage ID)
    
    Parameters:
    -----------
    foundation_flood_csv_path : str
        Path to the CSV file containing foundation/flood peril damage functions
    
    Returns:
    --------
    DataFrame with columns:
        - Construction_Type
        - Occupancy_Type
        - Story_Min
        - Story_Max
        - SQFT_Min
        - SQFT_Max
        - FLSBT_Range
        - Foundation_Type
        - Flood_Peril_Type
        - Damage_Function_ID
    """
    
    # Generate FLSBT lookup table
    print("Generating FLSBT lookup table...")
    flsbt_lookup = generate_flsbt_lookup_table()
    
    # Load and unpivot foundation/flood table
    print(f"Loading foundation/flood table from {foundation_flood_csv_path}...")
    foundation_flood = unpivot_foundation_flood_table(foundation_flood_csv_path)
    
    # Join the two tables on FLSBT_Range
    print("Merging tables...")
    complete_table = flsbt_lookup.merge(
        foundation_flood,
        on='FLSBT_Range',
        how='left'
    )
    
    # Sort for readability
    complete_table = complete_table.sort_values([
        'Construction_Type', 
        'Occupancy_Type', 
        'Story_Min',
        'Foundation_Type',
        'Flood_Peril_Type'
    ])
    complete_table = complete_table.reset_index(drop=True)

    # cast all columns to lowercase
    complete_table.columns = [col.lower() for col in complete_table.columns]

    # update foundation types to NSI-style codes
    complete_table = update_foundation_types(complete_table)

    print(f"\nComplete! Generated {len(complete_table)} total lookup rules")
    print(f"  - {len(flsbt_lookup)} unique FLSBT ranges")
    print(f"  - {len(complete_table['foundation_type'].unique())} foundation types")
    print(f"  - {len(complete_table['flood_peril_type'].unique())} flood peril types")
    
    return complete_table





if __name__ == "__main__":
    # Ensure output directory exists
    os.makedirs('outputs', exist_ok=True)
    
    # Generate and save FLSBT lookup table
    lookup_table = generate_flsbt_lookup_table()
    
    print(f"Generated {len(lookup_table)} FLSBT lookup rules")
    print("\nSample FLSBT rules:")
    print(lookup_table.head(20))
    
    lookup_table.to_csv('outputs/flsbt_lookup_table.csv', index=False)
    print("\nSaved FLSBT rules to outputs/flsbt_lookup_table.csv")
    
    # Generate and save complete flattened lookup table
    print("\n" + "="*60)
    print("GENERATING COMPLETE FLATTENED TABLE:")
    print("="*60)
    
    complete_table = create_complete_lookup_table('data/foundation_flood_table.csv')
    print("\nSample from complete table:")
    print(complete_table.head(20))
    
    complete_table.to_csv('outputs/df_lookup_structures.csv', index=False)
    print("\nSaved complete lookup table to outputs/df_lookup_structures.csv")