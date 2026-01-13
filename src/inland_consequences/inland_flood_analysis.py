from typing import Dict, Any, Optional, Tuple, List
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction
from .raster_collection import RasterCollection
import inspect
import numpy as np
import pandas as pd
import geopandas as gpd
import duckdb
import pyarrow as pa
from pathlib import Path
from datetime import datetime

# Raster inputs are provided via a RasterCollection instance which
# enforces labeled rasters per return period (depth required, optional
# uncertainty, velocity, duration).


class InlandFloodAnalysis:
    """Vectorized inland flood analysis orchestrator.

    This class expects a raster_input mapping of return_period -> raster-like object
    where each raster implements get_value_vectorized(geometries) -> array-like depths.
    The buildings object must expose a pandas Geo/DataFrame at `buildings.gdf`
    and contain a column with monetary values (building_value_col).
    The vulnerability object must implement calculate_vulnerability(exposure_df)
    and return a DataFrame of damage ratios with the same shape as exposure_df.
    """

    def __init__(
        self,
        raster_collection: RasterCollection,
        buildings: Any,
        vulnerability: AbstractVulnerabilityFunction,
        calculate_aal: bool = True,
        aal_rate_limits: Optional[Tuple[float, float]] = None,
    ) -> None:
        # Must be a RasterCollection instance (validated by its constructor)
        if not isinstance(raster_collection, RasterCollection):
            raise TypeError("raster_collection must be a RasterCollection instance")
        self.conn = None  # type: duckdb.DuckDBPyConnection | None
        self.raster_collection = raster_collection
        self.buildings = buildings
        self.vulnerability: AbstractVulnerabilityFunction = vulnerability
        self.calculate_aal = calculate_aal
        self.aal_rate_limits = aal_rate_limits

        # Since the vulnerability needs the buildings right now we need to think about how to choose them and apply to keep the buildings in sync.

        # Minimal validation
        if not hasattr(self.buildings, "gdf"):
            raise ValueError("buildings must have a .gdf attribute containing building rows")

    def _get_db_identifier(self):
        """Returns the database identifier.  Monkey-patch this for testing in memory databases."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = Path.cwd() / f"inland_flood_analysis_{timestamp}.duckdb"
        return str(db_path)

    # ----------------------------------------------------
    # Helper for Conditional Connection Management
    # ----------------------------------------------------
    def _get_or_create_connection(self):
        """
        Returns the persistent connection if available, otherwise creates a 
        temporary connection for a single operation.
        """
        if self.conn:
            # Mode 1: Context Managed (connection is already open)
            return self.conn, False # conn_is_temporary = False
        else:
            # Mode 2: Standalone (create, use, and close temporary connection)
            db_id = self._get_db_identifier()
            temp_conn = duckdb.connect(database=db_id)
            return temp_conn, True # conn_is_temporary = True

    # ----------------------------------------------------
    # Context Manager Protocol Methods
    # ----------------------------------------------------
    def __enter__(self):
        """Establishes the persistent connection."""
        if self.conn is not None:
            raise RuntimeError("DataProcessor context manager is not re-entrant.")
            
        db_id = self._get_db_identifier()
        self.conn = duckdb.connect(database=db_id)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes the persistent connection."""
        if self.conn:
            self.conn.close()
        self.conn = None # Reset the connection attribute

    def _calculate_exposure(self) -> pd.DataFrame:
        """Vectorized sampling of all rasters for all building geometries.

        Returns:
            DataFrame: rows=buildings.index, cols=return_periods (int)
        """
        gdf = self.buildings.gdf
        geometries = gdf.geometry if "geometry" in gdf.columns else gdf.index.to_series()

        exposures: Dict[int, np.ndarray] = {}
        uncertainties: Dict[int, np.ndarray] = {}

        # Iterate deterministic sorted return periods
        for rp in self.raster_collection.return_periods():
            spec = self.raster_collection.get(rp)
            depth_raster = spec.get("depth")
            uncertainty_spec = spec.get("uncertainty")
            velocity_raster = spec.get("velocity")
            duration_raster = spec.get("duration")

            # Enforce that depth_raster is an AbstractRasterReader instance
            if not isinstance(depth_raster, AbstractRasterReader):
                raise ValueError(f"Depth raster for return period {rp} must be an AbstractRasterReader instance")

            mean_values = np.asarray(depth_raster.get_value_vectorized(geometries))
            if mean_values.shape[0] != len(gdf):
                raise ValueError(f"Raster for return period {rp} returned {mean_values.shape[0]} values but expected {len(gdf)}")

            # Determine uncertainty values
            if uncertainty_spec is None:
                uvals = np.zeros(len(gdf))
            elif isinstance(uncertainty_spec, AbstractRasterReader):
                uvals = np.asarray(uncertainty_spec.get_value_vectorized(geometries))
                if uvals.shape[0] != len(gdf):
                    raise ValueError(f"Uncertainty raster for return period {rp} returned {uvals.shape[0]} values but expected {len(gdf)}")
            elif isinstance(uncertainty_spec, (int, float)):
                uvals = np.full(len(gdf), float(uncertainty_spec))
            else:
                raise ValueError(f"Uncertainty for return period {rp} must be an AbstractRasterReader, numeric, or None")

            # Compute depth columns: mean, min, max
            mean_col = f"flood_depth_{rp}_mean"
            min_col = f"flood_depth_{rp}_min"
            max_col = f"flood_depth_{rp}_max"

            self.buildings.gdf[mean_col] = mean_values
            self.buildings.gdf[min_col] = mean_values - uvals
            self.buildings.gdf[max_col] = mean_values + uvals

            # Optionally sample and attach velocity/duration if provided
            # Always create velocity column: sample if raster provided, otherwise fill with NaN
            vel_col = f"flood_velocity_{rp}"
            if velocity_raster is not None:
                vel_vals = np.asarray(velocity_raster.get_value_vectorized(geometries))
                if vel_vals.shape[0] != len(gdf):
                    raise ValueError(f"Velocity raster for return period {rp} returned {vel_vals.shape[0]} values but expected {len(gdf)}")
                self.buildings.gdf[vel_col] = vel_vals
            else:
                # fill with NaN so downstream code can check for presence
                self.buildings.gdf[vel_col] = np.full(len(gdf), np.nan)

            # Always create duration column: sample if raster provided, otherwise fill with NaN
            dur_col = f"flood_duration_{rp}"
            if duration_raster is not None:
                dur_vals = np.asarray(duration_raster.get_value_vectorized(geometries))
                if dur_vals.shape[0] != len(gdf):
                    raise ValueError(f"Duration raster for return period {rp} returned {dur_vals.shape[0]} values but expected {len(gdf)}")
                self.buildings.gdf[dur_col] = dur_vals
            else:
                self.buildings.gdf[dur_col] = np.full(len(gdf), np.nan)

            exposures[rp] = mean_values
            uncertainties[rp] = uvals

        exposure_df = pd.DataFrame(exposures, index=gdf.index)
        uncertainty_df = pd.DataFrame(uncertainties, index=gdf.index)

        # store uncertainty dataframe for downstream usage
        self.exposure_uncertainty = uncertainty_df
        return exposure_df

    def _calculate_damage(self, exposure_df: pd.DataFrame):
        """Use the vulnerability component to vectorize damage ratio lookup and compute loss.

        Returns:
            loss_df (DataFrame): monetary loss per building (rows) per scenario (cols)
        """
        
        # Placeholder for the damage computations.  Right now SPHERE has this all on the buildings gdf but we might be able to separate it out
        # to determine how we want to represent the interim values and the final values.

        return

    def _calculate_vulnerability(self, exposure_df: pd.DataFrame):
        """Placeholder wrapper for vulnerability calculation.

        Current implementation simply forwards to the provided vulnerability object's
        calculate_vulnerability method. No additional logic is added here; this
        method exists so higher-level orchestration can call a single method.
        """
        # Basic pass-through to the vulnerability object. Consumers may replace
        # this with a more sophisticated, vectorized implementation later.
        self.vulnerability.apply_damage_percentages()
        
        # Attempt a simple call with only exposure. Vulnerability implementations
        # that accept uncertainty may ignore it for now.
        return

    def _calculate_metrics(self, loss_df: pd.DataFrame) -> float:
        """Aggregate losses and optionally compute AAL using trapezoidal integration.

        Assumes keys of raster_input are return periods (ints) and uses AEP = 1/return_period.
        """
        # Sum losses per scenario
        total_losses = loss_df.sum(axis=0)

        # Apply rate limits if present
        if self.aal_rate_limits is not None:
            low, high = self.aal_rate_limits
            total_losses = total_losses.clip(lower=low, upper=high)

        # Prepare arrays for integration: x = AEP, y = total loss
        rps = np.array(list(total_losses.index), dtype=float)
        aeps = 1.0 / rps
        # sort by AEP ascending (from rare to frequent?) we'll sort by AEP
        order = np.argsort(aeps)
        x = np.asarray(aeps[order], dtype=float)
        y = np.asarray(total_losses.values[order], dtype=float)

        # Integrate over AEP domain using trapezoidal rule
        aal = float(np.trapz(y, x))
        return aal

    def run(self) -> Dict[str, Any]:
        exposure_df = self._calculate_exposure()
        self._calculate_vulnerability(exposure_df)
        loss_df = self._calculate_damage(exposure_df)

        # Summarize scenario losses as list of tuples (return_period, total_loss)
        total_losses = loss_df.sum(axis=0)
        # Create scenario_losses as list of (return_period, total_loss)
        rps = [int(x) for x in total_losses.index]
        vals = [float(x) for x in total_losses.values]
        scenario_losses: List[Tuple[int, float]] = list(zip(rps, vals))

        result: Dict[str, Any] = {"scenario_losses": scenario_losses}

        if self.calculate_aal:
            aal = self._calculate_metrics(loss_df)
            result["AAL"] = aal

        return result
    
    def calculate_losses(self):
        # Going to calculate the losses using DuckDB

        # 1. Create DuckDB database file to be persisted the interim results in just the current Path for the script that runs this code.
        # 2. Create table from building data (gdf)
        # 3. Create tables from vulnerability data (csv)
        # 4. Method to gather damage functions from vulnerability function
        # 5. Get the nested values for the depths and uncertainties from the hazard inputs
        # 6. Unpivot the wide damage functions that were gathered to interpolate the damage ratios from the depth and uncertainty
        
        conn, close_after_use = self._get_or_create_connection()
        
        try:
            # Use the connection
            # Enable GeoArrow extensions for spatial data support
            conn.execute("INSTALL spatial;")
            conn.execute("LOAD spatial;")
            conn.execute("CALL register_geoarrow_extensions()")
            
            # Copy buildings to database
            self._create_buildings_table(conn)
            
            # Copy vulnerability tables to database
            self._create_vulnerability_tables(conn)
            
            # Copy hazard inputs to database
            self._create_hazard_tables(conn)    

            # Gather damage functions from vulnerability function
            self._gather_damage_functions(conn)

            # Compute the mean and std. deviation of the damage functions
            self._compute_damage_function_statistics(conn)

            # Calculate damages
            self._calculate_losses(conn)

            # Run AAL
            self._calculate_aal(conn)

        finally:
            # Only close if we created it ourselves (Standalone Mode)
            if close_after_use:
                conn.close()

        return

    def _create_duckdb_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a DuckDB database file in the current working directory.

        Returns:
            DuckDBPyConnection: Connection to the persisted DuckDB database.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = Path.cwd() / f"inland_flood_analysis_{timestamp}.duckdb"
        connection = duckdb.connect(str(db_path))
        return connection

    def _create_buildings_table(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Create a table from the buildings GeoDataFrame.

        Args:
            connection: Active DuckDB connection.
        """
        gdf = self.buildings.gdf

        # Build a standardized DataFrame where columns are the internal field
        # names used by the Buildings/FieldMapping system. This ensures the
        # DuckDB table has predictable column names regardless of the source
        # column names in the provided GeoDataFrame.
        fm = self.buildings.fields

        # Collect all internal properties (input + output)
        props = list(fm.input_fields) + list(fm.output_fields)

        # Build a rename map from source column name -> internal property name
        # (only include columns that actually exist and need renaming).
        rename_map = {
            fm.get_field_name(prop): prop
            for prop in props
            if fm.get_field_name(prop) in gdf.columns and fm.get_field_name(prop) != prop
        }
        
        # Rename in a lightweight way (returns a view/copy as needed) so we do
        # not re-create every column manually; this keeps column objects intact
        # where possible and maintains geometry on GeoDataFrame.
        standardized = gdf.rename(columns=rename_map)

        # Enable GeoArrow extensions for spatial data support
        connection.execute("CALL register_geoarrow_extensions()")

        # Register the standardized DataFrame as a DuckDB table (for Intellisense reasons since it can auto-register)
        standardized_arrow = standardized.to_arrow()

        
        
        connection.execute("DROP TABLE IF EXISTS buildings")
        connection.execute("CREATE TABLE buildings AS SELECT * FROM standardized_arrow")

    def _create_vulnerability_tables(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Create tables from the vulnerability data CSVs.

        Args:
            connection: Active DuckDB connection.
        """
        import pandas as pd
        # Define CSV file paths
        base_path = Path(__file__).parent / "data"
        csv_files = {
            "xref_contents": base_path / "df_lookup_contents.csv",
            "xref_inventory": base_path / "df_lookup_inventory.csv",
            "xref_structures": base_path / "df_lookup_structures.csv",
        }

        for table_name, csv_path in csv_files.items():
            df = pd.read_csv(csv_path)
            arrow_table = pa.Table.from_pandas(df)
            connection.execute(f"DROP TABLE IF EXISTS {table_name}")
            connection.execute(f"CREATE TABLE {table_name} AS SELECT * FROM arrow_table")
        
        df_structure = pd.read_csv(base_path / "df_structure.csv")
        structure_arrow_table = pa.Table.from_pandas(df_structure)

        connection.execute(f"CREATE TABLE ddf_structure AS SELECT * FROM structure_arrow_table")
        
    def _create_hazard_tables(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Create a hazard table using DuckDB SQL from building IDs and return periods, with random depth and std_dev."""
        # Drop the hazard table if it exists
        connection.execute("DROP TABLE IF EXISTS hazard")

        # Use DuckDB SQL to cross join buildings with return periods and randomize depth and std_dev
        # Assumes buildings table has an 'ID' column
        connection.execute('''
            CREATE TABLE hazard AS
            SELECT
                b.ID,
                rp.return_period,
                1 + random() * 6 AS depth,
                CASE WHEN round(random()) = 0 THEN 0 ELSE 2 END AS std_dev
            FROM buildings b
            CROSS JOIN (
                SELECT 25 AS return_period UNION ALL
                SELECT 100 UNION ALL
                SELECT 500 UNION ALL
                SELECT 1000
            ) rp
        ''')
    
    def _gather_damage_functions(self, connection: duckdb.DuckDBPyConnection) -> None:

        # Example attribute columns for matching (update as needed)
        # For demonstration, assume columns: 'YearBuilt', 'BldgType', 'DesignLevel', etc.
        # and lookup tables have min/max columns for each attribute

        # # Structure Damage Functions
        # structure_query = '''
        #     CREATE TABLE structure_damage_functions AS
        #     SELECT b.ID AS building_id, x.damage_function_id
        #     FROM buildings b
        #     JOIN xref_structures x
        #         ON b.occupancy_type = x.occupancy_type
        #         --AND b.BldgType = x.bldg_type
        #         --AND b.DesignLevel = x.design_level
        # '''
        structure_query = '''
        CREATE TABLE structure_damage_functions AS
        WITH 
        curve_matches AS (
            SELECT 
                b.ID,
                c.damage_function_id,
                b.first_floor_height,
                0 as ffh_sig,
                -- NULL attributes match ANY value
                -- Foundation type mapping: NSI codes (I,B,S,P,W,C,F) -> xref names (PILE,BASE,SLAB,SHAL)
                CASE 
                    WHEN b.foundation_type IS NOT NULL AND c.foundation_type IS NOT NULL AND 
                        CASE 
                            WHEN b.foundation_type = 'I' THEN 'PILE'
                            WHEN b.foundation_type = 'B' THEN 'BASE'
                            WHEN b.foundation_type = 'S' THEN 'SLAB'
                            WHEN b.foundation_type = 'P' THEN 'PILE'
                            WHEN b.foundation_type = 'W' THEN 'BASE'
                            WHEN b.foundation_type = 'C' THEN 'SHAL'
                            WHEN b.foundation_type = 'F' THEN 'SHAL'
                            ELSE NULL
                        END != c.foundation_type THEN 0
                    WHEN b.number_stories IS NOT NULL AND c.story_min IS NOT NULL AND c.story_max IS NOT NULL 
                        AND NOT (b.number_stories BETWEEN c.story_min AND c.story_max) THEN 0
                    WHEN 'W' IS NOT NULL AND c.construction_type IS NOT NULL AND 'W' != c.construction_type THEN 0
                    ELSE 1
                END AS is_match
            FROM buildings b
            CROSS JOIN xref_structures c
            WHERE b.occupancy_type = c.occupancy_type
        ),
        filtered_matches AS (
            SELECT ID, damage_function_id, first_floor_height, ffh_sig
            FROM curve_matches
            WHERE is_match = 1
        ),
        curve_frequencies AS (
            SELECT 
                ID, damage_function_id, first_floor_height, ffh_sig,
                COUNT(*) OVER (PARTITION BY ID) AS total_matches,
                COUNT(*) OVER (PARTITION BY ID, damage_function_id) AS curve_count
            FROM filtered_matches
        ),
        unique_scenarios AS (
            SELECT DISTINCT
                ID, damage_function_id, first_floor_height, ffh_sig,
                CAST(curve_count AS DOUBLE) / NULLIF(total_matches, 0) AS weight
            FROM curve_frequencies
        )
        SELECT 
            ID AS building_id,
            damage_function_id,
            first_floor_height,
            ffh_sig,
            weight
        FROM unique_scenarios;
        '''
        connection.execute(structure_query)

        # Content Damage Functions
        content_query = '''
            CREATE TABLE content_damage_functions AS    
            SELECT b.ID AS building_id, x.damage_function_id
            FROM buildings b
            JOIN xref_contents x
                ON b.occupancy_type = x.occupancy_type
                --AND b.BldgType = x.bldg_type
                --AND b.DesignLevel = x.design_level
        '''
        connection.execute(content_query)

        # Inventory Damage Functions
        inventory_query = '''
            CREATE TABLE inventory_damage_functions AS
            SELECT b.ID AS building_id, x.damage_function_id
            FROM buildings b
            JOIN xref_inventory x
                ON b.occupancy_type = x.occupancy_type
                --AND b.BldgType = x.bldg_type
                --AND b.DesignLevel = x.design_level
        '''
        connection.execute(inventory_query)          

    def _compute_damage_function_statistics(self, connection: duckdb.DuckDBPyConnection) -> None:
        # Compute the mean and std. deviation of the damage functions.

        """
        # Original SQL that we came up with prior to triangular distribution logic.

        sql_statement = '''
            CREATE OR REPLACE TABLE damage_function_statistics AS

            WITH 
            -- 1. Unpivot DDF Structure (Cleaned and Cast)
            -- We filter out NULLs immediately to keep the index clean
            ddf_points AS (
                SELECT 
                    ddf_id,
                    CAST(REPLACE(REPLACE(REPLACE(variable_name, 'depth_', ''), 'm', '-'), '_', '.') AS DOUBLE) AS depth_ft,
                    value_column as value
                FROM ddf_structure 
                UNPIVOT EXCLUDE NULLS (
                    value_column FOR variable_name IN (COLUMNS('^depth_'))
                )
            ),

            -- 2. Create Interpolation Segments
            -- We look ahead to the next point to define the line segment (slope) for each interval.
            ddf_segments AS (
                SELECT 
                    ddf_id,
                    depth_ft as x1,
                    value as y1,
                    LEAD(depth_ft) OVER (PARTITION BY ddf_id ORDER BY depth_ft) as x2,
                    LEAD(value) OVER (PARTITION BY ddf_id ORDER BY depth_ft) as y2
                FROM ddf_points
            ),

            -- 3. Generate Hazard Evaluation Points
            -- For every building, we create 3 rows: Mean, Mean + Std, Mean - Std
            hazard_points AS (
                SELECT h.id, h.return_period, sdf.damage_function_id as ddf_id, h.depth as eval_depth
                FROM hazard h
                JOIN structure_damage_functions sdf ON h.ID = sdf.building_id
                
                UNION ALL
                
                SELECT h.id, h.return_period, sdf.damage_function_id as ddf_id, h.depth + h.std_dev as eval_depth
                FROM hazard h
                JOIN structure_damage_functions sdf ON h.ID = sdf.building_id
                
                UNION ALL
                
                SELECT h.id, h.return_period, sdf.damage_function_id as ddf_id, h.depth - h.std_dev as eval_depth
                FROM hazard h
                JOIN structure_damage_functions sdf ON h.ID = sdf.building_id
            ),

            -- 4. Perform Linear Interpolation
            interpolated_results AS (
                SELECT 
                    hp.id,
                    hp.return_period,
                    hp.eval_depth,
                    -- Interpolation Logic
                    CASE 
                        -- Case A: Depth is below the lowest defined point on curve -> Assume 0 damage (or clamp to min)
                        WHEN ds.x1 IS NULL THEN 0 
                        -- Case B: Depth is above the highest defined point -> Clamp to max damage found
                        WHEN ds.x2 IS NULL THEN ds.y1
                        -- Case C: Standard Linear Interpolation: y = y1 + (x - x1) * slope
                        ELSE ds.y1 + (hp.eval_depth - ds.x1) * (ds.y2 - ds.y1) / (ds.x2 - ds.x1)
                    END as calc_damage
                FROM hazard_points hp
                -- ASOF JOIN allows us to find the specific segment where: segment_start <= current_depth
                ASOF LEFT JOIN ddf_segments ds 
                    ON hp.ddf_id = ds.ddf_id 
                    AND hp.eval_depth >= ds.x1
            )

            -- 5. Final Aggregation
            SELECT 
                id as building_id,
                return_period,
                AVG(calc_damage) as damage_percent,
                STDDEV(calc_damage) as damage_percent_std
            FROM interpolated_damages
            GROUP BY id, return_period;
        '''
        """

        sql_statement = '''
            CREATE OR REPLACE TABLE damage_function_statistics AS

            WITH 
            -- 1. Unpivot DDF Structure
            ddf_points AS (
                SELECT 
                    ddf_id,
                    CAST(REPLACE(REPLACE(REPLACE(variable_name, 'depth_', ''), 'm', '-'), '_', '.') AS DOUBLE) AS depth_ft,
                    value_column as value
                FROM ddf_structure 
                UNPIVOT EXCLUDE NULLS (
                    value_column FOR variable_name IN (COLUMNS('^depth_'))
                )
            ),

            -- 2. Create Interpolation Segments
            ddf_segments AS (
                SELECT 
                    ddf_id,
                    depth_ft as x1,
                    value as y1,
                    LEAD(depth_ft) OVER (PARTITION BY ddf_id ORDER BY depth_ft) as x2,
                    LEAD(value) OVER (PARTITION BY ddf_id ORDER BY depth_ft) as y2
                FROM ddf_points
            ),

            -- 3. Generate Hazard Evaluation Points (With Tagging)
            hazard_points AS (
                SELECT h.id, h.return_period, sdf.damage_function_id as ddf_id, h.depth as eval_depth, 'mean' as point_type
                FROM hazard h JOIN structure_damage_functions sdf ON h.ID = sdf.building_id
                UNION ALL
                SELECT h.id, h.return_period, sdf.damage_function_id as ddf_id, h.depth + h.std_dev as eval_depth, 'max' as point_type
                FROM hazard h JOIN structure_damage_functions sdf ON h.ID = sdf.building_id
                UNION ALL
                SELECT h.id, h.return_period, sdf.damage_function_id as ddf_id, h.depth - h.std_dev as eval_depth, 'min' as point_type
                FROM hazard h JOIN structure_damage_functions sdf ON h.ID = sdf.building_id
            ),

            -- 4. Perform Linear Interpolation
            interpolated_results AS (
                SELECT 
                    hp.id,
                    hp.return_period,
                    hp.point_type,
                    CASE 
                        WHEN ds.x1 IS NULL THEN 0 
                        WHEN ds.x2 IS NULL THEN ds.y1
                        ELSE ds.y1 + (hp.eval_depth - ds.x1) * (ds.y2 - ds.y1) / (ds.x2 - ds.x1)
                    END as calc_damage
                FROM hazard_points hp
                ASOF LEFT JOIN ddf_segments ds 
                    ON hp.ddf_id = ds.ddf_id AND hp.eval_depth >= ds.x1
            ),

            -- 5. Pivot Statistics
            pivoted_stats AS (
                SELECT 
                    id as building_id,
                    return_period,
                    MAX(CASE WHEN point_type = 'mean' THEN calc_damage END) as d_mean,
                    MAX(CASE WHEN point_type = 'min'  THEN calc_damage END) as d_min,
                    MAX(CASE WHEN point_type = 'max'  THEN calc_damage END) as d_max
                FROM interpolated_results
                GROUP BY id, return_period
            ),

            -- 6. Apply Triangular Distribution Logic
            triangular_calc AS (
                SELECT 
                    building_id,
                    return_period,
                    d_mean,
                    d_min,
                    d_max,
                    -- Calculate Mode: (3 * Mean) - Min - Max
                    -- We clamp it between Min and Max to ensure the math doesn't break if skew is extreme
                    GREATEST(d_min, LEAST(d_max, (3 * d_mean) - d_min - d_max)) as mode_clamped
                FROM pivoted_stats
            )

            -- 7. Final Output
            SELECT 
                building_id,
                return_period,
                d_mean as damage_percent,
                d_min,
                d_max,

                -- New Column: The "Peak" of the distribution
                mode_clamped as d_mode,
                -- 1. Hinge Corrected Mean
                -- Corrects for the asymmetric slopes pulling the average down
                d_mean + ( (d_min + d_max - 2 * d_mean) * (1.0 / SQRT(2 * PI())) ) as damage_percent_mean,

                ABS(d_max - d_min) / 2.0 as damage_percent_std,
                -- Standard Deviation (Square root of the Variance)
                SQRT(ABS(
                    (POWER(d_min, 2) + POWER(d_max, 2) + POWER(mode_clamped, 2) 
                    - (d_min * d_max) 
                    - (d_min * mode_clamped) 
                    - (d_max * mode_clamped)) / 18
                )) as triangular_std_dev,
                NULLIF(d_max - d_min, 0) / 4 AS range_std_dev
            FROM triangular_calc;
        '''
        connection.execute(sql_statement)

    def _calculate_losses(self, connection: duckdb.DuckDBPyConnection) -> None:
        # Compute the damages from the valuation * the damage percents.
        # damage_function_statistics with damage_percent_mean and damage_percent_std by building_id and return_period. 

        sql_statement = '''
            CREATE OR REPLACE TABLE losses AS
            SELECT
                b.ID,
                d.return_period,
                b.building_cost * d.damage_percent_mean AS loss_mean,
                b.building_cost * d.damage_percent_std AS loss_std
            FROM buildings b
            JOIN damage_function_statistics d ON b.ID = d.building_id
        '''

        connection.execute(sql_statement)

    def _calculate_aal(self, connection: duckdb.DuckDBPyConnection) -> None:
        # Calculate AAL using trapezoidal rule

        sql_statement = '''
            CREATE OR REPLACE TABLE aal_losses AS

            WITH 
            -- 1. Convert Return Period to Annual Probability
            probabilities AS (
                SELECT 
                    ID,
                    return_period,
                    loss_mean,
                    loss_std,
                    1.0 / return_period as prob
                FROM losses
            ),

            -- 2. Create Trapezoidal Segments
            -- We sort by Probability DESC (High Frequency -> Low Frequency)
            -- Example: 10yr (0.1) -> 50yr (0.02) -> 100yr (0.01)
            segments AS (
                SELECT 
                    ID,
                    prob as p_start,
                    loss_mean as l_start,
                    loss_std as s_start,
                    -- Look ahead to the next probability point
                    LEAD(prob) OVER (PARTITION BY ID ORDER BY prob DESC) as p_end,
                    LEAD(loss_mean) OVER (PARTITION BY ID ORDER BY prob DESC) as l_end,
                    LEAD(loss_std) OVER (PARTITION BY ID ORDER BY prob DESC) as s_end
                FROM probabilities
            ),

            -- 3. Calculate Area of Segments
            segment_areas AS (
                SELECT 
                    ID,
                    -- Trapezoid Area: Average Height * Width
                    -- Width = (Start Prob - End Prob)
                    
                    -- Mean AAL Contribution
                    ( (l_start + l_end) / 2.0 ) * (p_start - p_end) as aal_contribution_mean,
                    
                    -- Std Dev AAL Contribution (Assuming Perfect Correlation)
                    ( (s_start + s_end) / 2.0 ) * (p_start - p_end) as aal_contribution_std
                FROM segments
                -- We filter out the last row (highest return period) because it has no "next" point to connect to
                WHERE p_end IS NOT NULL
            )

            -- 4. Sum Segments to get Total AAL
            SELECT 
                ID,
                SUM(aal_contribution_mean) as aal_mean,
                SUM(aal_contribution_std) as aal_std
            FROM segment_areas
            GROUP BY ID;
        '''

        connection.execute(sql_statement)