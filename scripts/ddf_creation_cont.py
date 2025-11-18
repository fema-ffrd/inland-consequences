import os
import pandas as pd
import numpy as np


def generate_flsbt_lookup_table():
    """
    Generate a complete lookup table (for contents) that maps:
    (Construction Type, Occupancy Type, Story Range, SQFT Range) → FLSBT Range
    
    This replaces the complex conditional logic with a simple table lookup.
    """

    rows = []

    # Helper function to add rows
    def add_row(construction, occupancies, story_min, story_max, flsbt_base, sqft_min=np.nan, sqft_max=np.nan):
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
    add_row('H', 'RES2', 1, 999, 'MH', None, None)
    add_row('MH', 'RES2', 1, 999, 'MH', None, None)

    # ==================== WOOD (W) ====================
    
    # WSF: RES1, RES3A (1-4 stories)
    add_row('W', ['RES1', 'RES3A'], 1, 1, 'WSF', None, None)
    add_row('W', ['RES1', 'RES3A'], 2, 4, 'WSF', None, None)

    # WMUH: RES3B-F, RES4-6 (1-4 stories)
    wmuh_occs = ['RES3B', 'RES3C', 'RES3D', 'RES3E', 'RES3F', 'RES4', 'RES5', 'RES6']
    add_row('W', wmuh_occs, 1, 1, 'WMUH', None, None)
    add_row('W', wmuh_occs, 2, 4, 'WMUH', None, None)

    # WLRM: special case, occupancy-based
    # add_row('W', ['COM1', 'COM9'], 1, 2, 'WLRM', None, None) # Original - structures version
    wlrm_occs = ['COM1', 'COM2', 'COM3', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10',
                 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6',
                 'REL1', 'AGR1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('W', wlrm_occs, 1, 2, 'WLRM', None, None)  # Updated - contents version
    add_row('W', ['COM4'], 1, 1, 'WLRM', None, None)  # COM4 1 Story
    add_row('W', ['COM4'], 2, 2, 'WLRM', None, None)  # COM4 2 Story+
    
    # # WLRI: COM1, COM9 (3-6 stories): special case, Missing from Source Table so integrating below
    # add_row('W', ['COM1', 'COM9'], 3, 6, 'WLRI', None, None)

    # WLRI: special case, occupancy-based
    wlri_occs = ['COM1', 'COM2', 'COM3', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9','COM10',
                 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6',
                 'REL1', 'AGR1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('W', wlri_occs, 1, 6, 'WLRI', None, None) # Updated - contents version
    add_row('W', ['COM4'], 1, 1, 'WLRI', None, None)  # COM4 1 Story
    add_row('W', ['COM4'], 2, 6, 'WLRI', None, None)  # COM4 2 Story+

    # ==================== MASONRY (M) ====================
    
    # MSF: RES1, RES3A (1-7 stories)
    add_row('M', ['RES1', 'RES3A'], 1, 1, 'MSF', None, None)
    add_row('M', ['RES1', 'RES3A'], 2, 4, 'MSF', None, None)
    add_row('M', ['RES1', 'RES3A'], 5, 7, 'MSF', None, None)

    # MMUH: RES3B (1-7 stories)
    add_row('M', 'RES3B', 1, 1, 'MMUH', None, None)
    add_row('M', 'RES3B', 2, 4, 'MMUH', None, None)
    add_row('M', 'RES3B', 5, 7, 'MMUH', None, None)

    # MLRM: COM1, COM9 (1-2 stories)
    add_row('M', ['COM1', 'COM9'], 1, 2, 'MLRM', None, None)

    # MLRI: IND1, AGR1 (1 story only, no suffix)
    add_row('M', ['IND1', 'AGR1'], 1, 1, 'MLRI', None, None)

    # MERB: RES3C-F, RES4-6 (1-30 stories)
    merb_occs = ['RES3C', 'RES3D', 'RES3E', 'RES3F', 'RES4', 'RES5', 'RES6']
    add_row('M', merb_occs, 1, 1, 'MERB', None, None)
    add_row('M', merb_occs, 2, 4, 'MERB', None, None)
    add_row('M', merb_occs, 5, 30, 'MERB', None, None)

    # # MECB: COM1, COM9 (3+ stories): special case, Missing from Source Table so integrating below
    # add_row('M', ['COM1', 'COM9'], 1, 30, 'MECB', None, None)

    # MECB: Other commercial/industrial (1-30 stories)
    mecb_occs = ['COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM10',
                 'IND2', 'IND3', 'IND4', 'IND5', 'IND6',
                 'REL1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('M', mecb_occs, 1, 30, 'MECB', None, None)

    # ==================== CONCRETE (C) ====================
    
    # CSF: RES1, RES3A (1-40 stories)
    add_row('C', ['RES1', 'RES3A'], 1, 1, 'CSF', None, None)
    add_row('C', ['RES1', 'RES3A'], 2, 4, 'CSF', None, None)
    add_row('C', ['RES1', 'RES3A'], 5, 40, 'CSF', None, None) 

    # CERB: RES3B-F, RES4-6 (1-40 stories)
    cerb_occs = ['RES3B', 'RES3C', 'RES3D', 'RES3E', 'RES3F', 'RES4', 'RES5', 'RES6']
    add_row('C', cerb_occs, 1, 1, 'CERB', None, None)
    add_row('C', cerb_occs, 2, 4, 'CERB', None, None)
    add_row('C', cerb_occs, 5, 40, 'CERB', None, None)

    # CECB: All commercial/industrial (1-40 stories) TODO: See Occupancy Table
    cecb_occs = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10',
                 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6',
                 'REL1', 'AGR1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('C', cecb_occs, 1, 4, 'CECB', None, None)
    add_row('C', cecb_occs, 5, 40, 'CECB', None, None)

    # ==================== STEEL (S) ====================
    
    # SPMB: COM1, COM2, IND1-6, AGR1 (≤4000 sqft, no story suffix) TODO: See Occupancy Table
    spmb_occs = ['COM1', 'COM2', 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6', 'AGR1']
    add_row('S', spmb_occs, 1, 108, 'SPMB', None, None) # TODO: Resolve if <4000sf?

    # SERB: All residential (1-108 stories)
    serb_occs = ['RES1', 'RES3A', 'RES3B', 'RES3C', 'RES3D', 'RES3E', 'RES3F', 'RES4', 'RES5', 'RES6']
    add_row('S', serb_occs, 1, 1, 'SERB')
    add_row('S', serb_occs, 2, 4, 'SERB')
    add_row('S', serb_occs, 5, 108, 'SERB')

    # SECB: COM1, COM2, IND1-6, AGR1 (>4000 sqft, 1-108 stories) TODO: See Occupancy Table
    secb1_occs = ['COM1', 'COM2', 'IND1', 'IND2', 'IND3', 'IND4', 'IND5', 'IND6', 'AGR1']
    add_row('S', secb1_occs, 1, 4, 'SECB', sqft_min=4001, sqft_max=None) # TODO: See occupancy table
    add_row('S', secb1_occs, 5, 108, 'SECB', sqft_min=4001, sqft_max=None) # TODO: See occupancy table

    # # SECB: Other commercial/institutional (1-108 stories)
    # secb2_occs = ['COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10',
    #               'REL1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    # add_row('S', secb2_occs, 1, 4, 'SECB')
    # add_row('S', secb2_occs, 5, 108, 'SECB')

    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Sort for better readability
    df = df.sort_values(['Construction_Type', 'Occupancy_Type', 'Story_Min'])
    df = df.reset_index(drop=True)
    
    return df



def unpivot_foundation_flood_table_cont(filepath_or_df):
    """
    Unpivot the foundation type and flood peril type table (for contents).

    The CSV has a first column with flood specific building types (FLSBT)
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
    
    # Normalize the first column name to 'FLSBT_Range'
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

                # # Skip only if damage_id is blank or NaN (keep -9999)
                # if pd.isna(damage_id) or damage_id == '':
                #     continue

                rows.append({
                    'FLSBT_Range': flsbt,
                    'Foundation_Type': foundation,
                    'Flood_Peril_Type': peril,
                    'Damage_Function_ID': damage_id
                })
    
    result_df = pd.DataFrame(rows)
    
    # Convert Damage_Function_ID to integer
    result_df['Damage_Function_ID'] = result_df['Damage_Function_ID'].astype(int)

    # Sort for readability
    result_df = result_df.sort_values(['FLSBT_Range', 'Foundation_Type', 'Flood_Peril_Type'])
    result_df = result_df.reset_index(drop=True)

    print(f"Unpivoted foundation/flood table with {len(result_df)} rows")
    print(result_df.head(10))
    
    return result_df


def unpivot_occupancy_flood_table_cont(filepath_or_df):
    """
    Unpivot the occupancy-based foundation type and flood peril type table (for contents).

    The CSV has a first column with occupancy types (COM1, COM2, etc.)
    Some occupancy types include story information (e.g., "COM4 1 Story", "COM4 2 Story+")
    
    The CSV has two header rows:
    - Row 1: Foundation Type (PILE, SHAL, SLAB, BASE repeating)
    - Row 2: Flood Peril Type (RLS, RHS, RLL, RHL, CST, CMV, CHW repeating)
    
    Returns a long table with columns:
    - Occupancy_Type (normalized to base occupancy)
    - Story_Min
    - Story_Max
    - Foundation_Type
    - Flood_Peril_Type
    - Damage_Function_ID
    
    Parameters:
    -----------
    filepath_or_df : str or DataFrame
        Either path to CSV file or DataFrame with the occupancy/flood data
    
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
    
    # Normalize the first column name to 'Occupancy_Type'
    if hasattr(df.columns, 'levels') and getattr(df.columns, 'nlevels', 1) > 1:
        # MultiIndex: replace the first tuple with a simple string
        cols = list(df.columns)
        cols[0] = 'Occupancy_Type'
        df.columns = cols
    else:
        # Single-level columns: just rename the first column
        first_col = df.columns[0]
        df = df.rename(columns={first_col: 'Occupancy_Type'})
    
    # Helper function to parse occupancy type with embedded story info
    def parse_occupancy_type(occ_string):
        """
        Parse occupancy type string and extract base occupancy and story range.
        
        Examples:
        - "COM4 1 Story" → ("COM4", 1, 1)
        - "COM4 2 Story+" → ("COM4", 2, 999)
        - "COM1" → ("COM1", NaN, NaN)
        """
        occ_string = str(occ_string).strip()
        
        # Pattern: "OCCTYPE 1 Story" (single story)
        if " 1 Story" in occ_string:
            base_occ = occ_string.replace(" 1 Story", "").strip()
            return (base_occ, 1, 1)
        
        # Pattern: "OCCTYPE 2 Story+" (story and above)
        if " 2 Story+" in occ_string:
            base_occ = occ_string.replace(" 2 Story+", "").strip()
            return (base_occ, 2, 999)
        
        # No story info embedded
        return (occ_string, np.nan, np.nan)
    
    # Build long format table
    rows = []
    
    for _, row in df.iterrows():
        occupancy_raw = row['Occupancy_Type']
        base_occ, story_min, story_max = parse_occupancy_type(occupancy_raw)
        
        # Iterate through all other columns (which are tuples of (Foundation, Peril))
        for col in df.columns[1:]:
            if isinstance(col, tuple) and len(col) == 2:
                foundation = col[0]  # First header row value
                peril = col[1]       # Second header row value
                damage_id = row[col]

                rows.append({
                    'Occupancy_Type': base_occ,
                    'Story_Min': story_min,
                    'Story_Max': story_max,
                    'Foundation_Type': foundation,
                    'Flood_Peril_Type': peril,
                    'Damage_Function_ID': damage_id
                })
    
    result_df = pd.DataFrame(rows)
    
    # Convert Damage_Function_ID to integer
    result_df['Damage_Function_ID'] = result_df['Damage_Function_ID'].astype(int)

    # Sort for readability
    result_df = result_df.sort_values(['Occupancy_Type', 'Story_Min', 'Foundation_Type', 'Flood_Peril_Type'])
    result_df = result_df.reset_index(drop=True)

    print(f"Unpivoted occupancy/flood table with {len(result_df)} rows")
    print(result_df.head(10))
    
    # Show examples of parsed story information
    print("\nSample rows with story information:")
    story_info = result_df[result_df['Story_Min'].notna()][['Occupancy_Type', 'Story_Min', 'Story_Max', 'Foundation_Type', 'Flood_Peril_Type', 'Damage_Function_ID']].head(10)
    if not story_info.empty:
        print(story_info)
    
    return result_df

##################################




# def lookup_flsbt(df, lookup_table):
#     """
#     Perform direct lookup to find FLSBT_Range for each building.
    
#     Parameters:
#     -----------
#     df : DataFrame with columns S_GENERALBUILDINGTYPE, S_OCCTYPE, S_NUMSTORY, S_SQFT
#     lookup_table : DataFrame returned by generate_flsbt_lookup_table()
    
#     Returns:
#     --------
#     DataFrame with added FLSBT_Range column
#     """
#     df = df.copy()
    
#     # Normalize inputs
#     df['_construction'] = df['S_GENERALBUILDINGTYPE'].str.upper().str.strip()
#     df['_occupancy'] = df['S_OCCTYPE'].str.upper().str.strip()
#     df['_stories'] = pd.to_numeric(df['S_NUMSTORY'], errors='coerce')
#     df['_sqft'] = pd.to_numeric(df.get('S_SQFT', 0), errors='coerce').fillna(0)
    
#     # Initialize result column
#     df['FLSBT_Range'] = None
    
#     # For each row in the lookup table, find matching buildings
#     for _, rule in lookup_table.iterrows():
#         mask = (
#             (df['_construction'] == rule['Construction_Type']) &
#             (df['_occupancy'] == rule['Occupancy_Type']) &
#             (df['_stories'] >= rule['Story_Min']) &
#             (df['_stories'] <= rule['Story_Max'])
#         )
        
#         # Apply SQFT filters if specified
#         if pd.notna(rule['SQFT_Min']):
#             mask &= (df['_sqft'] >= rule['SQFT_Min'])
#         if pd.notna(rule['SQFT_Max']):
#             mask &= (df['_sqft'] <= rule['SQFT_Max'])
        
#         df.loc[mask, 'FLSBT_Range'] = rule['FLSBT_Range']
    
#     # Clean up temporary columns
#     df = df.drop(columns=['_construction', '_occupancy', '_stories', '_sqft'])
    
#     return df


# Generate and display the lookup table
def create_complete_lookup_table(foundation_flood_csv_path):
    """
    Create a completely flattened lookup table for contents that combines:
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
    
    # Generate FLSBT lookup table (contents version)
    print("Generating FLSBT lookup table for contents...")
    flsbt_lookup = generate_flsbt_lookup_table()
    
    # Load and unpivot foundation/flood DF table
    print(f"Loading foundation/flood table from {foundation_flood_csv_path}...")
    foundation_flood = unpivot_foundation_flood_table_cont(foundation_flood_csv_path)

    # Load and unpivot the occupancy-based DF table
    print(f"Loading occupancy/flood table from data/foundation_flood_table_cont2.csv...")
    occupancy_flood = unpivot_occupancy_flood_table_cont(
        'data/foundation_flood_table_cont2.csv'
    )
    
    # Join flsbt_lookup with foundation_flood on FLSBT_Range
    print("\nMerging with FLSBT-based damage functions...")
    complete_table = flsbt_lookup.merge(
        foundation_flood,
        on='FLSBT_Range',
        how='left'
    )
    
    # For rows with Damage_Function_ID = -9999, try to get values from occupancy flood table
    print("\nFilling -9999 damage function IDs with occupancy-based lookups...")
    mask_needs_replacement = complete_table['Damage_Function_ID'] == -9999
    
    if mask_needs_replacement.any():
        print(f"  Found {mask_needs_replacement.sum()} rows with Damage_Function_ID = -9999")
        
        # Get rows that need replacement, keeping the index
        rows_to_update = complete_table[mask_needs_replacement].copy()
        rows_to_update = rows_to_update.reset_index()
        
        # Merge with occupancy flood table on Occupancy_Type, Foundation_Type, Flood_Peril_Type
        # Note: occupancy_flood may have Story_Min/Story_Max that we need to ignore for now
        updated_rows = rows_to_update.drop(columns=['Damage_Function_ID']).merge(
            occupancy_flood[['Occupancy_Type', 'Foundation_Type', 'Flood_Peril_Type', 'Damage_Function_ID']].drop_duplicates(
                subset=['Occupancy_Type', 'Foundation_Type', 'Flood_Peril_Type']
            ),
            on=['Occupancy_Type', 'Foundation_Type', 'Flood_Peril_Type'],
            how='left'
        )
        
        # Set the index back and update the complete_table
        updated_rows = updated_rows.set_index('index')
        complete_table.loc[updated_rows.index, 'Damage_Function_ID'] = updated_rows['Damage_Function_ID']
        
        # Report results
        still_missing = (complete_table['Damage_Function_ID'] == -9999).sum()
        replaced_count = mask_needs_replacement.sum() - still_missing
        print(f"  Successfully replaced {replaced_count} values using occupancy-based lookups")
        if still_missing > 0:
            print(f"  WARNING: {still_missing} rows still have Damage_Function_ID = -9999")
    
    # Sort for readability
    complete_table = complete_table.sort_values([
        'Construction_Type', 
        'Occupancy_Type', 
        'Story_Min',
        'Foundation_Type',
        'Flood_Peril_Type'
    ])
    complete_table = complete_table.reset_index(drop=True)
    
    print(f"\nComplete! Generated {len(complete_table)} total lookup rules")
    print(f"  - {len(flsbt_lookup)} unique FLSBT ranges")
    print(f"  - {len(foundation_flood['Foundation_Type'].unique())} foundation types")
    print(f"  - {len(foundation_flood['Flood_Peril_Type'].unique())} flood peril types")
    print(f"  - {complete_table['Damage_Function_ID'].notna().sum()} rules with damage functions")
    print(f"  - {(complete_table['Damage_Function_ID'] != -9999).sum()} rules with valid damage functions (excluding -9999)")
    
    return complete_table


if __name__ == "__main__":

    lookup_table = generate_flsbt_lookup_table()
    lookup_table.to_csv('outputs/flsbt_lookup_table_contents.csv', index=False)
    
    print(f"Generated {len(lookup_table)} lookup rules")
    print("\nSample rows:")
    print(lookup_table.head(3))

    foundation_df = unpivot_foundation_flood_table_cont(
        'data/foundation_flood_table_cont1.csv'
    )

    foundation_df.to_csv('outputs/unpivoted_foundation_flood_table_contents.csv', index=False)

    print("\nSample unpivoted foundation/flood table, CECB entries:")
    print(foundation_df[foundation_df['FLSBT_Range'].str.contains('CECB')])

    # Unpivot the occupancy-based table
    print("\n" + "="*60)
    print("UNPIVOTING OCCUPANCY-BASED TABLE:")
    print("="*60)
    
    occupancy_df = unpivot_occupancy_flood_table_cont(
        'data/foundation_flood_table_cont2.csv'
    )
    
    occupancy_df.to_csv('outputs/unpivoted_occupancy_flood_table_contents.csv', index=False)
    
    print("\nSample unpivoted occupancy/flood table, COM entries:")
    print(occupancy_df[occupancy_df['Occupancy_Type'].str.contains('COM')])

    # Generate complete lookup table
    print("\n" + "="*60)
    print("GENERATING COMPLETE LOOKUP TABLE FOR CONTENTS:")
    print("="*60)
    
    os.makedirs('outputs', exist_ok=True)
    complete_table = create_complete_lookup_table(
        'data/foundation_flood_table_cont1.csv'
    )
    
    print("\nSample from complete table:")
    print(complete_table.sample(min(30, len(complete_table))))
    
    complete_table.to_csv('outputs/complete_lookup_table_contents.csv', index=False)
    print("\nSaved complete lookup table to outputs/complete_lookup_table_contents.csv")