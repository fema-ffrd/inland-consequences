import os
import pandas as pd
import numpy as np

"""
This script processes the 2025 OpenHazus damage function lookup table for riverine contents,
expanding foundation types, peril types, occupancy/story ranges, and construction types,
and exports the final DataFrame to a CSV file for use in the inland consequences model.

The new OpenHazusDDFUpdates_2025.xlsx file is the source for the updated damage function lookup
tables. The previous method relied on flood specific building types which have been deprecated and
will only be discoverable through the git history of the repository.
"""

def read_riverine_content_excel_table(file_path, sheet_name="Proposed Contents DDF"):
    """Read the riverine content from the 2025 OpenHazus content damage function lookup table
    
    Args:
        file_path (str): Path to the Excel file (OpenHazusDDFUpdates_2025.xlsx)
        sheet_name (str): Name of the sheet to read from the Excel file
    
    Returns:
        pd.DataFrame: DataFrame containing the riverine content data
    """
    # read the proposed content tab, subsetting to the freshwater (riverine) content columns
    df = pd.read_excel(file_path,
                       sheet_name=sheet_name,
                       usecols=[0, 1, 2, 3, 4])

    # drop row 0 (title row) and row 1 ("Freshwater" header), keeping occupancy col for now
    df = df.drop(index=1).reset_index(drop=True)

    # extract occupancy values from col 0 before dropping it (data rows start at index 2)
    occupancy = df.iloc[2:, 0].reset_index(drop=True)

    # drop col 0 now that occupancy is saved
    df = df.iloc[:, 1:]

    # infill the missing merged-cell values for duration labels
    df.iloc[1, 1] = "Short Duration"
    df.iloc[1, 3] = "Long Duration"

    # set first two rows as a MultiIndex header
    new_header = df.iloc[0:2]
    df = df.iloc[2:].reset_index(drop=True)
    df.columns = pd.MultiIndex.from_arrays(new_header.values)

    # set occupancy as the index so it survives the stack
    df.index = occupancy
    df.index.name = "Occupancy"

    # unpivot: stack MultiIndex columns into rows, then flatten index to columns
    df = df.stack(level=[0, 1]).reset_index()
    df.columns = ["Occupancy", "Base Type", "Duration", "DDF Value"]

    return df

def expand_foundation_types(df):
    """Expand foundation types in the DataFrame by duplicating rows for each foundation type.
    
    Args:
        df (pd.DataFrame): Input DataFrame with a 'Base Type' column
    
    Returns:
        pd.DataFrame: Expanded DataFrame with separate rows for each foundation type
    """
    # generate a foundation map and dataframe
    foundation_map = [
        ("NOBASE", "SHALLOW"),
        ("NOBASE", "SLAB"),
        ("NOBASE", "PILE"),
        ("BASE",   "BASEMENT"),
    ]

    df_foundation = pd.DataFrame(foundation_map, columns=["Base Type", "Foundation Type"])

    # outer join to duplicate rows for each foundation type
    df_expanded = df.merge(df_foundation, on="Base Type", how="outer")

    return df_expanded

def expand_peril_type(df):
    """Expand peril types in the DataFrame by duplicating rows for each peril type.
    
    Args:
        df (pd.DataFrame): Input DataFrame with a 'Duration' column
    
    Returns:
        pd.DataFrame: Expanded DataFrame with separate rows for each peril type
    """
    # generate a peril map and dataframe
    peril_map = [
        ("Short Duration", "RLS"),
        ("Short Duration", "RHS"),
        ("Long Duration", "RLL"),
        ("Long Duration", "RHL"),
    ]

    df_peril = pd.DataFrame(peril_map, columns=["Duration", "flood_peril_type"])

    # outer join to duplicate rows for each peril type
    df_expanded = df.merge(df_peril, on="Duration", how="outer")

    return df_expanded

def expand_occupancy_story_ranges(df):
    """Expand occupancy and story ranges in the DataFrame by duplicating rows for each story count.
    
    Args:
        df (pd.DataFrame): Input DataFrame with an 'Occupancy' column and complex story ranges (ex:
            'RES1, 1 Story', 'RES3, 1-3 Story', 'RES3, 4+ Story', 'RES2')

    Returns:
        pd.DataFrame: Expanded DataFrame with separate rows for each story count
    """
    # define a helper function to parse story ranges
    def parse_story_range(story_range_str):
        if story_range_str == '1 Story':
            return (1, 999)
        elif story_range_str == '2 Story+':
            return (2, 999)
        elif story_range_str == '1-3 Story':
            return (1, 3)
        elif story_range_str == '4+ Story':
            return (4, 999)
        elif story_range_str == '2 Story +':
            return (2, 999)
        else:
            raise ValueError(f"Unrecognized story range: {story_range_str}")
        
    # get the occupancy values (always coded first, before any commas)
    occupancies = []
    for _, row in df.iterrows():
        if ',' not in row['Occupancy']:
            occupancies.append(row['Occupancy'])
        else:
            occupancies.append(row['Occupancy'].split(',')[0].strip())

    # hard-code story range strings
    story_min = []
    story_max = []
    for _, row in df.iterrows():
        if ',' not in row['Occupancy']:
            story_min.append(np.nan)
            story_max.append(np.nan)
        else:
            story_range_str = row['Occupancy'].split(',')[1].strip()
            min_story, max_story = parse_story_range(story_range_str)
            story_min.append(min_story)
            story_max.append(max_story)

    # ensure occupancy, story_min, story_max and the original df have the same length
    assert len(occupancies) == len(story_min) == len(story_max) == len(df)

    # add the new columns to the dataframe
    df = df.copy()
    df['occupancy_type'] = occupancies
    df['story_min'] = story_min
    df['story_max'] = story_max

    # expand the RES3 rows to the set {'RES3A', 'RES3E', 'RES3C', 'RES3B', 'RES3F', 'RES3D'}
    _expanded = []
    for _, row in df.iterrows():
        if row['occupancy_type'] == 'RES3':
            for suffix in ['A', 'E', 'C', 'B', 'F', 'D']:
                new_row = row.copy()
                new_row['occupancy_type'] = f'RES3{suffix}'
                _expanded.append(new_row)
        else:
            _expanded.append(row)

    df_expanded = pd.DataFrame(_expanded)
    df_expanded = df_expanded[df_expanded['occupancy_type']!='RES3'].reset_index(drop=True)

    return df_expanded

