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
    add_row('M', ['COM1', 'COM9'], 3, 30, 'MECB')
    add_row('M', ['IND1', 'AGR1'], 3, 30, 'MECB')
    
    # MECB: Other commercial/industrial (1-30 stories)
    mecb_occs = ['COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM10',
                 'IND2', 'IND3', 'IND4', 'IND5', 'IND6',
                 'REL1', 'GOV1', 'GOV2', 'EDU1', 'EDU2']
    add_row('M', mecb_occs, 1, 30, 'MECB')
    
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


# Generate and display the lookup table
if __name__ == "__main__":
    lookup_table = generate_flsbt_lookup_table()
    
    print(f"Generated {len(lookup_table)} lookup rules")
    print("\nSample rows:")
    print(lookup_table.head(20))
    
    # Save to CSV
    lookup_table.to_csv('flsbt_lookup_table.csv', index=False)
    print("\nSaved to flsbt_lookup_table.csv")
    
    # Example usage
    print("\n" + "="*60)
    print("EXAMPLE USAGE:")
    print("="*60)
    
    # Create sample building data
    sample_buildings = pd.DataFrame({
        'S_GENERALBUILDINGTYPE': ['W', 'M', 'C', 'S', 'W'],
        'S_OCCTYPE': ['RES1', 'COM1', 'RES3B', 'COM1', 'COM1'],
        'S_NUMSTORY': [2, 5, 15, 2, 4],
        'S_SQFT': [2000, 10000, 50000, 3000, 15000]
    })
    
    print("\nSample Buildings:")
    print(sample_buildings)
    
    # Perform lookup
    result = lookup_flsbt(sample_buildings, lookup_table)
    
    print("\nResults with FLSBT_Range:")
    print(result[['S_GENERALBUILDINGTYPE', 'S_OCCTYPE', 'S_NUMSTORY', 'S_SQFT', 'FLSBT_Range']])