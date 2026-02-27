-- =============================================================================
-- REFERENCE: Wide Format Export Query Structure
-- =============================================================================
--
-- This is a reference template showing the structure of the export_wide query.
-- The actual SQL is generated dynamically by sql_builder.py which:
--
-- 1. Discovers return periods from the database
-- 2. Checks for optional columns (velocity, duration)
-- 3. Builds CTEs for each data source
-- 4. Constructs the final SELECT with all pivoted columns
--
-- DO NOT RUN THIS FILE - use sql_builder.py instead via utils.py
--
-- =============================================================================

WITH

-- -----Pivot hazard (depth, velocity, duration) by return period -----
hazard_wide AS (
    SELECT
        id,
        -- For each return period, pivot depth, velocity, duration
        MAX(depth)     FILTER (WHERE return_period = 10) AS depth_rp10,
        MAX(velocity)  FILTER (WHERE return_period = 10) AS velocity_rp10,
        MAX(duration)  FILTER (WHERE return_period = 10) AS duration_rp10,
        -- ... repeated for all return periods (20, 50, 100, 200, 500, 1000, 2000)
    FROM hazard
    GROUP BY id
),

-- ----- Pivot losses (min, mean, std, max) by return period -----
losses_wide AS (
    SELECT
        id,
        -- For each return period, pivot all loss statistics
        MAX(loss_min)  FILTER (WHERE return_period = 10) AS loss_min_rp10,
        MAX(loss_mean) FILTER (WHERE return_period = 10) AS loss_mean_rp10,
        MAX(loss_std)  FILTER (WHERE return_period = 10) AS loss_std_rp10,
        MAX(loss_max)  FILTER (WHERE return_period = 10) AS loss_max_rp10,
        -- ... repeated for all return periods
    FROM losses
    GROUP BY id
)

-- -----Final wide select: one row per building -----
SELECT
    -- Building attributes
    b.id,
    b.bid,
    b.occupancy_type,
    b.general_building_type,
    b.number_stories,
    b.building_cost,
    
    -- Hazard per return period
    hw.depth_rp10, hw.depth_rp20, hw.depth_rp50, hw.depth_rp100,
    hw.velocity_rp10, hw.velocity_rp20, hw.velocity_rp50, hw.velocity_rp100,
    
    -- Losses per return period  
    lw.loss_min_rp10, lw.loss_min_rp20,
    lw.loss_mean_rp10, lw.loss_mean_rp20,
    lw.loss_std_rp10, lw.loss_std_rp20,
    lw.loss_max_rp10, lw.loss_max_rp20,
    
    -- Geometry
    b.geometry

FROM buildings b
LEFT JOIN hazard_wide hw ON b.id = hw.id
LEFT JOIN losses_wide lw ON b.id = lw.id