def expand_construction_types(df):
    """Expand construction types in the DataFrame by duplicating rows for each construction type.

    NOTE: Besides RES2 (which will have either H or MH construction types), all other occupancy types
    will have C, M, S, and W construction types.

    Args:
        df (pd.DataFrame): Input DataFrame
    
    Returns:
        pd.DataFrame: Expanded DataFrame with separate rows for each construction type
    """
    # generate a construction map and dataframe
    construction_map = []
    for occ_type in df['occupancy_type'].unique():
        if occ_type == 'RES2':
            construction_map.append((occ_type, 'H'))
            construction_map.append((occ_type, 'MH'))
        else:
            for ctype in ['C', 'M', 'S', 'W']:
                construction_map.append((occ_type, ctype))

    df_construction = pd.DataFrame(construction_map, columns=["occupancy_type", "construction_type"])

    # outer join to duplicate rows for each construction type
    df_expanded = df.merge(df_construction, on="occupancy_type", how="outer")

    return df_expanded

def prepare_for_export(df):
    """Rename fields and reorganize columns in the DataFrame before exporting.
    
    Args:
        df (pd.DataFrame): Input DataFrame
    Returns:
        pd.DataFrame: Reorganized DataFrame
    """
    # rename columns
    df = df.rename(columns={
        "DDF Value": "damage_function_id",
        "Foundation Type": "foundation_type",
    })

    # add sqft min/max columns (to match previous schema) and set to null
    df['sqft_min'] = np.nan
    df['sqft_max'] = np.nan

    # define the desired column order (and omit unneeded columns)
    desired_order = [
        "construction_type",
        "occupancy_type",
        "story_min",
        "story_max",
        "sqft_min",
        "sqft_max",
        "foundation_type",
        "flood_peril_type",
        "damage_function_id",
        "Duration",
        "Base Type",
    ]

    # reorder the columns
    df_reordered = df[desired_order]

    return df_reordered


if __name__ == "__main__":
    print("="*60)

    # read the riverine content data from the Excel file
    excel_path = "data/source_data/OpenHazusDDFUpdates_2025.xlsx"
    sheet_name = "Proposed Contents DDF"
    contents_df = read_riverine_content_excel_table(excel_path, sheet_name)

    # expand foundation types
    length_before = len(contents_df)
    contents_df2 = expand_foundation_types(contents_df)
    length_after = len(contents_df2)
    print(contents_df2)
    print(f"Length before expansion: {length_before}")
    print(f"Length after expansion: {length_after}")
    print("="*60)

    # expand peril types
    length_before = len(contents_df2)
    contents_df3 = expand_peril_type(contents_df2)
    length_after = len(contents_df3)
    print(contents_df3)
    print(f"Length before expansion: {length_before}")
    print(f"Length after expansion: {length_after}")
    print("="*60)

    # expand story ranges to min/max stories
    length_before = len(contents_df3)
    contents_df4 = expand_occupancy_story_ranges(contents_df3)
    length_after = len(contents_df4)
    print(contents_df4)
    print(f"Length before expansion: {length_before}")
    print(f"Length after expansion: {length_after}")
    print("="*60)

    # expand with contstruction types
    contents_df5 = expand_construction_types(contents_df4)
    length_before = len(contents_df4)
    length_after = len(contents_df5)
    print(contents_df5)
    print(f"Length before expansion: {length_before}")
    print(f"Length after expansion: {length_after}")
    print("="*60)

    # reorganzie columns before exporting
    final_contents_df = prepare_for_export(contents_df5)
    print(final_contents_df)

    print(f"Count of damage functions: {final_contents_df['damage_function_id'].nunique()}")

    # export to CSV
    output_path = "outputs/df_lookup_contents.csv"
    final_contents_df.to_csv(output_path, index=False)
    print(f"Exported final contents DataFrame to: {output_path}")



    # #  TEMP - ensure the new DFs have all the same occupancy types (passed)
    # df_original = pd.read_csv('src/inland_consequences/data/df_lookup_contents.csv')
    # original_occupancy_types = set(df_original['occupancy_type'].unique())
    # new_occupancy_types = set(contents_df4['occupancy_type'].unique())
    # missing_occupancy_types = original_occupancy_types - new_occupancy_types
    # if len(missing_occupancy_types) > 0:
    #     print("MISSING OCCUPANCY TYPES IN NEW DF:")
    #     print(missing_occupancy_types)
    # else:
    #     print("ALL OCCUPANCY TYPES PRESENT IN NEW DF.")


